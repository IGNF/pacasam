"""
This module provides functions to extract patches of lidar data from a sampling geopackage 
with columns 'split', 'geometry', and 'file_path' (to a LAZ file, which is a point cloud lidar format) 
into a directory structure like:

/dataset_path/
    /train/
        {input_laz_basename__without_suffix---patch_id}.laz
    /val/
    /test/

Functions:
    - `extract_lidar_patches`: Extracts patches of lidar data and saves them to files under the dataset path
      using the provided split ratios for train, validation, and test datasets
    - `extract_lidar_patches_end_to_end`: Provides an end-to-end function to extract lidar patches from a 
      sampling geopackage file and save them to disk using the provided dataset path.

"""
from pathlib import Path
from typing import Iterable
import geopandas as gpd
from shapely import Polygon

# TODO: have a unified structure for the key columns of a sampling, keep it DRY
LAZ_FILE_COLNAME = "laz_path"
PATCH_ID_COLNAME = "id"
SPLIT_COLNAME = "split"


def extract_dataset_from_sampling(sampling_path: Path, dataset_root_path: Path) -> None:
    sampling = load_sampling_df_with_checks(sampling_path)
    paths_of_extracted_patches = extract_patches_from_all_clouds(sampling, dataset_root_path)
    colorize_all_patches(paths_of_extracted_patches)


def extract_patches_from_single_cloud(sampling: gpd.GeoDataFrame, dataset_root_path: Path) -> Iterable[Path]:
    # sanity check to be sure this function is properly used (i.e. for a single cloud)
    assert sampling[LAZ_FILE_COLNAME].nunique() == 1
    laz_path = sampling[LAZ_FILE_COLNAME].iloc[0]

    # read LAZ file and create an octree. Or use pdal. dunno...

    list_of_extracted_path = []
    for patch_info in sampling.itertuples():
        # where to save patch data
        patch_path = define_patch_path_for_extraction(dataset_root_path, laz_path, patch_info)

        # TODO: extract and save to patch_path to patch_path

        list_of_extracted_path += [patch_path]
    return list_of_extracted_path


# TODO: we could even impose laz format in a global fashion, or las (for dataloading speed...).
def define_patch_path_for_extraction(dataset_root_path, laz_path, patch_info):
    """Formats the path to save the patch data. Creates dataset dir and split subdir(s) as needed.
    Format is /{dataset_root_path}/{split}/{laz_path_stem}---{zfilled patch_id}.laz

    The suffix is always lowercase for consistency across patches extractions.

    """
    split = getattr(patch_info, SPLIT_COLNAME)
    patch_id = getattr(patch_info, PATCH_ID_COLNAME)
    dir_to_save_patch: Path = dataset_root_path / split
    dir_to_save_patch.mkdir(parents=True, exist_ok=True)
    patch_path = dir_to_save_patch / f"{laz_path.stem}---{str(patch_id).zfill(4)}{laz_path.suffix.lower()}"
    return patch_path


def extract_patches_from_all_clouds(sampling: gpd.GeoDataFrame, dataset_root_path: Path) -> Iterable[Path]:
    # TODO: add some paralellization at the file level.
    # TODO: consider using generators, to enable streamlined colorization afterward.
    paths_of_extracted_patches = []
    for key, sampling_of_single_file in sampling.groupby(LAZ_FILE_COLNAME):
        extracted = extract_patches_from_single_cloud(
            sampling_of_single_file,
            dataset_root_path,
        )
        paths_of_extracted_patches += extracted
    return paths_of_extracted_patches


def colorize_all_patches(paths_of_extracted_patches: Iterable[Path]) -> None:
    for path in paths_of_extracted_patches:
        colorize_single_patch(path)


def colorize_single_patch(path_of_patch_data: Path) -> None:
    # Use a tmp file first for colorization, replace afterward, to avoid unwanted deletion...
    ...


# READING


def load_sampling_df_with_checks(sampling_path: Path) -> gpd.GeoDataFrame:
    sampling = gpd.read_file(sampling_path, converters={LAZ_FILE_COLNAME: Path})
    sampling[LAZ_FILE_COLNAME] = sampling[LAZ_FILE_COLNAME].apply(Path)
    check_sampling_format(sampling)
    assert all_files_can_be_accessed(sampling[LAZ_FILE_COLNAME])
    return sampling


def check_sampling_format(sampling: gpd.GeoDataFrame) -> None:
    """
    Check if the geopackage file follows the expected format.

    Args:
    - sampling (gpd.GeoDataFrame): A geopandas dataframe containing columns "split", "geometry" and LAZ_FILE_COLNAME.

    Returns:
    - None

    Raises:
    - ValueError: If any of the required columns is missing or has an incorrect format.

    """
    required_columns = ["split", "geometry", LAZ_FILE_COLNAME]
    for col in required_columns:
        if col not in sampling.columns:
            raise ValueError(f"Column '{col}' missing from the sampling dataframe")

    if not isinstance(sampling["split"].iloc[0], str):
        raise ValueError("Column 'split' should be a string")

    if not isinstance(sampling["geometry"].iloc[0], Polygon):
        raise ValueError("Column 'geometry' should be a geometry column")


def all_files_can_be_accessed(files: Iterable[Path]) -> bool:
    return all(Path(f).exists() for f in files)
