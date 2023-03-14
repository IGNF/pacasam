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


# TODO: create an interface object
class BaseSequential:
    name: str = "BaseSequential"

    def sample(self, connector: Connector, optimization_config: Dict):
        cf = optimization_config

        ids = []
        # criteria is a dict {name: {where: sql_expression_not_used_now, target: float_value_to_reach}}
        for descriptor_name, descriptor_objectives in cf["criteria"].items():
            # direct addition to start with
            matching_ids = connector.request_ids_where_above_zero(descriptor_name)
            num_samples = int(descriptor_objectives["target_min_samples_proportion"] * cf["num_tiles_in_sampled_dataset"])
            num_samples_possibles = min(num_samples, len(matching_ids))  # cannot take more that there is.
            # random sampling independant of previous selection, with duplicates dropped later.
            matching_ids = matching_ids.sample(num_samples_possibles, random_state=1)
            log.info(
                f'Descriptor: {descriptor_name}. Target: {(descriptor_objectives["target_min_samples_proportion"]):.02f} (n={num_samples}).'
                f'Found: {(num_samples_possibles/cf["num_tiles_in_sampled_dataset"]):.02f} (n={num_samples_possibles})'
            )
            ids += [matching_ids]
        ids = pd.concat(ids)
        n = len(ids)
        log.info(f"Sampled {n} ids to reach descriptors targets.")
        ids = ids.drop_duplicates()
        n_distinct = len(ids)
        log.info(f"Corresponds to {n_distinct} distinct ids (concentration ratio: {n_distinct/n})")

        # Complete with random sampling
        num_to_add_randomly = cf["num_tiles_in_sampled_dataset"] - len(ids)
        log.info(f"Completing with {num_to_add_randomly} samples.")
        randomly_sampled_ids = connector.select_randomly_without_repetition(
            num_to_add_randomly=num_to_add_randomly, already_sampled_ids=ids
        )
        ids = pd.concat([ids, randomly_sampled_ids])

        return ids


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
        connector = SyntheticConnector(**optimization_config["kwargs"])
    else:
        config_file = Path("configs/toy-lipac-optimization-config.yml")
        with open(config_file, "r") as file:
            optimization_config = yaml.safe_load(file)

        outdir = Path("outputs/lipac/")
        set_log_text_handler(log, outdir, log_file_name=sampler.name + ".log")
        connector = load_LiPaCConnector()

    ids: pd.Series = sampler.sample(connector, optimization_config)
    gdf = connector.extract_using_ids(ids)

    # Output dataset description
    bools = gdf.select_dtypes(include=np.number) > 0
    desc = bools.mean(numeric_only=True)
    desc.to_csv(outdir / f"{sampler.name}-prevalences.csv", sep=";", index=True)
