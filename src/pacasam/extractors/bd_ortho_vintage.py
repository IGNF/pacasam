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
from pathlib import Path
from typing import Tuple
import numpy as np
from pacasam.connectors.connector import GEOMETRY_COLNAME, PATCH_ID_COLNAME
from pacasam.extractors.extractor import Extractor
from pacasam.samplers.sampler import SPLIT_COLNAME
import rasterio
from rasterio import DatasetReader
from rasterio.mask import mask

from geopandas import GeoDataFrame


class BDOrthoVintageExtractor(Extractor):
    """Extract a dataset of IRC,R,G,B data patches (4 bands TIFF) from a BD Ortho file system."""

    patch_suffix: str = ".tiff"
    dept_column: str = "french_department_id_imagery"
    year_column: str = "year_imagery"
    resolution: float = 0.2
    vintages_vrt_dir: Path = Path("/mnt/store-lidarhd/projet-LHD/IA/BDForet/Data/202308_PureForestStandDataset_Archive/extraction/VRT/")

    def extract(self) -> None:
        """Download the orthoimages dataset."""
        for (dept, year), single_vintage in self.sampling.groupby([self.dept_column, self.year_column]):
            self.log.info(f"{self.name}: Extraction + Colorization from {dept}-{year} (k={len(single_vintage)} patches)")
            rvb_vrt = self.vintages_vrt_dir / "rvb" / f"{dept}-{year}.vrt"
            irc_vrt = self.vintages_vrt_dir / "irc" / f"{dept}-{year}.vrt"
            self.extract_from_single_vintage(rvb_vrt, irc_vrt, single_vintage)
            self.log.info(f"{self.name}: SUCCESS for {dept}-{year}")

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
                assert width == height  # sqaures only
                meta.update(width=width, heigh=height)
                num_pixels = int(width / self.resolution)
                rvb_arr = extract_patch_as_geotiffs(rvb, patch_geometry, num_pixels)
                irc_arr = extract_patch_as_geotiffs(irc, patch_geometry, num_pixels)
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
