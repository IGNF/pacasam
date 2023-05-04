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
    - `read_sampling_file`: Reads the geopandas dataframe from the sampling geopackage file
    - `check_sampling_file`: Performs checks on the sampling geopackage dataframe to ensure it is valid
    - `extract_lidar_patches`: Extracts patches of lidar data and saves them to files under the dataset path
      using the provided split ratios for train, validation, and test datasets
    - `extract_lidar_patches_end_to_end`: Provides an end-to-end function to extract lidar patches from a 
      sampling geopackage file and save them to disk using the provided dataset path.

"""

from pathlib import Path
from typing import Iterable
import geopandas as gpd
from shapely import Polygon


def load_sampling_df(sampling_path: Path):
    df = gpd.read_file(sampling_path)
    # perform some checks
    check_sampling_format(df)
    assert all_files_can_be_accessed(df[LAZ_FILE_COLNAME])
    return df


LAZ_FILE_COLNAME = "laz_path"


def check_sampling_format(df: gpd.GeoDataFrame) -> None:
    """
    Check if the geopackage file follows the expected format.

    Args:
    - df (gpd.GeoDataFrame): A geopandas dataframe containing columns "split", "geometry" and LAZ_FILE_COLNAME.

    Returns:
    - None

    Raises:
    - ValueError: If any of the required columns is missing or has an incorrect format.

    """
    required_columns = ["split", "geometry", LAZ_FILE_COLNAME]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' missing from the sampling dataframe")

    if not isinstance(df["split"].iloc[0], str):
        raise ValueError("Column 'split' should be a string")

    if not isinstance(df["geometry"].iloc[0], Polygon):
        raise ValueError("Column 'geometry' should be a geometry column")


def all_files_can_be_accessed(files: Iterable[Path]):
    return all(Path(f).exists() for f in files)
