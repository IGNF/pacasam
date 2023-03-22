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
from pacasam.samplers.utils import drop_duplicates_by_id_and_log_sampling_attrition, load_optimization_config
from pacasam.utils import set_log_text_handler, setup_custom_logger
from pacasam.samplers.algos import fps, sample_randomly, sample_spatially_by_slab
from sklearn.preprocessing import QuantileTransformer

log = setup_custom_logger()

# PARAMETERS
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--connector", default="lipac", choices=["synthetic", "lipac"])

# TODO: add the sampling method for each tile.
SELECTION_SCHEMA = ["id", "is_test_set"]
TILE_INFO = ["id", "dalle_id", "geometry"]


class BaseSequential:
    name: str = "BaseSequential"

    def __init__(self, connector: Connector, optimization_config: Dict):
        self.connector = connector
        self.cf = optimization_config

    # TODO: have a sample method that use the three approaches successively. All output a geodataframe with SELECTION_SCHEMA
    def select_tiles(self) -> pd.Series:
        """Define a dataset as a GeoDataFrame with fields [id, is_test_set]."""

        targetted = self.get_targetted_tiles()
        targetted = drop_duplicates_by_id_and_log_sampling_attrition(log=log, gdf=targetted, sampling_name="Targeted Sampling")

        # Perform diversity sampling based on class histograms
        num_diverse_to_sample = (self.cf["num_tiles_in_sampled_dataset"] - len(targetted)) // 2  # half of remaining tiles
        if num_diverse_to_sample < 0:
            log.warning(
                f"Target dataset size of n={self.cf['num_tiles_in_sampled_dataset']} tiles achieved via targetted sampling single-handedly."
                "\n This means that the SUM OF CONSTRAINTS IS ABOVE 100%. Consider reducing constraints, and potentially having a bigger dataset."
            )
            return targetted

        diverse = self.get_diverse_tiles(num_to_sample=num_diverse_to_sample)
        diverse = drop_duplicates_by_id_and_log_sampling_attrition(log=log, gdf=diverse, sampling_name="Diversity Sampling")

        # add to the rest of the selection
        selection = pd.concat([targetted, diverse])

        # Complete the dataset with the other tiles
        num_tiles_to_complete = self.cf["num_tiles_in_sampled_dataset"] - len(selection)
        others = self.get_other_tiles(current_selection=selection, num_to_sample=num_tiles_to_complete)
        selection = pd.concat([selection, others])
        return selection

    def get_targetted_tiles(self):
        """Sample tiles by"""
        selection = []
        # Meet target requirements for each criterium
        for descriptor_name, descriptor_objectives in self._get_sorted_criteria().items():
            tiles = self._get_matching_tiles(descriptor_name, descriptor_objectives)
            selection += [tiles]
        selection = pd.concat(selection)
        return selection

    def _get_matching_tiles(self, descriptor_name: str, descriptor_objectives: Dict):
        """Query the tiles info based on a descriptor name + objective."""
        query = descriptor_objectives.get("where", f"{descriptor_name} > 0")
        tiles = connector.request_tiles_by_condition(where=query)
        num_samples_target = int(descriptor_objectives["target_min_samples_proportion"] * self.cf["num_tiles_in_sampled_dataset"])
        num_samples_to_sample = min(num_samples_target, len(tiles))  # cannot take more that there is.

        if self.cf["use_spatial_sampling"]:
            tiles = sample_spatially_by_slab(tiles, num_samples_to_sample)
        else:
            tiles = sample_randomly(tiles, num_samples_to_sample)

        log.info(
            f"Sampling: {descriptor_name} "
            f'| Target: {(descriptor_objectives["target_min_samples_proportion"])} (n={num_samples_target}). '
            f'| Found: {(num_samples_to_sample/self.cf["num_tiles_in_sampled_dataset"]):.03f} (n={num_samples_to_sample}) '
            f"| Query: {query}"
        )

        if num_samples_to_sample < num_samples_target:
            log.warning(f"Could not reach target for {descriptor_name}: not enough samples matching query in database.")

        self._set_test_set_flag_inplace(tiles=tiles)

        return tiles[SELECTION_SCHEMA]

    def get_diverse_tiles(self, num_to_sample: int):
        """We want to cover the space of class histogram, to include the most diverse scenes.
        Class histogram is a proxy for scene content. E.g. highly present building, quasi absent vegetation --> urban scene?
        We need to normalize each count of points to map them to class-specific notions from "absent" to "highly present".
        To do so we use quantiles computed on tiles where the class is present.
        We use a high number of quantiles so that signal is preserved between elements with close values.
        With q=50, we get for 4 classes 50**4 potential bins. Tests show on 100k tiles that most (>99%) are unique, so
        FPS will have the signal it requires to sample.

        NB: Rare classes are already targeted spatially via sequential sampling. Adding them here might give them a high weight...
        but may be done.

        # TODO: make this configurable in the optimization config.
        # Could be done with an API similar to the sequential one, with a num_quantile arg. Each
        # col can be obtained via a sql query (sum included),
        """

        # TODO: extract could be done in a single big sql formula, by chunk.
        # TODO: clean out the comments once this is stable
        extract = connector.extract(selection=None)
        # WARNING: Here we put everything in memory
        # TODO: Might not scale with more than 100k tiles ! we need to do this by chunk...
        # Or test with synthetic data, but we would need to create the fields.

        vegetation_columns = ["nb_points_vegetation_basse", "nb_points_vegetation_moyenne", "nb_points_vegetation_haute"]
        # Therefore we do not need to sample them by the amount of points.
        extract["nb_points_vegetation"] = extract[vegetation_columns].sum(axis=1)
        # TODO: get back medium and high vegetation, which are informative !!
        nb_points_cols = [
            "nb_points_sol",
            "nb_points_bati",
            "nb_points_non_classes",
            "nb_points_vegetation",
            # "nb_points_pont",
            # "nb_points_eau",
            # "nb_points_sursol_perenne",
        ]
        extract = extract[TILE_INFO + nb_points_cols]
        # 1/2 Set zeros as NaN to ignore them in the quantile transforms.
        extract = extract.replace(to_replace=0, value=np.nan)
        qt = QuantileTransformer(n_quantiles=50, random_state=0, subsample=100_000)
        # https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.QuantileTransformer.html

        extract.loc[:, nb_points_cols] = qt.fit_transform(extract[nb_points_cols].values)

        # 2/2 Set back zeros where they were.
        extract = extract.fillna(0)

        # Farthest Point Sampling
        # Set indices to a range to be sure that np indices = pandas indices.
        extract = extract.reset_index(drop=True)
        diverse_idx = fps(extract.loc[:, nb_points_cols].values, num_to_sample)
        diverse = extract.loc[diverse_idx, TILE_INFO]

        # Nice property of FPS: using it on its own output starting from the same
        # point would yield the same order. So we take the first n points as test_set
        # so that they are well distributed.
        num_samples_test_set = floor(self.cf["frac_test_set"] * len(diverse))
        diverse["is_test_set"] = 0
        diverse.loc[diverse.index[:num_samples_test_set], ("is_test_set",)] = 1

        return diverse[SELECTION_SCHEMA]

    def get_other_tiles(self, current_selection: gpd.GeoDataFrame, num_to_sample: int) -> gpd.GeoDataFrame:
        others = connector.request_all_other_tiles(exclude_ids=current_selection["id"])
        if self.cf["use_spatial_sampling"]:
            sampled_others = sample_spatially_by_slab(others, num_to_sample)
        else:
            sampled_others = sample_randomly(others, num_to_sample)
        log.info(f"Completing with {num_to_sample} samples.")
        self._set_test_set_flag_inplace(tiles=sampled_others)
        return sampled_others[SELECTION_SCHEMA]

    def _get_sorted_criteria(self):
        """Sort criteria target_min_samples_proportion.

        TODO: DECISION: This may be removed if having control over order is better...
        criteria is a dict {name: {where: sql_expression_not_used_now, target: float_value_to_reach}}
        """
        return dict(
            sorted(
                self.cf["criteria"].items(),
                key=lambda item: item[1]["target_min_samples_proportion"],
            )
        )

    def _set_test_set_flag_inplace(self, tiles: gpd.GeoDataFrame):
        """(Inplace) Set a binary flag for the test tiles, selected randomly or by slab."""
        num_samples_test_set = floor(self.cf["frac_test_set"] * len(tiles))

        if self.cf["use_spatial_sampling"]:
            test_ids = sample_spatially_by_slab(tiles, num_samples_test_set)["id"]
        else:
            test_ids = sample_randomly(tiles, num_samples_test_set)["id"]

        tiles["is_test_set"] = 0
        tiles.loc[tiles["id"].isin(test_ids), "is_test_set"] = 1


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
    sampler = BaseSequential(connector=connector, optimization_config=conf)
    outdir = Path(f"outputs/{connector.name}/")
    set_log_text_handler(log, outdir, log_file_name=sampler.name + ".log")

    # DEBUG:
    # # diverse = sampler.get_diverse_tiles(100)

    selection: gpd.GeoDataFrame = sampler.select_tiles()
    gdf = connector.extract(selection)
    gdf.to_file(outdir / f"{sampler.name}-{connector.name}-extract.gpkg")

    #     # Output dataset description
    #     # TODO: abstract this in another kind of stat object (perhaps in utils.py)
    bools = gdf.select_dtypes(include=np.number) > 0
    desc = bools.mean(numeric_only=True)
    desc.name = "prop_above_zero"
    desc.index.name = "attribute_name"
    desc.to_csv(outdir / f"{sampler.name}-stats_of_extract.csv", sep=";", index=True)
