import geopandas as gpd
import pandas as pd
from typing import Dict
from pacasam.samplers.algos import sample_randomly, sample_spatially_by_slab
from pacasam.samplers.sampler import SELECTION_SCHEMA, Sampler


class TargettedSampler(Sampler):
    """A sampling to meet constraints - target prevalence of descriptor - sequentially."""

    def get_tiles(self) -> gpd.GeoDataFrame:
        selection = []
        # Meet target requirements for each criterium
        for descriptor_name, descriptor_objectives in self._get_sorted_criteria(self.cf["targets_for_TargettedSampler"]).items():
            tiles = self._get_matching_tiles(descriptor_name, descriptor_objectives)
            selection += [tiles]
        selection = pd.concat(selection)
        return selection

    def _get_matching_tiles(self, descriptor_name: str, descriptor_objectives: Dict):
        """Query the tiles info based on a descriptor name + objective."""
        query = descriptor_objectives.get("where", f"{descriptor_name} > 0")
        tiles = self.connector.request_tiles_by_condition(where=query)
        num_samples_target = int(descriptor_objectives["target_min_samples_proportion"] * self.cf["num_tiles_in_sampled_dataset"])
        num_samples_to_sample = min(num_samples_target, len(tiles))  # cannot take more that there is.

        tiles = sample_spatially_by_slab(tiles, num_samples_to_sample)

        self.log.info(
            f"Sampling: {descriptor_name} "
            f'| Target: {(descriptor_objectives["target_min_samples_proportion"])} (n={num_samples_target}). '
            f"| Query: {query}"
        )

        if num_samples_to_sample < num_samples_target:
            self.log.warning(
                f"Could not reach target for {descriptor_name}. "
                f"| Found: {(num_samples_to_sample/self.cf['num_tiles_in_sampled_dataset']):.03f} (n={num_samples_to_sample})."
            )

        self._set_test_set_flag_inplace(tiles=tiles)
        tiles["sampler"] = self.name
        return tiles[SELECTION_SCHEMA]

    def _get_sorted_criteria(self, criteria: Dict):
        """Sort criteria target_min_samples_proportion.

        TODO: DECISION: This may be removed if having control over order is better...
        criteria is a dict {name: {where: sql_expression_not_used_now, target: float_value_to_reach}}
        """
        return dict(
            sorted(
                criteria.items(),
                key=lambda item: item[1]["target_min_samples_proportion"],
            )
        )
