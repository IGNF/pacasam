import sys
from pathlib import Path
import numpy as np
import geopandas as gpd

directory = Path(__file__).resolve().parent.parent
sys.path.append(str(directory))
from pacasam.utils import CONNECTORS_LIBRARY, SAMPLERS_LIBRARY, set_log_text_handler, load_optimization_config, setup_custom_logger

log = setup_custom_logger()

# PARAMETERS
import argparse

parser = argparse.ArgumentParser()
POSSIBLE_CONFIGS = ["configs/lipac-optimization-config.yml", "configs/synthetic-optimization-config.yml"]
parser.add_argument("--config_file", default="configs/lipac-optimization-config.yml", choices=POSSIBLE_CONFIGS)

parser.add_argument("--connector_class", default="LiPaCConnector", choices=CONNECTORS_LIBRARY.keys())
parser.add_argument("--sampler_class", default="TripleSampler", choices=SAMPLERS_LIBRARY.keys())

config_file = Path()


def main():
    # config_file = Path("configs/lipac-optimization-config.yml")
    args = parser.parse_args()
    conf = load_optimization_config(args.config_file)

    # Connector
    connector_class = CONNECTORS_LIBRARY.get(args.connector_class)
    connector = connector_class(**conf["connector_kwargs"])

    # Sampler
    sampler_class = SAMPLERS_LIBRARY.get(args.sampler_class)
    sampler = sampler_class(connector=connector, optimization_config=conf, log=log)

    # Prepare logging
    outdir = Path(f"outputs/{connector.name}/")
    set_log_text_handler(log, outdir, log_file_name=sampler.name + ".log")

    # Perform sampling
    selection: gpd.GeoDataFrame = sampler.get_tiles()
    gdf = connector.extract(selection)
    gdf.to_file(outdir / f"{sampler.name}-{connector.name}-extract.gpkg")

    # Describe sampling with statistics
    #     # TODO: abstract this in another kind of stat object (perhaps in utils.py)
    bools = gdf.select_dtypes(include=np.number) > 0
    desc = bools.mean(numeric_only=True)
    desc.name = "prop_above_zero"
    desc.index.name = "attribute_name"
    desc.to_csv(outdir / f"{sampler.name}-stats_of_extract.csv", sep=";", index=True)


if __name__ == "__main__":
    main()
