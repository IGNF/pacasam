"""
This module provides functions to extract and colorize patches of LiDAR data from a sampling geopackage and save them as LAZ files.
These files can be further processed for machine learning tasks.
The sampling geopackage is expected to have columns 'split', 'geometry', and 'file_path' that represent
the desired train/validation/test split, the polygon geometry for each patch, and the path
to the corresponding LAZ file, respectively.

The extracted patches are saved to a directory structure under the specified `dataset_root_path`,
with subdirectories for train, validation, and test data.
dataset_root_path/
├── train/
│   ├── TRAIN-file-{file_id}-patch-{patch_id}.laz
├── val/
│   ├── VAL-file-{file_id}-patch-{patch_id}.laz
├── test/
│   ├── TEST-file-{file_id}-patch-{patch_id}.laz

Functions:
    - `extract_laz_dataset(sampling_path: Path, dataset_root_path: Path) -> None`:
        Extracts LiDAR patches from a sampling geopackage and saves them to LAZ files under the dataset path.
    - `extract_patches_from_all_clouds(sampling: GeoDataFrame, dataset_root_path: Path) -> Iterable[Path]`:
        Extracts patches from all LAZ files based on the given sampling information.
    - `extract_patches_from_single_cloud(sampling: GeoDataFrame, dataset_root_path: Path) -> Iterable[Path]`:
        Extracts patches from a single LAZ file based on the given sampling information.
    - `define_patch_path_for_extraction(dataset_root_path: Path, file_path: Path, patch_info) -> Path`:
        Formats the path to save the patch data. Creates dataset directory and split subdirectories as needed.
    - `colorize_all_patches(paths_of_extracted_patches: Iterable[Path]) -> None`:
        Applies colorization to extracted patches.
    - `colorize_single_patch(path_of_patch_data: Path) -> None`:
        Applies colorization to a single patch.

Read and check the sampling geopackage:
    - `load_sampling_with_checks(sampling_path: Path) -> GeoDataFrame`:
        Loads the sampling geopackage as a geopandas dataframe and checks if it follows the expected format.
    - `check_sampling_format(sampling: GeoDataFrame) -> None`:
        Checks if the sampling geopackage follows the expected format.
    - `all_files_can_be_accessed(files: Iterable[Path]) -> bool`:
        Checks if all LAZ files in the sampling geopackage can be accessed.

"""


from pathlib import Path
import tempfile
from typing import Optional, Union
import laspy
from laspy import LasData, LasHeader
from pdaltools.color import color
from geopandas import GeoDataFrame
import smbclient
from pacasam.connectors.connector import FILE_PATH_COLNAME, FILE_ID_COLNAME, GEOMETRY_COLNAME, PATCH_ID_COLNAME
from pacasam.extractors.extractor import Extractor, format_new_patch_path
from pacasam.samplers.sampler import SPLIT_COLNAME

# Optionally used: if the variable is given in the sampling it overrides the projection from the LAZ file.
# Necessary to handle situations where proj=None in the LAZ, which defaults to EPSG:9001 ("World") when
# pdaltools tries to infer the projection from the LAZ file.
SRID_LAZ_COLNAME = "srid"
EMPTY_STRING_TO_TELL_PDALTOOLS_TO_INFER_PROJ_FROM_LAZ_FILE = ""


class LAZExtractor(Extractor):
    """Extract a dataset of LAZ data patches."""

    patch_suffix: str = ".laz"

    def extract(self) -> None:
        """Performs extraction and colorization to a laz dataset.

        Uses pandas groupby to handle both single-file and multiple-file samplings.

        """
        for single_file_path, single_file_sampling in self.sampling.groupby(FILE_PATH_COLNAME):
            self.log.info(f"{self.name}: Extraction + Colorization from {single_file_path} (k={len(single_file_sampling)} patches)")
            self._extract_from_single_file(single_file_path, single_file_sampling)
            self.log.info(f"{self.name}: SUCCESS for {single_file_path}")

    def _extract_from_single_file(self, single_file_path: Path, single_file_sampling: GeoDataFrame):
        """Extract all patches from a single file based on its sampling."""
        if self.use_samba:
            with smbclient.open_file(single_file_path, mode="rb") as open_single_file:
                cloud = laspy.read(open_single_file)
        else:
            cloud = laspy.read(single_file_path)
        header = cloud.header
        for patch_info in single_file_sampling.itertuples():
            patch_bounds = getattr(patch_info, GEOMETRY_COLNAME).bounds
            file_id = getattr(patch_info, FILE_ID_COLNAME)
            tmp_nocolor_patch: tempfile._TemporaryFileWrapper = extract_single_patch_from_LasData(cloud, header, patch_bounds)
            colorized_patch: Path = format_new_patch_path(
                dataset_root_path=self.dataset_root_path,
                file_id=file_id,
                patch_id=getattr(patch_info, PATCH_ID_COLNAME),
                split=getattr(patch_info, SPLIT_COLNAME),
                patch_suffix=self.patch_suffix,
            )
            # Use given srid if possible, else pdaltools will infer it from the LAZ file.
            srid = getattr(patch_info, SRID_LAZ_COLNAME, None)
            colorize_single_patch(nocolor_patch=Path(tmp_nocolor_patch.name), colorized_patch=colorized_patch, srid=srid)


def extract_single_patch_from_LasData(cloud: LasData, header: LasHeader, patch_bounds) -> tempfile._TemporaryFileWrapper:
    """Extracts data from a single patch from a (laspy.LasData) cloud.

    Save to a tempfile since we will only keep colorized data, not this uncolorized data.

    Nota: using laspy and min/max conditions might not be efficient in case of many patches by file,
    but it is expected that only a few patches will be selected by file.
    Alternative could be using a KDTree.

    """
    new_patch_cloud = LasData(header)
    xmin, ymin, xmax, ymax = patch_bounds
    new_patch_cloud.points = cloud.points[(cloud.x >= xmin) & (cloud.x <= xmax) & (cloud.y >= ymin) & (cloud.y <= ymax)]

    patch_tmp_file: tempfile._TemporaryFileWrapper = tempfile.NamedTemporaryFile(
        suffix=".laz", prefix="extracted_patch_without_color_information"
    )
    new_patch_cloud.write(patch_tmp_file.name)
    return patch_tmp_file


def colorize_single_patch(nocolor_patch: Union[str, Path], colorized_patch: Union[str, Path], srid: Optional[int] = None) -> None:
    """Colorizes (RGBNIR) laz in a secure way to avoid corrupted files due to interruptions.

    By default, srid_str="" means that pdaltools infer the srid form the LAZ file directly.

    Wrapper to support Path objects since color does not accept Path objects, only strings as file paths.

    """
    # Special case: EPSG:0 is an invalid SRID, and we should infer from the LAZ.
    if srid is None or srid == 0:
        srid = EMPTY_STRING_TO_TELL_PDALTOOLS_TO_INFER_PROJ_FROM_LAZ_FILE

    if isinstance(nocolor_patch, str):
        nocolor_patch = Path(nocolor_patch)
    if isinstance(colorized_patch, str):
        colorized_patch = Path(colorized_patch)

    color(str(nocolor_patch.resolve()), str(colorized_patch.resolve()), proj=str(srid))
