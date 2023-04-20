from typing import Iterable
import geopandas as gpd

from pacasam.samplers.algos import sample_randomly, sample_spatially_by_slab
from pacasam.samplers.sampler import SELECTION_SCHEMA, Sampler


class RandomSampler(Sampler):
    """Random sampling - With option to exclude ids via current_selection_ids."""

    def get_tiles(self, **kwargs) -> gpd.GeoDataFrame:
        # TODO : put the predefined parameters as named elements in the signature, before **kwargs !
        # Same for SpatialSampler and others.
        current_selection_ids: Iterable = kwargs.get("current_selection_ids", set())
        num_to_sample: int = kwargs.get("num_to_sample", self.cf["num_tiles_in_sampled_dataset"])

        tiles = self.connector.request_all_other_tiles(exclude_ids=current_selection_ids)
        tiles = sample_randomly(tiles=tiles, num_to_sample=num_to_sample)
        self.log.info(f"RandomSampler: Completing with {num_to_sample} samples.")

        self._set_test_set_flag_inplace(tiles=tiles)
        tiles["sampler"] = self.name
        return tiles[SELECTION_SCHEMA]
