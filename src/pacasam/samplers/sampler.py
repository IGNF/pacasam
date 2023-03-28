import logging
from math import floor
from typing import Dict
import geopandas as gpd

from pacasam.samplers.algos import sample_randomly, sample_spatially_by_slab
from pacasam.connectors.connector import Connector

SELECTION_SCHEMA = ["id", "is_test_set", "sampler"]
TILE_INFO = ["id", "dalle_id"]
# need the geometrie for sql requests.
TILE_INFO_SQL = '"' + '", "'.join(TILE_INFO + ["geometrie"]) + '"'


class Sampler:
    def __init__(self, connector: Connector, optimization_config: Dict, log: logging.Logger = logging.getLogger(__name__)):
        self.name: str = self.__class__.__name__
        self.connector = connector
        self.cf = optimization_config
        self.log = log

    def get_tiles(self, *args, **kwargs) -> gpd.GeoDataFrame:
        """Get tiles - output must have schema SELECTION_SCHEMA."""
        raise NotImplementedError("This is an abstract class. use child class for specific sampling approaches.")

    def drop_duplicates_by_id_and_log_sampling_attrition(self, gdf: gpd.GeoDataFrame):
        n_sampled = len(gdf)
        gdf = gdf.drop_duplicates(subset=["id"])
        n_distinct = len(gdf)
        self.log.info(f"{self.name}: {n_sampled} ids --> {n_distinct} distinct ids (redundancy ratio: {n_distinct/n_sampled:.03f}) ")
        return gdf

    def _set_test_set_flag_inplace(self, tiles: gpd.GeoDataFrame):
        """(Inplace) Set a binary flag for the test tiles, selected randomly or by slab."""
        num_samples_test_set = floor(self.cf["frac_test_set"] * len(tiles))

        if self.cf["use_spatial_sampling"]:
            test_ids = sample_spatially_by_slab(tiles, num_samples_test_set)["id"]
        else:
            test_ids = sample_randomly(tiles, num_samples_test_set)["id"]

        tiles["is_test_set"] = 0
        tiles.loc[tiles["id"].isin(test_ids), "is_test_set"] = 1
