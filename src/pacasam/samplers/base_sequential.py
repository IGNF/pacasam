"""Basic sampling for tests and defining an interface.

Sequential random selection to reach target. 
Each selection independant from the previous one.
No spatial sampling nor any optimization.

"""

import sys
from pathlib import Path

directory = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(directory))

from typing import Dict
import pandas as pd
import numpy as np

import geopandas as gpd
import yaml
from pathlib import Path


from pacasam.connectors.lipac import LiPaCConnector, load_LiPaCConnector
from pacasam.connectors.synthetic import Connector, SyntheticConnector
from pacasam.utils import set_log_text_handler, setup_custom_logger

log = setup_custom_logger()


class BaseSequential:
    name: str = "BaseSequential"
    # TODO: adding a spatial sampling -> matching_ids.sample(...), and select_randomly_without_repetition
    # Could be methods of the BaseSequential, with a "spatial" argument each...
    # Seems not needed for now, may be needed with way larger input database.
    # See that when we have the full Lipac DB OR use synthetic data --> easier inspection...

    def sample(self, connector: Connector, optimization_config: Dict):
        cf = optimization_config

        ids = []
        # sort criteria
        # criteria is a dict {name: {where: sql_expression_not_used_now, target: float_value_to_reach}}
        cf["criteria"] = self._sort_criteria(cf["criteria"])
        for descriptor_name, descriptor_objectives in cf["criteria"].items():
            # direct addition to start with
            matching_ids = connector.request_ids_where_above_zero(descriptor_name)
            num_samples_target = int(descriptor_objectives["target_min_samples_proportion"] * cf["num_tiles_in_sampled_dataset"])
            num_samples_found = min(num_samples_target, len(matching_ids))  # cannot take more that there is.
            # random sampling independant of previous selection, with duplicates dropped later.
            matching_ids = matching_ids.sample(num_samples_found, random_state=1)
            log.info(
                f'Descriptor: {descriptor_name}. Target: {(descriptor_objectives["target_min_samples_proportion"]):.02f} (n={num_samples_target}).'
                f'Found: {(num_samples_found/cf["num_tiles_in_sampled_dataset"]):.02f} (n={num_samples_found})'
            )
            if num_samples_found < num_samples_target:
                log.warning(f"Could not reach target for indicateur {descriptor_name}")
            ids += [matching_ids]
        ids = pd.concat(ids)
        n = len(ids)
        log.info(f"Sampled {n} ids to reach descriptors targets.")
        ids = ids.drop_duplicates()
        n_distinct = len(ids)
        log.info(f"Corresponds to {n_distinct} distinct ids (concentration ratio: {n_distinct/n})")

        # Complete with random sampling
        num_to_add_randomly = cf["num_tiles_in_sampled_dataset"] - len(ids)
        randomly_sampled_ids = connector.select_randomly_without_repetition(
            num_to_add_randomly=num_to_add_randomly, already_sampled_ids=ids
        )
        log.info(f"Completing with {num_to_add_randomly} samples.")
        # We get rid of the geometries here, as we will make a real later right after.
        # TODO: see if we can get rid of geometries earlier, after having performed spatial sampling...

        ids = pd.concat([ids["id"], randomly_sampled_ids])
        return ids

    def _sort_criteria(self, criteria):
        return dict(
            sorted(
                criteria.items(),
                key=lambda item: item[1]["target_min_samples_proportion"],
            )
        )


if __name__ == "__main__":
    sampler = BaseSequential()
    # Choose database to use:
    # DATABASE_NAME = "synthetic"
    DATABASE_NAME = "lipac"

    if DATABASE_NAME == "synthetic":
        config_file = Path("configs/synthetic-optimization-config.yml")
        with open(config_file, "r") as file:
            optimization_config = yaml.safe_load(file)

        outdir = Path("outputs/synthetic/")
        set_log_text_handler(log, outdir, log_file_name=sampler.name + ".log")
        connector = SyntheticConnector(**optimization_config["connector_kwargs"])
    else:
        config_file = Path("configs/toy-lipac-optimization-config.yml")
        with open(config_file, "r") as file:
            optimization_config = yaml.safe_load(file)

        outdir = Path("outputs/lipac/")
        set_log_text_handler(log, outdir, log_file_name=sampler.name + ".log")
        connector = load_LiPaCConnector(optimization_config["connector_kwargs"])

    ids: pd.Series = sampler.sample(connector, optimization_config)
    gdf = connector.extract_using_ids(ids)
    gdf.to_file(outdir / f"{sampler.name}-{connector.name}-extract.gpkg")

    # Output dataset description
    bools = gdf.select_dtypes(include=np.number) > 0
    desc = bools.mean(numeric_only=True)
    desc.name = "prop_above_zero"
    desc.index.name = "attribute_name"
    desc.to_csv(outdir / f"{sampler.name}-stats_of_extract.csv", sep=";", index=True)
