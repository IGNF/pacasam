import warnings
import pandas as pd
from pacasam.connectors.connector import PATCH_ID_COLNAME
from pacasam.samplers.sampler import Sampler
from pacasam.samplers.spatial import SpatialSampler
from pacasam.samplers.diversity import DiversitySampler
from pacasam.samplers.targetted import TargettedSampler


class TripleSampler(Sampler):
    """Succession of Targetted, Diversity, and Completion sampling."""

    def get_patches(self) -> pd.Series:
        ts = TargettedSampler(connector=self.connector, sampling_config=self.cf, log=self.log, complete_with_spatial_sampling=False)
        targetted = ts.get_patches()
        targetted = ts.drop_duplicates_by_id_and_log_sampling_attrition(targetted)

        # Perform diversity sampling based on class histograms
        num_to_sample = (self.cf["target_total_num_patches"] - len(targetted)) // 2  # half of remaining patches
        if num_to_sample < 0:
            warnings.warns(
                f"Target dataset size of n={self.cf['target_total_num_patches']} patches achieved via targetted sampling single-handedly."
                "\n This means the SUM OF CONSTRAINTS IS ABOVE 100%. Consider reducing constraints, and having a bigger dataset."
            )
            return targetted

        ds = DiversitySampler(connector=self.connector, sampling_config=self.cf, log=self.log)
        diverse = ds.get_patches(num_to_sample=num_to_sample)
        selection = pd.concat([targetted, diverse])
        selection = ds.drop_duplicates_by_id_and_log_sampling_attrition(selection)

        # Complete the dataset with the other patches
        num_patches_to_complete = self.cf["target_total_num_patches"] - len(selection)
        cs = SpatialSampler(connector=self.connector, sampling_config=self.cf, log=self.log)
        others = cs.get_patches(current_selection_ids=selection[PATCH_ID_COLNAME], num_to_sample=num_patches_to_complete)
        selection = pd.concat([selection, others])
        # sanity deduplication, just in case
        selection = self.drop_duplicates_by_id_and_log_sampling_attrition(selection)

        return selection
