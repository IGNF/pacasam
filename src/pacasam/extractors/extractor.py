import logging
from pathlib import Path
from typing import Iterable
from geopandas import GeoDataFrame
import geopandas as gpd
from shapely import Polygon


DEFAULT_SRID_LAMBERT93 = "2154"  # Assume Lambert93 if we cannot infer srid from sampling or data itself


class Extractor:
    """Abstract class defining extractor interface.

    All extractors support parallelization with mpire.
    All extractors support resuming extraction without duplication of computations: patches are only extracted
    if they do not yet exist, and extraction operations are atomic at the patch level.
    """

    def __init__(self, log: logging.Logger, sampling_path: Path, dataset_root_path: Path, num_jobs: int = 1):
        """Initializes the extractor. Always loads the sampling with sanity checks on format."""
        self.log = log
        self.name: str = self.__class__.__name__
        self.dataset_root_path = dataset_root_path
        self.sampling = load_sampling(sampling_path=sampling_path)
        check_sampling_format(self.sampling)
        self.num_jobs = num_jobs

    def extract(self):
        raise NotImplementedError("Abstract class.")


# READING SAMPLINGS


def load_sampling(sampling_path: Path) -> GeoDataFrame:
    """Loads a sampling."""
    sampling: GeoDataFrame = gpd.read_file(sampling_path)
    return sampling


def check_sampling_format(sampling: GeoDataFrame) -> None:
    """Checks if the geopackage file follows the expected format.

    Args:
    - sampling (GeoDataFrame): A geopandas dataframe containing columns "split", "geometry", in the right format.

    Returns:
    - None

    Raises:
    - ValueError: If any of the required columns is missing or has an incorrect format.

    """
    required_columns = ["split", "geometry"]
    for col in required_columns:
        if col not in sampling.columns:
            raise ValueError(f"Column '{col}' missing from the sampling dataframe")

    if not isinstance(sampling["split"].iloc[0], str):
        raise TypeError("Column 'split' should be a string")

    if not isinstance(sampling["geometry"].iloc[0], Polygon):
        raise TypeError("Column 'geometry' should be a geometry column")


def check_all_files_exist(paths: Iterable[str]):
    """Raises an informative error if some file(s) cannot be reached."""
    files_not_found = [p for p in paths if not Path(p).exists()]
    if files_not_found:
        raise_explicit_FileNotFoundError(files_not_found)


def raise_explicit_FileNotFoundError(files_not_found):
    if len(files_not_found) > 10:  # truncate for readibility
        files_not_found = files_not_found[:5] + ["..."] + files_not_found[-5:]
    files_not_found_str = "\n".join(files_not_found)
    raise FileNotFoundError(f"Expected files to exist and be accessible: \n{files_not_found_str}")


# WRITING


# TODO: move to laz.py since this is specific to laz extraction.
def format_new_patch_path(dataset_root_path: Path, patch_id: int, split: str, patch_suffix: str) -> Path:
    """Formats the path to save the patch data. Creates dataset dir and split subdir(s) as needed.
    Format is /{dataset_root_path}/{split}/{SPLIT}-{zfilled patch_id}.laz

    The suffix is not infered from input data for consistency across extractions, for instance when
    there are both las and laz files.

    """
    dir_to_save_patch: Path = dataset_root_path / split
    dir_to_save_patch.mkdir(parents=True, exist_ok=True)
    patch_path = dir_to_save_patch / f"{split.upper()}-{patch_id}{patch_suffix}"  # noqa
    return patch_path
