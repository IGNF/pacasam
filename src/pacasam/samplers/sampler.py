import logging
from math import floor
from typing import Dict, List, Union
from geopandas import GeoDataFrame
from pacasam.samplers.algos import sample_with_stratification
from pacasam.connectors.connector import Connector

# Schema of all DataFrame outputs of sampler.get_patches(...) calls.

# Needed for connector & extraction
FILE_COLNAME = "file_path"
GEOMETRY_COLNAME = "geometry"

# Needed for sampling
PATCH_ID_COLNAME = "id"
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
        gdf = gdf.drop_duplicates(subset=["id"])
        n_distinct = len(gdf)
        self.log.info(f"{self.name}: {n_sampled} ids --> {n_distinct} distinct ids (uniqueness ratio: {n_distinct/n_sampled:.03f}) ")
        return gdf

    def _set_validation_patches_with_stratification(self, patches: GeoDataFrame, keys: Union[str, List[str]]):
        """(Inplace) Set a binary flag for the validation patches, selected spatially by slab."""
        patches.loc[:, "split"] = "test"
        if self.cf["frac_validation_set"] is not None:
            patches.loc[:, "split"] = "train"
            num_samples_val_set = floor(self.cf["frac_validation_set"] * len(patches))
            val_patches_ids = sample_with_stratification(patches, num_samples_val_set, keys=keys)["id"]
            patches.loc[patches["id"].isin(val_patches_ids), "split"] = "val"
        return patches
