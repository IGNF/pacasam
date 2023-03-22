"""Basic sampling for tests and defining an interface.

Sequential random selection to reach target.
Each selection independant from the previous one.
No spatial sampling nor any optimization.

"""

import sys
from pathlib import Path


directory = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(directory))

from math import floor
from typing import Any, Dict
import pandas as pd
import geopandas as gpd
import numpy as np

from pathlib import Path


from pacasam.connectors.lipac import load_LiPaCConnector
from pacasam.connectors.synthetic import SyntheticConnector
from pacasam.utils import set_log_text_handler, setup_custom_logger
from pacasam.samplers.utils import load_optimization_config
from pacasam.samplers.algos import sample_randomly, sample_spatially_by_slab

from pacasam.samplers.base import BaseSampling
from pacasam.samplers.completion import CompletionSampling
from pacasam.samplers.diverse import DiversitySampling
from pacasam.samplers.targetted import TargettedSampling

log = setup_custom_logger()

# PARAMETERS
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--connector", default="lipac", choices=["synthetic", "lipac"])


class TripleSampling(BaseSampling):
    """Succession of Targetted, Diversity, and Completion sampling."""

    def get_tiles(self) -> pd.Series:
        """Define a dataset as a GeoDataFrame with fields [id, is_test_set]."""
        ts = TargettedSampling(connector=self.connector, optimization_config=self.cf, log=self.log)
        targetted = ts.get_tiles()
        targetted = ts.drop_duplicates_by_id_and_log_sampling_attrition(targetted)

        # Perform diversity sampling based on class histograms
        num_diverse_to_sample = (self.cf["num_tiles_in_sampled_dataset"] - len(targetted)) // 2  # half of remaining tiles
        if num_diverse_to_sample < 0:
            self.log.warning(
                f"Target dataset size of n={self.cf['num_tiles_in_sampled_dataset']} tiles achieved via targetted sampling single-handedly."
                "\n This means that the SUM OF CONSTRAINTS IS ABOVE 100%. Consider reducing constraints, and potentially having a bigger dataset."
            )
            return targetted
        ds = DiversitySampling(connector=self.connector, optimization_config=self.cf, log=self.log)
        diverse = ds.get_tiles(num_to_sample=num_diverse_to_sample)
        diverse = ds.drop_duplicates_by_id_and_log_sampling_attrition(diverse)
        selection = pd.concat([targetted, diverse])

        # Complete the dataset with the other tiles
        num_tiles_to_complete = self.cf["num_tiles_in_sampled_dataset"] - len(selection)
        cs = CompletionSampling(connector=self.connector, optimization_config=self.cf, log=self.log)
        others = cs.get_tiles(current_selection=selection, num_to_sample=num_tiles_to_complete)
        selection = pd.concat([selection, others])

        return selection


# TODO: move this main to run.py, in parents dir?
if __name__ == "__main__":
    args = parser.parse_args()

    if args.connector == "synthetic":
        config_file = Path("configs/synthetic-optimization-config.yml")
        conf = load_optimization_config(config_file)
        connector = SyntheticConnector(**conf["connector_kwargs"])
    else:
        config_file = Path("configs/lipac-optimization-config.yml")
        conf = load_optimization_config(config_file)
        connector = load_LiPaCConnector(conf["connector_kwargs"])
    sampler = TripleSampling(connector=connector, optimization_config=conf, log=log)
    outdir = Path(f"outputs/{connector.name}/")
    set_log_text_handler(log, outdir, log_file_name=sampler.name + ".log")

    # DEBUG:
    # # diverse = sampler.get_diverse_tiles(100)

    selection: gpd.GeoDataFrame = sampler.get_tiles()
    gdf = connector.extract(selection)
    gdf.to_file(outdir / f"{sampler.name}-{connector.name}-extract.gpkg")

    #     # Output dataset description
    #     # TODO: abstract this in another kind of stat object (perhaps in utils.py)
    bools = gdf.select_dtypes(include=np.number) > 0
    desc = bools.mean(numeric_only=True)
    desc.name = "prop_above_zero"
    desc.index.name = "attribute_name"
    desc.to_csv(outdir / f"{sampler.name}-stats_of_extract.csv", sep=";", index=True)
