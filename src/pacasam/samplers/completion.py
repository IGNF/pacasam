import geopandas as gpd

from pacasam.samplers.algos import sample_randomly, sample_spatially_by_slab
from pacasam.samplers.sampler import SELECTION_SCHEMA, Sampler


class CompletionSampler(Sampler):
    """A sampling to complete a dataset, excluding a current selection by their ids."""

    def get_tiles(self, current_selection: gpd.GeoDataFrame, num_to_sample: int) -> gpd.GeoDataFrame:
        others = self.connector.request_all_other_tiles(exclude_ids=current_selection["id"])
        if self.cf["use_spatial_sampling"]:
            sampled_others = sample_spatially_by_slab(others, num_to_sample)
        else:
            sampled_others = sample_randomly(others, num_to_sample)
        self.log.info(f"Completing with {num_to_sample} samples.")
        self._set_test_set_flag_inplace(tiles=sampled_others)
        return sampled_others[SELECTION_SCHEMA]
