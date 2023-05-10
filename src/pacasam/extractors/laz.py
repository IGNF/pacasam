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


import logging
from pathlib import Path
from typing import Generator, Iterable
from geopandas import GeoDataFrame
import laspy
from pdaltools.color import decomp_and_color

from pacasam.connectors.connector import FILE_COLNAME, GEOMETRY_COLNAME
from pacasam.extractors.extractor import Extractor, format_new_patch_path, load_sampling_with_checks


class LAZExtractor(Extractor):
    """Extract a dataset of LAZ data patches."""

    def make_dataset(self) -> None:
        """Main extraction function. Handles both single-file and multiple-file samplings."""

        for single_file_path, single_file_sampling in self.sampling.groupby(FILE_COLNAME):
            self.log.info(f"{self.name}: Extraction + Colorization from {single_file_path} (k={len(single_file_sampling)} patches)")
            new_patches_generator = extract_patches_from_single_cloud(
                single_file_path=single_file_path, single_file_sampling=single_file_sampling, dataset_root_path=self.dataset_root_path
            )
            for extracted_laz_path in new_patches_generator:
                colorize_single_patch(extracted_laz_path)
            self.log.info(f"{self.name}: SUCCESS for {single_file_path}")


def extract_patches_from_single_cloud(
    single_file_path: Path, single_file_sampling: GeoDataFrame, dataset_root_path: Path
) -> Generator[Path]:
    """Extract the patches of data from the sampling of a single LAZ.

    Nota: using laspy and min/max conditions might not be efficient in case of many patches by file,
    but it is expected that only a few patches will be selected by file.
    Alternative could be using a KDTree.

    TODO: we use geom.bounds --> make explicit that bbox are expected, and that extraction only supports rectangular geometries

    """
    cloud = laspy.read(single_file_path)
    header = cloud.header

    for patch_info in single_file_sampling.itertuples():
        # TODO: could be replaced by a tmp file here, so that it is easier to make sure everything was properly colorized later.
        new_patch_path = format_new_patch_path(dataset_root_path, single_file_path, patch_info)

        polygon = getattr(patch_info, GEOMETRY_COLNAME)
        new_patch_cloud = laspy.LasData(header)
        xmin, ymin, xmax, ymax = polygon.bounds
        new_patch_cloud.points = cloud.points[(cloud.x >= xmin) & (cloud.x <= xmax) & (cloud.y >= ymin) & (cloud.y <= ymax)]
        new_patch_cloud.write(new_patch_path)

        yield new_patch_path


def colorize_single_patch(path_of_patch_data: Path) -> None:
    """Colorization, in a secure way to avoid corrupted files due to interruptions."""
    # TODO Use a tmp file first for colorization, replace afterward, to avoid unwanted deletion...

    # Note: decomp_and_color does not accept Path objects, only strings as file paths.
    tmp_colorized_patch_path = path_of_patch_data.with_suffix(".laz.tmp_colorization")
    decomp_and_color(str(path_of_patch_data), str(tmp_colorized_patch_path))
    #
