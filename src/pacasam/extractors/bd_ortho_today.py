"""
This module provides functions to download patches of orthoimages from a sampling geopackage and save them as .tiff files
Behavior is similar to the one described in `laz.py`

dataset_root_path/
├── train/
│   ├── TRAIN-{patch_id}.tiff
├── val/
│   ├── VAL-{patch_id}.tiff
├── test/
│   ├── TEST-{patch_id}.tiff

"""


from pathlib import Path
import shutil
import tempfile
from pdaltools.color import retry, download_image_from_geoportail
from pacasam.connectors.connector import GEOMETRY_COLNAME, PATCH_ID_COLNAME, SRID_COLNAME
from pacasam.extractors.extractor import Extractor, DEFAULT_SRID_LAMBERT93
from pacasam.samplers.sampler import SPLIT_COLNAME
import rasterio
from mpire import WorkerPool


class BDOrthoTodayExtractor(Extractor):
    """Extract a dataset of Infrared-R-G-B data patches (4 bands TIFF) from the BD Ortho Web Map Service.

    Note: band are ordered by wavelength, inspired by the TreeSatAI (https://zenodo.org/records/6780578) ordering
    since this extractor was primarly designed to extract datset for forest classification.

    See: https://geoservices.ign.fr/services-web-experts-ortho

    """

    patch_suffix: str = ".tiff"
    timeout_second = 300
    pixel_per_meter = 5

    def extract(self) -> None:
        """Download the orthoimages dataset."""
        # mpire does argument unpacking, see https://github.com/sybrenjansen/mpire/issues/29#issuecomment-984559662.
        iterable_of_args = [(patch_info,) for _, patch_info in self.sampling.iterrows()]
        with WorkerPool(n_jobs=self.num_jobs) as pool:
            pool.map(self.extract_single_patch, iterable_of_args, progress_bar=True)

    def extract_single_patch(self, patch_info):
        """Extract and RGB+NIR tiff for the patch."""

        split = getattr(patch_info, SPLIT_COLNAME)
        patch_id = getattr(patch_info, PATCH_ID_COLNAME)
        dir_to_save_patch: Path = self.dataset_root_path / split
        tiff_patch_path = dir_to_save_patch / f"{split.upper()}-{patch_id}{self.patch_suffix}"
        if tiff_patch_path.exists():
            return
        patch_bounds = getattr(patch_info, GEOMETRY_COLNAME).bounds
        # Use given srid if possible, else use the default value.
        srid = getattr(patch_info, SRID_COLNAME, DEFAULT_SRID_LAMBERT93)

        with tempfile.NamedTemporaryFile(suffix=".tiff") as tmp_ortho_rgb, tempfile.NamedTemporaryFile(suffix=".tiff") as tmp_ortho_nir:
            self.get_orthoimages_for_patch(patch_bounds, srid, tmp_ortho_rgb.name, tmp_ortho_nir.name)
            tmp_patch: tempfile._TemporaryFileWrapper = tempfile.NamedTemporaryFile(suffix=self.patch_suffix, prefix="extracted_patch")
            self.collate_rgbnir_and_save(tmp_ortho_rgb.name, tmp_ortho_nir.name, tmp_patch)
            tiff_patch_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(tmp_patch.name, tiff_patch_path)

    def get_orthoimages_for_patch(self, patch_bounds: tuple, srid: str, tmp_ortho_rgb: str, tmp_ortho_nir: str):
        """Request RGB and NIR-Color orthoimages,"""
        xmin, ymin, xmax, ymax = patch_bounds

        download_image_from_geoportail_retrying = retry(7, 15, 2)(download_image_from_geoportail)
        download_image_from_geoportail_retrying(
            srid, "ORTHOIMAGERY.ORTHOPHOTOS", xmin, ymin, xmax, ymax, self.pixel_per_meter, tmp_ortho_rgb, self.timeout_second
        )
        download_image_from_geoportail_retrying(
            srid, "ORTHOIMAGERY.ORTHOPHOTOS.IRC", xmin, ymin, xmax, ymax, self.pixel_per_meter, tmp_ortho_nir, self.timeout_second
        )

    def collate_rgbnir_and_save(self, tmp_ortho_rgb: str, tmp_ortho_nir: str, tiff_patch_path: Path):
        """Collate RGB and NIR tiff images and save to a new geotiff."""
        with rasterio.open(tmp_ortho_rgb) as ortho_rgb, rasterio.open(tmp_ortho_nir) as ortho_irc:
            options = ortho_rgb.meta
            options.update(count=4)
            options.update(compress="DEFLATE")
            with rasterio.open(tiff_patch_path, "w", **options) as dst:
                dst.write(ortho_irc.read(1), 1)
                dst.set_band_description(1, "Infrared")
                dst.write(ortho_rgb.read(1), 2)
                dst.set_band_description(2, "Red")
                dst.write(ortho_rgb.read(2), 3)
                dst.set_band_description(3, "Green")
                dst.write(ortho_rgb.read(3), 4)
                dst.set_band_description(4, "Blue")
