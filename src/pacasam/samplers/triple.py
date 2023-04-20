import pandas as pd

from pacasam.samplers.sampler import Sampler
from pacasam.samplers.spatial import SpatialSampler
from pacasam.samplers.diversity import DiversitySampler
from pacasam.samplers.targetted import TargettedSampler


class TripleSampler(Sampler):
    """Succession of Targetted, Diversity, and Completion sampling."""

    def get_tiles(self) -> pd.Series:
        ts = TargettedSampler(connector=self.connector, optimization_config=self.cf, log=self.log)
        targetted = ts.get_tiles()
        targetted = ts.drop_duplicates_by_id_and_log_sampling_attrition(targetted)

        # Perform diversity sampling based on class histograms
        num_diverse_to_sample = (self.cf["target_total_num_tiles"] - len(targetted)) // 2  # half of remaining tiles
        if num_diverse_to_sample < 0:
            self.log.warning(
                f"Target dataset size of n={self.cf['target_total_num_tiles']} tiles achieved via targetted sampling single-handedly."
                "\n This means the SUM OF CONSTRAINTS IS ABOVE 100%. Consider reducing constraints, and having a bigger dataset."
            )
            return targetted

        ds = DiversitySampler(connector=self.connector, optimization_config=self.cf, log=self.log)
        diverse = ds.get_tiles(num_diverse_to_sample=num_diverse_to_sample)
        diverse = ds.drop_duplicates_by_id_and_log_sampling_attrition(diverse)
        selection = pd.concat([targetted, diverse])

        # Complete the dataset with the other tiles
        num_tiles_to_complete = self.cf["target_total_num_tiles"] - len(selection)
        cs = SpatialSampler(connector=self.connector, optimization_config=self.cf, log=self.log)
        others = cs.get_tiles(current_selection_ids=selection["id"], num_to_sample=num_tiles_to_complete)
        selection = pd.concat([selection, others])

        return selection
