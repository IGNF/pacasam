import geopandas as gpd
import pandas as pd
from typing import Dict
from pacasam.samplers.algos import sample_spatially_by_slab
from pacasam.samplers.sampler import SELECTION_SCHEMA, Sampler


class TargettedSampler(Sampler):
    """A sampling to meet constraints - target prevalence of descriptor - sequentially."""

    def get_tiles(self) -> gpd.GeoDataFrame:
        selection = []
        # Meet target requirements for each criterium
        targets = self.cf["TargettedSampler"]["targets"]
        for descriptor_name, descriptor_objectives in self.sorted_targets(targets).items():
            tiles = self._get_matching_tiles(descriptor_name, descriptor_objectives)
            selection += [tiles]
        selection = pd.concat(selection)
        if len(selection) > self.cf["target_total_num_tiles"]:
            self.log.warning(
                f"{self.name}: selected N={len(selection)} patches."
                f"This is higher than the desired total of N={self.cf['target_total_num_tiles']}."
                "If this is not desired, please reconsider your targets."
            )
        return selection

    def _get_matching_tiles(self, descriptor_name: str, descriptor_objectives: Dict):
        """Query the tiles info based on a descriptor name + objective."""

        tiles = self.connector.request_tiles_by_boolean_indicator(descriptor_name)
        num_samples_target = int(descriptor_objectives["target_min_samples_proportion"] * self.cf["target_total_num_tiles"])
        num_samples_to_sample = min(num_samples_target, len(tiles))  # cannot take more that there is.

        tiles = sample_spatially_by_slab(tiles, num_samples_to_sample)

        self.log.info(
            f"TargettedSampler: {descriptor_name} "
            f'| Target: {(descriptor_objectives["target_min_samples_proportion"])} (n={num_samples_target}). '
        )

        if num_samples_to_sample < num_samples_target:
            self.log.warning(
                f"Could not reach target for {descriptor_name}. "
                f"| Found: {(num_samples_to_sample/self.cf['target_total_num_tiles']):.03f} (n={num_samples_to_sample})."
            )

        self._set_validation_tiles_with_spatial_stratification(tiles=tiles)
        tiles["sampler"] = self.name
        return tiles[SELECTION_SCHEMA]

    def sorted_targets(self, criteria: Dict):
        """Sort criteria target_min_samples_proportion.

        Criteria is a dict {name: {where: sql_expression_not_used_now, target: float_value_to_reach}}

        """
        return dict(
            sorted(
                criteria.items(),
                key=lambda item: item[1]["target_min_samples_proportion"],
            )
        )
