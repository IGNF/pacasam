import logging
import geopandas as gpd
import pandas as pd
from typing import Dict
from pacasam.connectors.connector import FILE_ID_COLNAME, Connector, PATCH_ID_COLNAME
from pacasam.samplers.algos import sample_with_stratification
from pacasam.samplers.sampler import Sampler
from pacasam.samplers.spatial import SpatialSampler


class TargettedSampler(Sampler):
    """A sampling to meet constraints - target prevalence of descriptor - sequentially.

    Sampling is completed with spatial sampling if not enough patches are found.

    """

    def __init__(
        self,
        connector: Connector,
        sampling_config: Dict,
        log: logging.Logger = logging.getLogger(__name__),
        complete_with_spatial_sampling: bool = True,
    ):
        self.complete_with_spatial_sampling = complete_with_spatial_sampling
        super().__init__(connector, sampling_config, log)

    def get_patches(self) -> gpd.GeoDataFrame:
        selection = []
        # Meet target requirements for each criterium
        targets = self.cf["TargettedSampler"]["targets"]
        for descriptor_name, descriptor_objectives in self.sorted_targets(targets).items():
            patches = self._get_matching_patches(descriptor_name, descriptor_objectives)
            selection += [patches]
        selection = pd.concat(selection, ignore_index=True)
        selection = self.drop_duplicates_by_id_and_log_sampling_attrition(selection)
        self.log.info(f"{self.name}: N={len(selection)} distinct patches selected to match TargettedSampler requirements.")

        if len(selection) > self.cf["target_total_num_patches"]:
            self.log.warning(
                f"Selected more than the desired total of N={self.cf['target_total_num_patches']}."
                "If this is not desired, please reconsider your targets."
            )
        elif self.complete_with_spatial_sampling:
            num_patches_to_complete = self.cf["target_total_num_patches"] - len(selection)
            ss = SpatialSampler(connector=self.connector, sampling_config=self.cf, log=self.log)
            completion = ss.get_patches(num_to_sample=num_patches_to_complete, current_selection_ids=selection[PATCH_ID_COLNAME])
            selection = pd.concat([selection, completion])
            self.log.info(f"{self.name}: completed targetted sampling with N={num_patches_to_complete} additional patches.")

        return selection

    def _get_matching_patches(self, descriptor_name: str, descriptor_objectives: Dict):
        """Query the patches info based on a descriptor name + objective."""

        patches = self.connector.request_patches_by_boolean_indicator(descriptor_name)
        num_samples_target = int(descriptor_objectives["target_min_samples_proportion"] * self.cf["target_total_num_patches"])
        num_samples_to_sample = min(num_samples_target, len(patches))  # cannot take more that there is.

        patches = sample_with_stratification(patches, num_samples_to_sample, keys=[FILE_ID_COLNAME])

        self.log.info(
            f"TargettedSampler: {descriptor_name} "
            f'| Target: {(descriptor_objectives["target_min_samples_proportion"])} (n={num_samples_target}). '
        )

        if num_samples_to_sample < num_samples_target:
            self.log.warning(
                f"Could not reach target for {descriptor_name}. "
                f"| Found: {(num_samples_to_sample/self.cf['target_total_num_patches']):.03f} (n={num_samples_to_sample})."
            )

        patches["sampler"] = self.name
        self._set_validation_patches_with_stratification(patches=patches, keys=[FILE_ID_COLNAME])
        return patches[self.sampling_schema]

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
