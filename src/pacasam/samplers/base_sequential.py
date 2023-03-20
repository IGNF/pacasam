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
from pacasam.utils import load_config, set_log_text_handler, setup_custom_logger

log = setup_custom_logger()

# PARAMETERS

# CONNECTOR_NAME = "synthetic"
CONNECTOR_NAME = "lipac"


class BaseSequential:
    name: str = "BaseSequential"

    def make_a_complying_dataset(self, connector: Connector, optimization_config: Dict):
        cf = optimization_config
        ids = []
        sorted_criteria = self._sort_criteria(cf["criteria"])
        for descriptor_name, descriptor_objectives in sorted_criteria.items():
            matching_ids = self.get_matching_ids(cf, connector, descriptor_name, descriptor_objectives)
            ids += [matching_ids]
        ids = pd.concat(ids)
        n_sampled = len(ids)
        ids = ids.drop_duplicates(subset=["id"])
        n_distinct = len(ids)
        log.info(f"Sampled {n_sampled} ids --> {n_distinct} distinct ids (redundancy ratio: {n_distinct/n_sampled:.03f}) ")

        # Complete with random sampling
        num_to_add_randomly = cf["num_tiles_in_sampled_dataset"] - len(ids)
        randomly_sampled_ids = connector.select_randomly_without_repetition(
            num_to_add_randomly=num_to_add_randomly, already_sampled_ids=ids
        )
        log.info(f"Completing with {num_to_add_randomly} samples.")
        ids = pd.concat([ids["id"], randomly_sampled_ids])
        return ids

    def get_matching_ids(self, cf, connector: Connector, descriptor_name: str, descriptor_objectives: Dict):
        # query the matching ids
        query = descriptor_objectives.get("where", f"{descriptor_name} > 0")
        matching_ids = connector.request_ids_by_condition(where=query)
        num_samples_target = int(descriptor_objectives["target_min_samples_proportion"] * cf["num_tiles_in_sampled_dataset"])
        num_samples_to_sample = min(num_samples_target, len(matching_ids))  # cannot take more that there is.

        if cf["use_spatial_sampling"]:
            sampled_matching_ids = self.sample_spatially_by_slab(matching_ids, num_samples_to_sample)
        else:
            sampled_matching_ids = self.sample_randomly(matching_ids, num_samples_to_sample)

        log.info(
            f"Sampling: {descriptor_name}"
            f'| Target: {(descriptor_objectives["target_min_samples_proportion"])} (n={num_samples_target}). '
            f'| Found: {(num_samples_to_sample/cf["num_tiles_in_sampled_dataset"]):.03f} (n={num_samples_to_sample})'
            f"| Query: {query}"
        )

        if num_samples_to_sample < num_samples_target:
            log.warning(f"Could not reach target for {descriptor_name}: not enough samples matching query in database.")

        return sampled_matching_ids

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

    def sample_randomly(self, matching_ids: gpd.GeoDataFrame, num_samples_to_sample: int):
        return matching_ids.sample(n=num_samples_to_sample, replace=False, random_state=1)

    def sample_spatially_by_slab(self, matching_ids: gpd.GeoDataFrame, num_samples_to_sample: int):
        """Efficient spatial sampling by sampling in each slab, iteratively.


        Args:
            matching_ids (gpd.GeoDataFrame): _description_
            num_samples_to_sample (int): _description_

        Returns:
            _type_: _description_
        """
        if len(matching_ids) == 0:
            return matching_ids
        # Step 1: start by sampling in each slab the minimal number of tiles by slab we would want.
        # Sample with replacement to avoid errors, dropping duplicates afterwards.
        # This leads us to be already close to our target num of samples.

        random_state = 0
        min_n_by_slab = floor(num_samples_to_sample / len(matching_ids["dalle_id"].unique()))
        min_n_by_slab = max(min_n_by_slab, 1)
        sampled_ids = matching_ids.groupby("dalle_id").sample(n=min_n_by_slab, random_state=random_state, replace=True)
        sampled_ids = sampled_ids.drop_duplicates(subset="id")

        # Step 2: Complete, accounting for slabs with a small number of tiles by removing the already selected
        # ones from the pool, and sampling one tile at each iteration.
        while len(sampled_ids) < num_samples_to_sample:
            random_state += 1
            remaining_ids = matching_ids[~matching_ids["id"].isin(sampled_ids["id"])]
            add_these_ids = remaining_ids.groupby("dalle_id").sample(n=1, random_state=random_state, replace=False)

            if len(add_these_ids) + len(sampled_ids) > num_samples_to_sample:
                add_these_ids = add_these_ids.sample(n=num_samples_to_sample - len(sampled_ids), random_state=random_state)

            sampled_ids = pd.concat([sampled_ids, add_these_ids])
            # sanity check
            sampled_ids_uniques = sampled_ids.drop_duplicates(subset=["id"])
            assert len(sampled_ids) == len(sampled_ids_uniques)
            sampled_ids = sampled_ids_uniques

        return sampled_ids


if __name__ == "__main__":
    sampler = BaseSequential()

    if CONNECTOR_NAME == "synthetic":
        config_file = Path("configs/synthetic-optimization-config.yml")
        optimization_config = load_config(config_file)
        connector = SyntheticConnector(**optimization_config["connector_kwargs"])
    else:
        config_file = Path("configs/lipac-optimization-config.yml")
        optimization_config = load_config(config_file)
        connector = load_LiPaCConnector(optimization_config["connector_kwargs"])

    outdir = Path(f"outputs/{CONNECTOR_NAME}/")
    set_log_text_handler(log, outdir, log_file_name=sampler.name + ".log")
    ids: pd.Series = sampler.make_a_complying_dataset(connector, optimization_config)
    gdf = connector.extract_using_ids(ids)
    gdf.to_file(outdir / f"{sampler.name}-{connector.name}-extract.gpkg")

    # Output dataset description
    # TODO: abstract this in another kind of stat object (perhaps in utils.py)
    bools = gdf.select_dtypes(include=np.number) > 0
    desc = bools.mean(numeric_only=True)
    desc.name = "prop_above_zero"
    desc.index.name = "attribute_name"
    desc.to_csv(outdir / f"{sampler.name}-stats_of_extract.csv", sep=";", index=True)
