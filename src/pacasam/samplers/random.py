from typing import Iterable
import geopandas as gpd
from pacasam.connectors.connector import FILE_ID_COLNAME
from pacasam.samplers.algos import sample_randomly
from pacasam.samplers.sampler import Sampler


class RandomSampler(Sampler):
    """Random sampling - With option to exclude ids via current_selection_ids."""

    def get_patches(self, num_to_sample: int = None, current_selection_ids: Iterable = {}, **kwargs) -> gpd.GeoDataFrame:
        # If num_to_sample was not defined, sample the full final dataset with this sampler.
        if not num_to_sample:
            num_to_sample = self.cf["target_total_num_patches"]

        patches = self.connector.request_all_other_patches(exclude_ids=current_selection_ids)
        patches = sample_randomly(patches=patches, num_to_sample=num_to_sample)
        self.log.info(f"{self.name}: N={min(num_to_sample, len(patches))}/{num_to_sample} patches.")

        self._set_validation_patches_with_stratification(patches=patches, keys=[FILE_ID_COLNAME])
        patches["sampler"] = self.name
        return patches[self.sampling_schema]
