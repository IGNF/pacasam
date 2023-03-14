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
import geopandas as gpd
import yaml
from pathlib import Path


from pacasam.connectors.postgresql import PostgreSQLConnector
from pacasam.connectors.synthetic import Connector, SyntheticConnector
from pacasam.utils import set_log_text_handler, setup_custom_logger

log = setup_custom_logger()


# TODO: create an interface object
class BaseSequential:
    # def __init__(self) -> None:

    def sample(self, connector: Connector, optimization_config: Dict):
        cf = optimization_config

        ids = []
        # criteria is a dict {name: {where: sql_expression_not_used_now, target: float_value_to_reach}}
        for descriptor_name, descriptor_objectives in cf["criteria"].items():
            # direct addition to start with
            matching_ids = connector.request_ids_where_above_zero(descriptor_name)
            num_samples = int(descriptor_objectives["target_min_samples_proportion"] * cf["target_size_num_samples"])
            num_samples = min(num_samples, len(matching_ids))  # cannot take more that there is.
            # random sampling independant of previous selection, with duplicates dropped later.
            matching_ids = matching_ids.sample(num_samples, random_state=1)
            ids += [matching_ids]
        ids = pd.concat(ids)
        n = len(ids)
        log.info(f"Sampled {n} ids to reach descriptors targets.")
        ids = ids.drop_duplicates()
        n_distinct = len(ids)
        log.info(f"Corresponds to {n_distinct} distinct ids (concentration ratio: {n_distinct/n})")

        # Complete with random sampling
        num_to_add_randomly = cf["target_size_num_samples"] - len(ids)
        log.info(f"Completing with {num_to_add_randomly} samples.")
        randomly_sampled_ids = connector.select_randomly_without_repetition(
            num_to_add_randomly=num_to_add_randomly, already_sampled_ids=ids
        )
        ids = pd.concat([ids, randomly_sampled_ids])

        return ids


# All samplers can be run with the synthetic dataset.
# This is where we developp the workflow : checks, messages...


def run_base_sequential_sampling(connector_class, config_file: Path) -> gpd.GeoDataFrame:
    with open(config_file, "r") as file:
        optimization_config = yaml.safe_load(file)

    connector: Connector = connector_class(**optimization_config["kwargs"])
    sampler = BaseSequential()
    ids: pd.Series = sampler.sample(connector, optimization_config)
    return connector.extract_using_ids(ids)


if __name__ == "__main__":
    # outdir = Path("outputs/synthetic/")
    # set_log_text_handler(log, outdir)
    # gdf = run_base_sequential_sampling(SyntheticConnector, Path("configs/synthetic-optimization-config.yml"))

    outdir = Path("outputs/postgresql/")
    set_log_text_handler(log, outdir)
    gdf = run_base_sequential_sampling(PostgreSQLConnector, Path("configs/toy-lipac-optimization-config.yml"))

    desc = gdf.mean(numeric_only=True)
    desc.to_csv(outdir / "base_sequential_means.csv", sep=";", index=True)
