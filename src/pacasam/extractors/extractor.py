import logging
from pathlib import Path
from typing import Iterable, Optional
from geopandas import GeoDataFrame
import geopandas as gpd
from shapely import Polygon
from dataclasses import dataclass
import smbclient
import yaml
from tqdm import tqdm
from pacasam.connectors.connector import FILE_COLNAME

ZFILL_MAX_PATCH_NUMBER = 7  # patch id consistent below 10M patches (i.e. up to 9_999_999 patches)


@dataclass
class SambaCredentials:
    SMB_LOGIN: str
    SMB_DOMAIN: str
    SMB_PASSWORD: str


class Extractor:
    """Abstract class defining extractor interface.

    Nota: could this be an interface directly?

    """

    def __init__(self, log: logging.Logger, sampling_path: Path, dataset_root_path: Path, use_samba: bool = False):
        """Initialization of extractor. Always load the sampling with sanity checks on format."""
        self.name: str = self.__class__.__name__
        self.log = log
        self.dataset_root_path = dataset_root_path
        # Wether to use samba client or use the local filesystem.
        self.use_samba = use_samba
        self.sampling = load_sampling_with_checks(sampling_path=sampling_path, use_samba=self.use_samba)

    def extract(self):
        raise NotImplementedError("Abstract class.")


def set_smb_client_singleton(smb_client_config: Optional[Path]) -> None:
    """Instantiates the Samba ClientConfig object from a credentials yaml file.

    When samba_client_credentials=None, it means the files are local and we will use the defautl file system
    during extraction.

    Note that smbclient.ClientConfig is a singleton and we do not need to pass it to further processes.
    For more information see: https://pypi.org/project/smbprotocol/

    """
    if smb_client_config:
        with open(smb_client_config, "r") as f:
            cf = yaml.safe_load(f)
        smb_username = cf["SMB_USERNAME"]
        smb_password = cf["SMB_PASSWORD"]
        smbclient.ClientConfig(username=smb_username, password=smb_password)


# READING SAMPLINGS


def load_sampling_with_checks(sampling_path: Path, use_samba: bool = False) -> GeoDataFrame:
    """Load a sampling, with useful checks on format and file existence.

    If use_smbclient=True, checks will know that the files are in a samba store.

    """
    sampling = load_sampling(sampling_path)
    check_sampling_format(sampling)
    unique_file_paths = sampling[FILE_COLNAME].unique()
    if use_samba:
        check_all_files_exist_in_samba_filesystem(unique_file_paths)
    else:
        check_all_files_exist_in_default_filesystem(unique_file_paths)
    return sampling


def load_sampling(sampling_path: Path) -> GeoDataFrame:
    """Load a sampling"""
    sampling: GeoDataFrame = gpd.read_file(sampling_path, converters={FILE_COLNAME: Path})
    # TODO: this seocnd line seems redundant. Check if actually needed, remove elsewise.
    sampling[FILE_COLNAME] = sampling[FILE_COLNAME].apply(Path)
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
    # files_not_found = [str(p) for p in paths if not smbclient.path.exists(p)]
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
    patch_path = dir_to_save_patch / f"{split.upper()}-file-{file_id}-patch-{str(patch_id).zfill(ZFILL_MAX_PATCH_NUMBER)}{patch_suffix}"
    return patch_path
