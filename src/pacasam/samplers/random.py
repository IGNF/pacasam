from typing import Iterable
import geopandas as gpd

from pacasam.samplers.algos import sample_randomly
from pacasam.samplers.sampler import SELECTION_SCHEMA, Sampler


class RandomSampler(Sampler):
    """Random sampling - With option to exclude ids via current_selection_ids."""

    def get_patches(self, num_to_sample: int = None, current_selection_ids: Iterable = {}, **kwargs) -> gpd.GeoDataFrame:
        # If num_to_sample was not defined, sample the full final dataset with this sampler.
        if not num_to_sample:
            num_to_sample = self.cf["target_total_num_patches"]

        patches = self.connector.request_all_other_patches(exclude_ids=current_selection_ids)
        patches = sample_randomly(patches=patches, num_to_sample=num_to_sample)
        self.log.info(f"RandomSampler: Completing with {num_to_sample} samples.")

        self._set_validation_patches_with_spatial_stratification(patches=patches)
        patches["sampler"] = self.name
        return patches[SELECTION_SCHEMA]
