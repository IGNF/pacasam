import logging
from math import floor
import os
from pathlib import Path
import shutil
from typing import Dict, List, Union
import fiona
from geopandas import GeoDataFrame
from pacasam.samplers.algos import sample_with_stratification
from pacasam.connectors.connector import FILE_ID_COLNAME, PATCH_ID_COLNAME, Connector

# Schema of all DataFrame outputs of sampler.get_patches(...) calls.


# Created by samplers
SPLIT_COLNAME = "split"
SAMPLER_COLNAME = "sampler"


class Sampler:
    # Output schema of get_patches
    sampling_schema: List[str] = [
        PATCH_ID_COLNAME,  # unique identifier of a patch.
        SPLIT_COLNAME,  # Dataset split. Either train, val, or test.
        SAMPLER_COLNAME,  # Class name for the called sampler.
    ]

    def __init__(self, connector: Connector, sampling_config: Dict, log: logging.Logger = logging.getLogger(__name__)):
        self.name: str = self.__class__.__name__
        self.connector = connector
        self.cf = sampling_config
        self.log = log

    def get_patches(self, **kwargs) -> GeoDataFrame:
        """Get patches - output must have schema self.sampling_schema."""
        raise NotImplementedError("This is an abstract class. Use child class for specific sampling approaches.")

    def drop_duplicates_by_id_and_log_sampling_attrition(self, gdf: GeoDataFrame):
        n_sampled = len(gdf)
        gdf = gdf.drop_duplicates(subset=[PATCH_ID_COLNAME])
        n_distinct = len(gdf)
        self.log.info(f"{self.name}: {n_sampled} ids --> {n_distinct} distinct ids (uniqueness ratio: {n_distinct/n_sampled:.03f}) ")
        return gdf

    def _set_validation_patches_with_stratification(self, patches: GeoDataFrame, keys: Union[str, List[str]] = FILE_ID_COLNAME):
        """(Inplace) Set a binary flag for the validation patches, selected spatially by slab."""
        patches[SPLIT_COLNAME] = "test"
        if self.cf["frac_validation_set"] is not None:
            patches.loc[:, SPLIT_COLNAME] = "train"
            num_samples_val_set = floor(self.cf["frac_validation_set"] * len(patches))
            val_patches_ids = sample_with_stratification(patches, num_samples_val_set, keys=keys)[PATCH_ID_COLNAME]
            patches.loc[patches[PATCH_ID_COLNAME].isin(val_patches_ids), SPLIT_COLNAME] = "val"
        return patches


def save_gpd_to_any_filesystem(gdf: GeoDataFrame, gpkg_path: Path):
    """We need this because Fiona does not support saving directly to a mounted Samba store.
    We therefore need to save to the local filesystem and then copy the gpkg to its destination.

    Note: Any only means local filesystem or mounted store here.

    """
    try:
        gdf.to_file(gpkg_path)
    except fiona.errors.TransactionError:
        tmp_copy = f"outputs/samplings/TEMPORARY-{gpkg_path.name}"
        gdf.to_file(tmp_copy)
        shutil.copy(tmp_copy, gpkg_path)
        os.remove(tmp_copy)
