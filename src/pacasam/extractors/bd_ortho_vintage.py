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


import os
from pathlib import Path
import shutil
import tempfile
from typing import Tuple
import numpy as np
from pacasam.connectors.connector import GEOMETRY_COLNAME, PATCH_ID_COLNAME
from pacasam.extractors.extractor import Extractor
from pacasam.samplers.sampler import SPLIT_COLNAME
import rasterio
from rasterio import DatasetReader
from rasterio import Affine
from rasterio.mask import mask
from mpire import WorkerPool

from geopandas import GeoDataFrame


class BDOrthoVintageExtractor(Extractor):
    """Extract a dataset of Infrared-R-G-B data patches (4 bands TIFF) from a BD Ortho file system.

    Note: band are ordered by wavelenght, inspired by the TreeSatAI (https://zenodo.org/records/6780578) ordering
    since this extractor was primarly designed to extract datset for forest classification.

    Environment variables:
      - BD_ORTHO_VINTAGE_VRT_DIR: path to a directory with subdirs irc and rgb, containing VRTs for each BD ORtho vintage (e.g. D01)

    """

    patch_suffix: str = ".tiff"
    dept_column: str = "french_department_id_imagery"
    year_column: str = "year_imagery"
    pixel_per_meter: int = 5

    def extract(self) -> None:
        """Download the orthoimages dataset."""
        vintages_vrt_dir = os.getenv("BD_ORTHO_VINTAGE_VRT_DIR")
        if not vintages_vrt_dir:
            raise ValueError("You should define where BD ORtho VRTs are with env variable `BD_ORTHO_VINTAGE_VRT_DIR`")

        iterable_of_args = []
        for (dept, year), single_vintage in self.sampling.groupby([self.dept_column, self.year_column]):
            rvb_vrt = Path(vintages_vrt_dir) / "rvb" / f"{dept}-{year}.vrt"
            irc_vrt = Path(vintages_vrt_dir) / "irc" / f"{dept}-{year}.vrt"
            iterable_of_args.append((rvb_vrt, irc_vrt, single_vintage))

        with WorkerPool(n_jobs=self.num_jobs) as pool:
            pool.map(self.extract_from_single_vintage, iterable_of_args, progress_bar=True)

    def extract_from_single_vintage(self, rvb_vrt, irc_vrt, single_file_sampling: GeoDataFrame):
        with rasterio.open(rvb_vrt) as rvb, rasterio.open(irc_vrt) as irc:
            for patch_info in single_file_sampling.itertuples():
                split = getattr(patch_info, SPLIT_COLNAME)
                patch_id = getattr(patch_info, PATCH_ID_COLNAME)
                tiff_patch_path: Path = self.make_new_patch_path(patch_id=patch_id, split=split)
                if tiff_patch_path.exists():
                    continue

                patch_geometry = getattr(patch_info, GEOMETRY_COLNAME)
                bbox = patch_geometry.bounds
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                assert width == height  # squares only
                width_pixels = int(self.pixel_per_meter * width)
                rvb_arr = extract_patch_as_geotiffs(rvb, patch_geometry, width_pixels)
                irc_arr = extract_patch_as_geotiffs(irc, patch_geometry, width_pixels)
                image_resolution = 1 / self.pixel_per_meter
                options = {
                    "driver": "GTiff",
                    "count": 4,
                    "dtype": rvb_arr.dtype,
                    "transform": Affine(image_resolution, 0, bbox[0], 0, -image_resolution, bbox[3]),
                    "crs": rvb.crs,
                    "width": width_pixels,
                    "height": width_pixels,
                    "compress": "DEFLATE",
                    "tiled": False,
                    "bigtiff": "IF_SAFER",
                    "nodata": None,
                }
                tmp_patch: tempfile._TemporaryFileWrapper = tempfile.NamedTemporaryFile(suffix=self.patch_suffix, prefix="extracted_patch")
                collate_rgbnir_and_save(options, rvb_arr, irc_arr, tmp_patch)
                tiff_patch_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(tmp_patch.name, tiff_patch_path)


def extract_patch_as_geotiffs(src_orthoimagery: DatasetReader, patch_geometry: Tuple, num_pixels: int):
    clipped_dataset, _ = mask(src_orthoimagery, [patch_geometry], crop=True)
    clipped_dataset = clipped_dataset[:, :num_pixels, :num_pixels]
    return clipped_dataset


def collate_rgbnir_and_save(meta, rvb_arr: np.ndarray, irc_arr: np.ndarray, tiff_patch_path: Path):
    """Collate RGB and NIR arrays and save to a new geotiff."""
    with rasterio.open(tiff_patch_path, "w", **meta) as dst:
        dst.write(irc_arr[0], 1)
        dst.set_band_description(1, "Infrared")
        dst.write(rvb_arr[0], 2)
        dst.set_band_description(2, "Red")
        dst.write(rvb_arr[1], 3)
        dst.set_band_description(3, "Green")
        dst.write(rvb_arr[2], 4)
        dst.set_band_description(4, "Blue")
