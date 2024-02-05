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

    patch_suffix: str

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

    def make_new_patch_path(self, patch_id: int, split: str) -> Path:
        """Get path to save patch data, creating directories if needed."""
        newdir: Path = self.dataset_root_path / split
        newdir.mkdir(parents=True, exist_ok=True)
        patch_path = newdir / f"{split.upper()}-{patch_id}{self.patch_suffix}"
        return patch_path


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
