from typing import Iterable
import geopandas as gpd

from pacasam.samplers.algos import sample_randomly, sample_spatially_by_slab
from pacasam.samplers.sampler import SELECTION_SCHEMA, Sampler


class RandomSampler(Sampler):
    """Random sampling - With option to exclude ids via current_selection_ids."""

    def get_tiles(self, num_to_sample: int = None, current_selection_ids: Iterable = {}, **kwargs) -> gpd.GeoDataFrame:
        # If num_to_sample was not defined, sample the full final dataset with this sampler.
        if not num_to_sample:
            num_to_sample = self.cf["target_total_num_tiles"]

        tiles = self.connector.request_all_other_tiles(exclude_ids=current_selection_ids)
        tiles = sample_randomly(tiles=tiles, num_to_sample=num_to_sample)
        self.log.info(f"RandomSampler: Completing with {num_to_sample} samples.")

        self._set_validation_tiles_with_spatial_stratification(tiles=tiles)
        tiles["sampler"] = self.name
        return tiles[SELECTION_SCHEMA]
