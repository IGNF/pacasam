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


from pathlib import Path
import tempfile
from typing import Tuple
from tqdm import tqdm
from pacasam.connectors.connector import GEOMETRY_COLNAME, PATCH_ID_COLNAME
from pacasam.extractors.extractor import Extractor
from pacasam.samplers.sampler import SPLIT_COLNAME
import rasterio
from rasterio import DatasetReader
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
            self._extract_from_single_area(rgb_irc_paths, single_file_sampling)
            self.log.info(f"{self.name}: SUCCESS for {rgb_irc_paths}")

    def extract_from_single_file(self, rgb_irc_paths: Tuple[Path, Path], single_file_sampling: GeoDataFrame):
        with rasterio.open(rgb_irc_paths[0]) as rgb, rasterio.open(rgb_irc_paths[1]) as irc:
            # for each patch
            for patch_info in single_file_sampling.itertuples():
                split = getattr(patch_info, SPLIT_COLNAME)
                patch_id = getattr(patch_info, PATCH_ID_COLNAME)
                dir_to_save_patch: Path = self.dataset_root_path / split
                tiff_patch_path = dir_to_save_patch / f"{split.upper()}-{patch_id}{self.patch_suffix}"

                patch_bounds = getattr(patch_info, GEOMETRY_COLNAME).bounds

                with tempfile.NamedTemporaryFile(suffix=self.patch_suffix) as tmp_patch_rgb, tempfile.NamedTemporaryFile(
                    suffix=self.patch_suffix
                ) as tmp_patch_irc:
                    self.extract_patch(src=rgb, bounds=patch_bounds, out_path=tmp_patch_rgb)
                    self.extract_patch(src=irc, bounds=patch_bounds, out_path=tmp_patch_irc)
                    self.collate_rgbnir_and_save(tmp_patch_rgb.name, tmp_patch_irc.name, tiff_patch_path)

    def extract_patch(src: DatasetReader, bounds: Tuple, out_path: tempfile._TemporaryFileWrapper):
        # TODO.
        ...

    def collate_rgbnir_and_save(self, tmp_ortho_rgb: str, tmp_ortho_nir: str, tiff_patch_path: Path):
        """Collate RGB and NIR tiff images and save to a new geotiff."""

        tiff_patch_path.parent.mkdir(parents=True, exist_ok=True)

        with rasterio.open(tmp_ortho_rgb) as ortho_rgb, rasterio.open(tmp_ortho_nir) as ortho_irc:
            merged_profile = ortho_rgb.profile
            merged_profile.update(count=4)
            with rasterio.open(tiff_patch_path, "w", **merged_profile) as dst:
                dst.write(ortho_rgb.read(1), 1)
                dst.set_band_description(1, "Red")
                dst.write(ortho_rgb.read(2), 2)
                dst.set_band_description(2, "Green")
                dst.write(ortho_rgb.read(3), 3)
                dst.set_band_description(3, "Blue")
                dst.write(ortho_irc.read(1), 4)
                dst.set_band_description(4, "Infrared")
