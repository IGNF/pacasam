from typing import Iterable
import geopandas as gpd

from pacasam.samplers.algos import sample_randomly, sample_spatially_by_slab
from pacasam.samplers.sampler import SELECTION_SCHEMA, Sampler


class SpatialSampler(Sampler):
    """Spatial sampling by slab - With option to exclude ids via current_selection_ids."""

    def get_tiles(self, num_to_sample: int = None, current_selection_ids: Iterable = {}, **kwargs) -> gpd.GeoDataFrame:
        # If num_to_sample was not defined, sample the full final dataset with this sampler.
        if not num_to_sample:
            num_to_sample = self.cf["target_total_num_tiles"]

        tiles = self.connector.request_all_other_tiles(exclude_ids=current_selection_ids)
        sampled_others = sample_spatially_by_slab(tiles, num_to_sample)
        self.log.info(f"SpatialSampler: Completing with {num_to_sample} samples.")

        self._set_validation_tiles_with_spatial_stratification(tiles=sampled_others)
        sampled_others["sampler"] = self.name
        return sampled_others[SELECTION_SCHEMA]
