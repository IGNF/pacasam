"""
This module provides functions to download patches of orthoimages from a sampling geopackage and save them as .tif files
Behavior is similar to the one described in `laz.py`

dataset_root_path/
├── train/
│   ├── TRAIN-file-{file_id}-patch-{patch_id}.tif
├── val/
│   ├── VAL-file-{file_id}-patch-{patch_id}.tif
├── test/
│   ├── TEST-file-{file_id}-patch-{patch_id}.tif

"""


from pathlib import Path
import tempfile
from pdaltools.color import retry, download_image_from_geoportail
from tqdm import tqdm
from pacasam.connectors.connector import FILE_ID_COLNAME, GEOMETRY_COLNAME, PATCH_ID_COLNAME
from pacasam.extractors.extractor import Extractor, format_new_patch_path
from pacasam.samplers.sampler import SPLIT_COLNAME
import rasterio


class OrthoimagesExtractor(Extractor):
    """Extract a dataset of RGB-NIR data patches (4 bands TIFF)."""

    patch_suffix: str = ".tiff"
    proj = 2154
    timeout_second = 300
    pixel_per_meter = 5

    def __init__(self,):


    def extract(self) -> None:
        """Download the orthoimages dataset."""
        for _, patch_info in tqdm(self.sampling.iterrows()):
            self.extract_single_patch(patch_info)

    def extract_single_patch(self, patch_info):
        """Extract and RGB+NIR tiff for the patch."""

        split = getattr(patch_info, SPLIT_COLNAME)
        patch_id = getattr(patch_info, PATCH_ID_COLNAME)
        dir_to_save_patch: Path = self.dataset_root_path / split
        tiff_patch_path = dir_to_save_patch / f"{split.upper()}-{patch_id}"

        patch_bounds = getattr(patch_info, GEOMETRY_COLNAME).bounds

        with tempfile.NamedTemporaryFile(suffix=".tiff") as tmp_ortho_rgb, tempfile.NamedTemporaryFile(suffix=".tiff") as tmp_ortho_nir:
            self.get_orthoimages_for_patch(patch_bounds, tmp_ortho_rgb.name, tmp_ortho_nir.name)
            self.collate_rgbnir_and_save(tmp_ortho_rgb.name, tmp_ortho_nir.name, tiff_patch_path)

    def get_orthoimages_for_patch(self, patch_bounds: tuple, tmp_ortho_rgb: str, tmp_ortho_nir: str):
        """Request RGB and NIR-Color orthoimages,"""
        xmin, ymin, xmax, ymax = patch_bounds

        download_image_from_geoportail_retrying = retry(7, 15, 2)(download_image_from_geoportail)
        download_image_from_geoportail_retrying(
            self.proj, "ORTHOIMAGERY.ORTHOPHOTOS", xmin, ymin, xmax, ymax, self.pixel_per_meter, tmp_ortho_rgb, self.timeout_second
        )
        download_image_from_geoportail_retrying(
            self.proj, "ORTHOIMAGERY.ORTHOPHOTOS.IRC", xmin, ymin, xmax, ymax, self.pixel_per_meter, tmp_ortho_nir, self.timeout_second
        )

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
