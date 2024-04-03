import logging
from math import floor
from pathlib import Path
import shutil
import tempfile
from typing import Dict, List, Literal, Union
import warnings
from geopandas import GeoDataFrame
from pacasam.samplers.algos import sample_with_stratification
from pacasam.connectors.connector import FILE_ID_COLNAME, PATCH_ID_COLNAME, Connector

# Created by samplers
SPLIT_COLNAME = "split"
SPLIT_POSSIBLE_VALUES = Union[Literal["train"], Literal["test"], Literal["any"]]
SAMPLER_COLNAME = "sampler"


class Sampler:
    # Output schema of get_patches
    sampling_schema: List[str] = [
        PATCH_ID_COLNAME,  # unique identifier of a patch.
        SPLIT_COLNAME,  # Dataset split. Either train, val, or test.
        SAMPLER_COLNAME,  # Class name for the called sampler.
    ]

    def __init__(
        self,
        connector: Connector,
        sampling_config: Dict,
        log: logging.Logger = logging.getLogger(),
    ):
        self.name: str = self.__class__.__name__
        self.connector = connector
        self.cf = sampling_config
        self.log = log

    def get_patches(self, **kwargs) -> GeoDataFrame:
        """Get patches - output must have schema self.sampling_schema."""
        raise NotImplementedError("This is an abstract class. Use child class for specific sampling approaches.")

    def drop_duplicates_by_id_and_log_sampling_attrition(self, gdf: GeoDataFrame):
        if not len(gdf):
            return gdf
        n_sampled = len(gdf)
        gdf = gdf.drop_duplicates(subset=[PATCH_ID_COLNAME])
        n_distinct = len(gdf)
        self.log.info(f"{self.name}: {n_sampled} ids --> {n_distinct} distinct ids (uniqueness ratio: {n_distinct/n_sampled:.03f}) ")
        return gdf

    def _set_validation_patches_with_stratification(self, patches: GeoDataFrame, keys: Union[str, List[str]] = FILE_ID_COLNAME):
        """(Inplace) Set a binary flag for the validation patches, selected spatially by slab."""
        patches[SPLIT_COLNAME] = "test"
        if self.cf["frac_validation_set"]:
            patches.loc[:, SPLIT_COLNAME] = "train"
            num_samples_val_set = floor(self.cf["frac_validation_set"] * len(patches))
            val_patches_ids = sample_with_stratification(patches, num_samples_val_set, keys=keys)[PATCH_ID_COLNAME]
            patches.loc[patches[PATCH_ID_COLNAME].isin(val_patches_ids), SPLIT_COLNAME] = "val"
        return patches


def save_gpd_to_any_filesystem(gdf: GeoDataFrame, gpkg_path: Path):
    """Save the gpd in a way that is compatible with samba filesystems.

    We need this because Fiona does not support saving directly to a mounted Samba store.
    We therefore save to the local filesystem and then copy the gpkg to its destination.
    We use copy instead of moving because moving from local filesystem to samba store is not supported.
    Additionnaly, we need to catch a false positive from geopandas/fiona, which do not recognize that the
    file extension is "gpkg" since we are using the file handle instead of its name.

    We make this temp+copy the default behavior since trying to establish a connection is longer and then catch
    an exception (fiona.errors.TransactionError) takes longer than writing + copy.
    Also trying to catch the exception does not always work, and lead to another exceptions:
        "fiona._err.CPLE_AppDefinedError: b'sqlite3_exec(COMMIT) failed: database is locked'"

    cf. https://github.com/r-spatial/sf/issues/628#issuecomment-364004859 on this issue.

    """

    with tempfile.NamedTemporaryFile(suffix=".gpkg", prefix="tmp_geopackage") as tmp_copy:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            gdf.to_file(tmp_copy)
        shutil.copy(tmp_copy.name, gpkg_path)
