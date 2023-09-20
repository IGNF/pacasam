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


from copy import copy, deepcopy
from pathlib import Path
import tempfile
from typing import Tuple
import numpy as np
from tqdm import tqdm
from pacasam.connectors.connector import GEOMETRY_COLNAME, PATCH_ID_COLNAME
from pacasam.extractors.extractor import Extractor
from pacasam.samplers.sampler import SPLIT_COLNAME
import rasterio
from rasterio import DatasetReader
from rasterio.mask import mask

from geopandas import GeoDataFrame


class BDOrthoVintageExtractor(Extractor):
    """Extract a dataset of RGB-NIR data patches (4 bands TIFF) from a BD Ortho file system."""

    patch_suffix: str = ".jp2"
    rgb_file_column: str = "rgb_file"
    irc_file_column: str = "irc_file"

    def extract(self) -> None:
        """Download the orthoimages dataset."""
        for rgb_irc_paths, single_file_sampling in self.sampling.groupby([self.rgb_file_column, self.irc_file_column]):
            self.log.info(f"{self.name}: Extraction + Colorization from {rgb_irc_paths} (k={len(single_file_sampling)} patches)")
            self.extract_from_single_file(rgb_irc_paths, single_file_sampling)
            self.log.info(f"{self.name}: SUCCESS for {rgb_irc_paths}")

    def extract_from_single_file(self, rgb_irc_paths: Tuple[Path, Path], single_file_sampling: GeoDataFrame):
        with rasterio.open(rgb_irc_paths[0], driver="JP2OpenJPEG") as rgb, rasterio.open(rgb_irc_paths[1], driver="JP2OpenJPEG") as irc:
            meta = deepcopy(rgb.meta)  # do not modify inplace ?
            meta.update(count=4)
            # for each patch
            for patch_info in single_file_sampling.itertuples():
                split = getattr(patch_info, SPLIT_COLNAME)
                patch_id = getattr(patch_info, PATCH_ID_COLNAME)
                dir_to_save_patch: Path = self.dataset_root_path / split
                tiff_patch_path = dir_to_save_patch / f"{split.upper()}-{patch_id}{self.patch_suffix}"

                patch_geometry = getattr(patch_info, GEOMETRY_COLNAME)

                # with tempfile.NamedTemporaryFile(suffix=self.patch_suffix) as tmp_patch_rgb, tempfile.NamedTemporaryFile(
                #     suffix=self.patch_suffix
                # ) as tmp_patch_irc:
                rgb_arr = extract_patch_as_geotiffs(src_orthoimagery=rgb, patch_geometry=patch_geometry)
                irc_arr = extract_patch_as_geotiffs(src_orthoimagery=irc, patch_geometry=patch_geometry)
                if rgb_arr.shape[1] == irc_arr.shape[1] == 60 * 5:
                    print("here")
                    collate_rgbnir_and_save(meta, rgb_arr, irc_arr, tiff_patch_path)


def extract_patch_as_geotiffs(src_orthoimagery: DatasetReader, patch_geometry: Tuple):
    clipped_dataset, _ = mask(src_orthoimagery, [patch_geometry], crop=True)
    clipped_dataset = clipped_dataset[:, :300, :300]
    return clipped_dataset


def collate_rgbnir_and_save(meta, rgb_arr: np.ndarray, irc_arr: np.ndarray, tiff_patch_path: Path):
    """Collate RGB and NIR arrays and save to a new geotiff."""
    tiff_patch_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(tiff_patch_path, "w", **meta) as dst:
        dst.write(rgb_arr[0], 1)
        dst.set_band_description(1, "Red")
        dst.write(rgb_arr[1], 2)
        dst.set_band_description(2, "Green")
        dst.write(rgb_arr[2], 3)
        dst.set_band_description(3, "Blue")
        dst.write(irc_arr[0], 4)
        dst.set_band_description(4, "Infrared")
