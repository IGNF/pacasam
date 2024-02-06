"""
This module provides functions to extract patches of orthoimages from a sampling geopackage and save them as .tiff files
Behavior is similar to the one described in `laz.py`, with output structured as:

dataset_root_path/
├── train/
│   ├── TRAIN-{patch_id}.tiff
├── val/
│   ├── VAL-{patch_id}.tiff
├── test/
│   ├── TEST-{patch_id}.tiff

Requirements in the sampling are a bit different: in addition to `patch_id`, `srid` (optionnal), `geometry`, `split`,
we need `rgb_file` and `irc_file`, which are path to the orthoimages (typically jp2 files, typically 1km x 1km but may be larger).
The patches are expected to be fully included in the indicated file. If this is not the case, consider indicating a vrt file instead.

"""


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

RGB_COLNAME = "rgb_file"
IRC_COLNAME = "irc_file"


class BDOrthoVintageExtractor(Extractor):
    """Extract a dataset of Infrared-R-G-B data patches (4 bands TIFF) from a BD Ortho file system.

    Note: band are ordered by wavelenght, inspired by the TreeSatAI (https://zenodo.org/records/6780578) ordering
    since this extractor was primarly designed to extract datset for forest classification.

    """

    patch_suffix: str = ".tiff"
    pixel_per_meter: int = 5

    def extract(self) -> None:
        """Download the orthoimages dataset."""
        iterable_of_args = []
        for (rgb_file, irc_file), single_imagery in self.sampling.groupby([RGB_COLNAME, IRC_COLNAME]):
            iterable_of_args.append((rgb_file, irc_file, single_imagery))

        with WorkerPool(n_jobs=self.num_jobs) as pool:
            pool.map(self.extract_from_single_file, iterable_of_args, progress_bar=True)

    def extract_from_single_file(self, rgb_file, irc_file, single_file_sampling: GeoDataFrame):
        with rasterio.open(rgb_file) as rgb, rasterio.open(irc_file) as irc:
            for patch_info in single_file_sampling.itertuples():
                split = getattr(patch_info, SPLIT_COLNAME)
                patch_id = getattr(patch_info, PATCH_ID_COLNAME)
                tiff_patch_path: Path = self.make_new_patch_path(patch_id=patch_id, split=split)
                if tiff_patch_path.exists():
                    continue
                patch_geometry = getattr(patch_info, GEOMETRY_COLNAME)
                tmp_patch = extract_rgbnir_patch_as_tmp_file(rgb, irc, self.pixel_per_meter, patch_geometry)
                tiff_patch_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(tmp_patch.name, tiff_patch_path)


def extract_rgbnir_patch_as_tmp_file(rgb, irc, pixel_per_meter, patch_geometry):
    """Extract both rgb and irc patch images and collate them into a temporary file."""
    bbox = patch_geometry.bounds
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    assert width == height  # squares only
    width_pixels = int(pixel_per_meter * width)
    rgb_arr = extract_patch_as_geotiffs(rgb, patch_geometry, width_pixels)
    irc_arr = extract_patch_as_geotiffs(irc, patch_geometry, width_pixels)
    image_resolution = 1 / pixel_per_meter
    options = {
        "driver": "GTiff",
        "count": 4,
        "dtype": rgb_arr.dtype,
        "transform": Affine(image_resolution, 0, bbox[0], 0, -image_resolution, bbox[3]),
        "crs": rgb.crs,
        "width": width_pixels,
        "height": width_pixels,
        "compress": "DEFLATE",
        "tiled": False,
        "bigtiff": "IF_SAFER",
        "nodata": None,
    }
    tmp_patch: tempfile._TemporaryFileWrapper = tempfile.NamedTemporaryFile(suffix=".tiff", prefix="extracted_patch")
    collate_rgbnir_and_save(options, rgb_arr, irc_arr, tmp_patch)
    return tmp_patch


def extract_patch_as_geotiffs(src_orthoimagery: DatasetReader, patch_geometry: Tuple, num_pixels: int):
    clipped_dataset, _ = mask(src_orthoimagery, [patch_geometry], crop=True)
    clipped_dataset = clipped_dataset[:, :num_pixels, :num_pixels]
    return clipped_dataset


def collate_rgbnir_and_save(meta, rgb_arr: np.ndarray, irc_arr: np.ndarray, tiff_patch_path: Path):
    """Collate RGB and NIR arrays and save to a new geotiff."""
    with rasterio.open(tiff_patch_path, "w", **meta) as dst:
        dst.write(irc_arr[0], 1)
        dst.set_band_description(1, "Infrared")
        dst.write(rgb_arr[0], 2)
        dst.set_band_description(2, "Red")
        dst.write(rgb_arr[1], 3)
        dst.set_band_description(3, "Green")
        dst.write(rgb_arr[2], 4)
        dst.set_band_description(4, "Blue")
