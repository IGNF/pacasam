import logging
import os
from pathlib import Path
from typing import Iterable
from geopandas import GeoDataFrame
import geopandas as gpd
from shapely import Polygon
import smbclient
from tqdm import tqdm
from pacasam.connectors.connector import FILE_ID_COLNAME, FILE_PATH_COLNAME

ZFILL_MAX_PATCH_NUMBER = 7  # patch id consistent below 10M patches (i.e. up to 9_999_999 patches)
DEFAULT_SRID_LAMBERT93 = "2154"  # Assume Lambert93 if we cannot infer srid from sampling or data itself


class Extractor:
    """Abstract class defining extractor interface."""

    def __init__(self, log: logging.Logger, sampling_path: Path, dataset_root_path: Path, use_samba: bool = False, n_jobs: int = 1):
        """Initializes the extractor. Always loads the sampling with sanity checks on format."""
        self.log = log
        self.name: str = self.__class__.__name__
        self.dataset_root_path = dataset_root_path
        self.n_jobs = n_jobs  # parallelization
        # Wether to use samba client or use the local filesystem.
        if use_samba:
            set_smb_client_singleton()
        self.sampling = load_sampling_with_checks(sampling_path=sampling_path, use_samba=use_samba)
        self.use_samba = use_samba

    def extract(self):
        raise NotImplementedError("Abstract class.")


def set_smb_client_singleton() -> None:
    """Instantiates the Samba ClientConfig object.

    Note that smbclient.ClientConfig is a singleton and we do not need to pass it to further processes.
    For more information see: https://pypi.org/project/smbprotocol/

    """
    if ("SAMBA_USERNAME" not in os.environ) or ("SAMBA_PASSWORD" not in os.environ):
        raise KeyError("Either SAMBA_USERNAME or SAMBA_PASSWORD were not exported, but you are using samba (USE_SAMBA is not null).")
    smb_username = os.getenv("SAMBA_USERNAME")
    smb_password = os.getenv("SAMBA_PASSWORD")
    smbclient.ClientConfig(username=smb_username, password=smb_password)


# READING SAMPLINGS


def load_sampling_with_checks(sampling_path: Path, use_samba: bool = False) -> GeoDataFrame:
    """Load a sampling, with useful checks on format and file existence.

    If use_samba=True, checks will know that the files are in a samba store.

    """
    sampling = load_sampling(sampling_path)
    check_sampling_format(sampling)
    unique_file_paths = sampling[FILE_PATH_COLNAME].unique()
    if use_samba:
        check_all_files_exist_in_samba_filesystem(unique_file_paths)
    else:
        check_all_files_exist_in_default_filesystem(unique_file_paths)
    return sampling


def load_sampling(sampling_path: Path) -> GeoDataFrame:
    """Loads a sampling."""
    sampling: GeoDataFrame = gpd.read_file(sampling_path)
    sampling[FILE_PATH_COLNAME] = sampling[FILE_PATH_COLNAME].apply(Path)
    return sampling


def check_sampling_format(sampling: GeoDataFrame) -> None:
    """Checks if the geopackage file follows the expected format.

    Args:
    - sampling (GeoDataFrame): A geopandas dataframe containing columns "split", "geometry" and FILE_PATH_COLNAME.

    Returns:
    - None

    Raises:
    - ValueError: If any of the required columns is missing or has an incorrect format.

    """
    required_columns = ["split", "geometry", FILE_PATH_COLNAME, FILE_ID_COLNAME]
    for col in required_columns:
        if col not in sampling.columns:
            raise ValueError(f"Column '{col}' missing from the sampling dataframe")

    if not isinstance(sampling["split"].iloc[0], str):
        raise TypeError("Column 'split' should be a string")

    if not isinstance(sampling["geometry"].iloc[0], Polygon):
        raise TypeError("Column 'geometry' should be a geometry column")


def check_all_files_exist_in_default_filesystem(paths: Iterable[Path]):
    """Raises an informative error if some file(s) cannot be reached."""
    files_not_found = [str(p) for p in paths if not p.exists()]
    if files_not_found:
        raise_explicit_FileNotFoundError(files_not_found)


def raise_explicit_FileNotFoundError(files_not_found):
    if len(files_not_found) > 10:  # truncate for readibility
        files_not_found = files_not_found[:5] + ["..."] + files_not_found[-5:]
    files_not_found_str = "\n".join(files_not_found)
    raise FileNotFoundError(f"Expected files to exists and be accessible: \n{files_not_found_str}")


def check_all_files_exist_in_samba_filesystem(paths: Iterable[Path]):
    files_not_found = []
    for p in tqdm(paths, unit="Samba file", desc="Checking Samba file existence."):
        try:
            with smbclient.open_file(p, mode="rb") as f:
                ...
        except FileNotFoundError:
            files_not_found += [str(f)]
    if files_not_found:
        raise_explicit_FileNotFoundError(files_not_found)


# WRITING


def format_new_patch_path(dataset_root_path: Path, file_id: str, patch_id: int, split: str, patch_suffix: str) -> Path:
    """Formats the path to save the patch data. Creates dataset dir and split subdir(s) as needed.
    Format is /{dataset_root_path}/{split}/{file_path_stem}---{zfilled patch_id}.laz

    The suffix is not infered from input data for consistency across extractions, for instance when
    there are both las and laz files.

    """
    dir_to_save_patch: Path = dataset_root_path / split
    dir_to_save_patch.mkdir(parents=True, exist_ok=True)
    patch_path = dir_to_save_patch / f"{split.upper()}-file-{file_id}-patch-{str(patch_id).zfill(ZFILL_MAX_PATCH_NUMBER)}{patch_suffix}"  # noqa
    return patch_path
