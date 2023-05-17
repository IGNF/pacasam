import logging
from pathlib import Path
from typing import Iterable
from geopandas import GeoDataFrame
import geopandas as gpd
from shapely import Polygon

from pacasam.connectors.connector import FILE_COLNAME


class Extractor:
    """Abstract class defining extractor interface.

    Nota: could this be an interface directly?

    """

    def __init__(self, log: logging.Logger, sampling_path: Path, dataset_root_path: Path):
        """Initialization of extractor. Always load the sampling with sanity checks on format."""
        self.name: str = self.__class__.__name__
        self.log = log
        self.dataset_root_path = dataset_root_path
        self.sampling = load_sampling_with_checks(sampling_path)

    def extract(self):
        raise NotImplementedError("Abstract class.")


# READING SAMPLINGS


def load_sampling_with_checks(sampling_path: Path) -> GeoDataFrame:
    """General function to load a sampling, with useful checks."""
    sampling: GeoDataFrame = gpd.read_file(sampling_path, converters={FILE_COLNAME: Path})
    sampling[FILE_COLNAME] = sampling[FILE_COLNAME].apply(Path)
    check_sampling_format(sampling)
    check_all_files_exist(sampling[FILE_COLNAME])
    return sampling


def check_sampling_format(sampling: GeoDataFrame) -> None:
    """
    Check if the geopackage file follows the expected format.

    Args:
    - sampling (GeoDataFrame): A geopandas dataframe containing columns "split", "geometry" and LAZ_FILE_COLNAME.

    Returns:
    - None

    Raises:
    - ValueError: If any of the required columns is missing or has an incorrect format.

    """
    required_columns = ["split", "geometry", FILE_COLNAME]
    for col in required_columns:
        if col not in sampling.columns:
            raise ValueError(f"Column '{col}' missing from the sampling dataframe")

    if not isinstance(sampling["split"].iloc[0], str):
        raise TypeError("Column 'split' should be a string")

    if not isinstance(sampling["geometry"].iloc[0], Polygon):
        raise TypeError("Column 'geometry' should be a geometry column")


def check_all_files_exist(files: Iterable[Path]):
    """Raise an informative error if some file(s) cannot be reached."""
    files_not_found = [str(f) for f in files if not Path(f).exists()]
    if files_not_found:
        files_not_found_str = "\n".join(files_not_found)
        raise FileNotFoundError(f"Expected files to exists and be accessible: \n{files_not_found_str}")


# WRITING


# ALternativeley : keeping the full filename may be more informative?
def format_new_patch_path(dataset_root_path: Path, file_path: Path, patch_id: int, split: str, patch_suffix: str) -> Path:
    """Formats the path to save the patch data. Creates dataset dir and split subdir(s) as needed.
    Format is /{dataset_root_path}/{split}/{file_path_stem}---{zfilled patch_id}.laz

    The suffix is not infered from input data for consistency across extractions, for instance when
    there are both las and laz files.

    """
    dir_to_save_patch: Path = dataset_root_path / split
    dir_to_save_patch.mkdir(parents=True, exist_ok=True)
    patch_path = dir_to_save_patch / f"{split.upper()}-{file_path.stem}-patch_{str(patch_id).zfill(4)}{patch_suffix}"
    return patch_path
