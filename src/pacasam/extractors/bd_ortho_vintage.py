"""
This module provides functions to extract patches of orthoimages from a sampling geopackage and save them as .jp2 (JPEG2000) files
Behavior is similar to the one described in `laz.py`, with output structured as:

dataset_root_path/
├── train/
│   ├── TRAIN-{patch_id}.tiff
├── val/
│   ├── VAL-{patch_id}.tiff
├── test/
│   ├── TEST-{patch_id}.tiff

Requirements in the sampling are a bit different: in addition to patch_id, srid (optionnal), geometry, split,
we need rgb_file and irc_file, which are path to the orthoimages (jp2 files, typically 1km x 1km, but may be larger).

"""


from copy import deepcopy
import os
from pathlib import Path
from typing import Tuple
import numpy as np
from tqdm import tqdm
from pacasam.connectors.connector import GEOMETRY_COLNAME, PATCH_ID_COLNAME
from pacasam.extractors.extractor import Extractor
from pacasam.samplers.sampler import SPLIT_COLNAME
import rasterio
from rasterio import DatasetReader
from rasterio.mask import mask
from mpire import WorkerPool

from geopandas import GeoDataFrame


class BDOrthoVintageExtractor(Extractor):
    """Extract a dataset of IRC,R,G,B data patches (4 bands TIFF) from a BD Ortho file system.

    Environment variables:
      - BD_ORTHO_VINTAGE_VRT_DIR: path to a directory with subdirs irc and rgb, containing VRTs for each BD ORtho vintage (e.g. D01)
      - NUM_JOBS: num of jobs in multiprocessing - ideally equal to the number of different vintage considered. Else, default to 1.

    """

    patch_suffix: str = ".tiff"
    dept_column: str = "french_department_id_imagery"
    year_column: str = "year_imagery"
    pixel_per_meter: int = 5
    vintages_vrt_dir: Path = Path(os.getenv("BD_ORTHO_VINTAGE_VRT_DIR"))

    def extract(self) -> None:
        """Download the orthoimages dataset."""
        iterable_of_args = []
        for (dept, year), single_vintage in self.sampling.groupby([self.dept_column, self.year_column]):
            rvb_vrt = self.vintages_vrt_dir / "rvb" / f"{dept}-{year}.vrt"
            irc_vrt = self.vintages_vrt_dir / "irc" / f"{dept}-{year}.vrt"
            iterable_of_args.append((rvb_vrt, irc_vrt, single_vintage))

        with WorkerPool(n_jobs=os.getenv("NUM_JOBS", default=1)) as pool:
            pool.map(self.extract_from_single_vintage, iterable_of_args, progress_bar=True)

    def extract_from_single_vintage(self, rvb_vrt, irc_vrt, single_file_sampling: GeoDataFrame):
        with rasterio.open(rvb_vrt) as rvb, rasterio.open(irc_vrt) as irc:
            meta = deepcopy(rvb.meta)  # Important: use meta and not profile!
            meta.update(count=4)
            meta.update(driver="GTiff")
            # for each patch
            for patch_info in single_file_sampling.itertuples():
                split = getattr(patch_info, SPLIT_COLNAME)
                patch_id = getattr(patch_info, PATCH_ID_COLNAME)
                dir_to_save_patch: Path = self.dataset_root_path / split
                tiff_patch_path = dir_to_save_patch / f"{split.upper()}-{patch_id}{self.patch_suffix}"

                patch_geometry = getattr(patch_info, GEOMETRY_COLNAME)
                bbox = patch_geometry.bounds
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                assert width == height  # squares only
                width_pixels = int(self.pixel_per_meter * width)
                meta.update(width=width_pixels, height=width_pixels)
                rvb_arr = extract_patch_as_geotiffs(rvb, patch_geometry, width_pixels)
                irc_arr = extract_patch_as_geotiffs(irc, patch_geometry, width_pixels)
                collate_rgbnir_and_save(meta, rvb_arr, irc_arr, tiff_patch_path)


def extract_patch_as_geotiffs(src_orthoimagery: DatasetReader, patch_geometry: Tuple, num_pixels: int):
    clipped_dataset, _ = mask(src_orthoimagery, [patch_geometry], crop=True)
    clipped_dataset = clipped_dataset[:, :num_pixels, :num_pixels]
    return clipped_dataset


def collate_rgbnir_and_save(meta, rvb_arr: np.ndarray, irc_arr: np.ndarray, tiff_patch_path: Path):
    """Collate RGB and NIR arrays and save to a new geotiff."""
    tiff_patch_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(tiff_patch_path, "w", **meta) as dst:
        dst.write(irc_arr[0], 1)
        dst.set_band_description(1, "Infrared")
        dst.write(rvb_arr[0], 2)
        dst.set_band_description(2, "Red")
        dst.write(rvb_arr[1], 3)
        dst.set_band_description(3, "Green")
        dst.write(rvb_arr[2], 4)
        dst.set_band_description(4, "Blue")
