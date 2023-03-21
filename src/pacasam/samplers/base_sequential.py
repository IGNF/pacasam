"""Basic sampling for tests and defining an interface.

Sequential random selection to reach target.
Each selection independant from the previous one.
No spatial sampling nor any optimization.

"""

from math import floor
import sys
from pathlib import Path


directory = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(directory))

from typing import Dict
import pandas as pd
import geopandas as gpd
import numpy as np

from pathlib import Path


from pacasam.connectors.lipac import load_LiPaCConnector
from pacasam.connectors.synthetic import Connector, SyntheticConnector
from pacasam.samplers.utils import load_optimization_config
from pacasam.utils import set_log_text_handler, setup_custom_logger
from pacasam.samplers.algos import sample_randomly, sample_spatially_by_slab

log = setup_custom_logger()

# PARAMETERS

CONNECTOR_NAME = "synthetic"
# CONNECTOR_NAME = "lipac"


class BaseSequential:
    name: str = "BaseSequential"

    def select_tiles(self, connector: Connector, optimization_config: Dict) -> pd.Series:
        """Define a dataset as a GeoDataFrame with fields [id, is_test_set]."""

        cf = optimization_config
        selection = []
        # Meet target requirements for each criterium
        sorted_criteria = self._sort_criteria(cf["criteria"])
        for descriptor_name, descriptor_objectives in sorted_criteria.items():
            tiles = self.get_matching_tiles(cf, connector, descriptor_name, descriptor_objectives)
            self._set_test_set_flag(tiles=tiles, frac_test_set=cf["frac_test_set"], use_spatial_sampling=cf["use_spatial_sampling"])
            selection += [tiles]
        selection = pd.concat(selection)

        # some logs
        n_sampled = len(selection)
        selection = selection.drop_duplicates(subset=["id"])
        n_distinct = len(selection)
        log.info(f"Sampled {n_sampled} ids --> {n_distinct} distinct ids (redundancy ratio: {n_distinct/n_sampled:.03f}) ")

        # Complete the dataset with the other tiles
        num_tiles_to_complete = cf["num_tiles_in_sampled_dataset"] - len(selection)
        sampled_others = self.get_other_tiles(cf=cf, connector=connector, selection=selection, num_to_sample=num_tiles_to_complete)
        self._set_test_set_flag(tiles=sampled_others, frac_test_set=cf["frac_test_set"], use_spatial_sampling=cf["use_spatial_sampling"])
        selection = pd.concat([selection[["id", "is_test_set"]], sampled_others[["id", "is_test_set"]]])
        return selection

    def _set_test_set_flag(
        self,
        tiles: gpd.GeoDataFrame,
        frac_test_set: float,
        use_spatial_sampling: bool = True,
    ):
        """(Inplace) Set a binary flag for the test tiles, selected randomly."""
        # TODO: decide if the config should be accessible as attribute of the class instead of a config param.
        num_samples_test_set = floor(frac_test_set * len(tiles))

        if use_spatial_sampling:
            test_ids = sample_spatially_by_slab(tiles, num_samples_test_set)["id"]
        else:
            test_ids = sample_randomly(tiles, num_samples_test_set)["id"]

        tiles["is_test_set"] = 0
        tiles.loc[tiles["id"].isin(test_ids), "is_test_set"] = 1

    def get_matching_tiles(self, cf, connector: Connector, descriptor_name: str, descriptor_objectives: Dict):
        # query the matching ids
        query = descriptor_objectives.get("where", f"{descriptor_name} > 0")
        tiles = connector.request_tiles_by_condition(where=query)
        num_samples_target = int(descriptor_objectives["target_min_samples_proportion"] * cf["num_tiles_in_sampled_dataset"])
        num_samples_to_sample = min(num_samples_target, len(tiles))  # cannot take more that there is.

        if cf["use_spatial_sampling"]:
            tiles = sample_spatially_by_slab(tiles, num_samples_to_sample)
        else:
            tiles = sample_randomly(tiles, num_samples_to_sample)

        log.info(
            f"Sampling: {descriptor_name} "
            f'| Target: {(descriptor_objectives["target_min_samples_proportion"])} (n={num_samples_target}). '
            f'| Found: {(num_samples_to_sample/cf["num_tiles_in_sampled_dataset"]):.03f} (n={num_samples_to_sample}) '
            f"| Query: {query}"
        )

        if num_samples_to_sample < num_samples_target:
            log.warning(f"Could not reach target for {descriptor_name}: not enough samples matching query in database.")

        return tiles

    def get_other_tiles(self, cf: Dict, connector: Connector, selection: gpd.GeoDataFrame, num_to_sample: int) -> gpd.GeoDataFrame:
        others = connector.request_all_other_tiles(exclude=selection)
        if cf["use_spatial_sampling"]:
            sampled_others = sample_spatially_by_slab(others, num_to_sample)
        else:
            sampled_others = sample_randomly(others, num_to_sample)
        log.info(f"Completing with {num_to_sample} samples.")
        return sampled_others

    def _sort_criteria(self, criteria):
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


if __name__ == "__main__":
    sampler = BaseSequential()

    if CONNECTOR_NAME == "synthetic":
        config_file = Path("configs/synthetic-optimization-config.yml")
        conf = load_optimization_config(config_file)
        connector = SyntheticConnector(**conf["connector_kwargs"])
    else:
        config_file = Path("configs/lipac-optimization-config.yml")
        conf = load_optimization_config(config_file)
        connector = load_LiPaCConnector(conf["connector_kwargs"])

    outdir = Path(f"outputs/{CONNECTOR_NAME}/")
    set_log_text_handler(log, outdir, log_file_name=sampler.name + ".log")
    selection: gpd.GeoDataFrame = sampler.select_tiles(connector, conf)
    gdf = connector.extract(selection)
    gdf.to_file(outdir / f"{sampler.name}-{connector.name}-extract.gpkg")

    # Output dataset description
    # TODO: abstract this in another kind of stat object (perhaps in utils.py)
    bools = gdf.select_dtypes(include=np.number) > 0
    desc = bools.mean(numeric_only=True)
    desc.name = "prop_above_zero"
    desc.index.name = "attribute_name"
    desc.to_csv(outdir / f"{sampler.name}-stats_of_extract.csv", sep=";", index=True)
