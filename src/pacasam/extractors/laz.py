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
│   ├── {input_laz_stem---patch_id}.laz
├── val/
│   ├── {input_laz_stem---patch_id}.laz
├── test/
│   ├── {input_laz_stem---patch_id}.laz

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
import laspy
from laspy import LasData
from pdaltools.color import decomp_and_color
from geopandas import GeoDataFrame
from pacasam.connectors.connector import FILE_COLNAME, GEOMETRY_COLNAME
from pacasam.extractors.extractor import Extractor, format_new_patch_path


class LAZExtractor(Extractor):
    """Extract a dataset of LAZ data patches."""

    def extract(self) -> None:
        """Main extraction function.

        Uses pandas groupby to handle both single-file and multiple-file samplings.

        """
        for single_file_path, single_file_sampling in self.sampling.groupby(FILE_COLNAME):
            self._extract_from_single_file(single_file_path, single_file_sampling)

    def _extract_from_single_file(self, single_file_path: Path, single_file_sampling: GeoDataFrame):
        self.log.info(f"{self.name}: Extraction + Colorization from {single_file_path} (k={len(single_file_sampling)} patches)")

        cloud = laspy.read(single_file_path)
        header = cloud.header

        for patch_info in single_file_sampling.itertuples():
            tmp_nocolor_patch: Path = extract_single_patch_from_LasData(cloud, header, patch_info)
            colorized_patch: Path = format_new_patch_path(self.dataset_root_path, single_file_path, patch_info)
            colorize_single_patch(nocolor_patch=tmp_nocolor_patch, colorized_patch=colorized_patch)

        self.log.info(f"{self.name}: SUCCESS for {single_file_path}")


def extract_single_patch_from_LasData(cloud: LasData, header, patch_info) -> Path:
    """Extracts data from a single patch from a (laspy.LasData) cloud..

    Save to a tempfile since we will only keep colorized data, not this uncolorized data.

    Nota: using laspy and min/max conditions might not be efficient in case of many patches by file,
    but it is expected that only a few patches will be selected by file.
    Alternative could be using a KDTree.

    """
    polygon = getattr(patch_info, GEOMETRY_COLNAME)
    new_patch_cloud = LasData(header)
    xmin, ymin, xmax, ymax = polygon.bounds
    new_patch_cloud.points = cloud.points[(cloud.x >= xmin) & (cloud.x <= xmax) & (cloud.y >= ymin) & (cloud.y <= ymax)]

    new_patch_path = tempfile.NamedTemporaryFile(suffix=".laz", prefix="extracted_patch_without_color_information")
    new_patch_cloud.write(new_patch_path)
    return new_patch_path


def colorize_single_patch(nocolor_patch: Path, colorized_patch: Path) -> None:
    """Colorizes (RGBNIR) laz in a secure way to avoid corrupted files due to interruptions.

    Wrapper to support Path objects since decomp_and_color does not accept Path objects, only strings as file paths.

    """
    decomp_and_color(str(nocolor_patch), str(colorized_patch))
