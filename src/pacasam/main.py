import sys
from pathlib import Path
import numpy as np
import geopandas as gpd

directory = Path(__file__).resolve().parent.parent
sys.path.append(str(directory))
from pacasam.utils import CONNECTORS_LIBRARY, SAMPLERS_LIBRARY, set_log_text_handler, load_optimization_config, setup_custom_logger
from pacasam.dataviz.describe import make_all_graphs_and_a_report

log = setup_custom_logger()

# PARAMETERS
import argparse

parser = argparse.ArgumentParser()
POSSIBLE_CONFIGS = ["configs/TripleSampler-Lipac.yml", "configs/TripleSampler-Synthetic.yml"]
parser.add_argument("--config_file", default="configs/TripleSampler-Lipac.yml", choices=POSSIBLE_CONFIGS)

parser.add_argument("--connector_class", default="LiPaCConnector", choices=CONNECTORS_LIBRARY.keys())
parser.add_argument("--sampler_class", default="TripleSampler", choices=SAMPLERS_LIBRARY.keys())

config_file = Path()


def main():
    # config_file = Path("configs/TripleSampler-Lipac.yml")
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
    gpkg_path = outdir / f"{sampler.name}-{connector.name}-extract.gpkg"
    gdf.to_file(gpkg_path)

    # make some html files
    output_path = outdir / "dataviz/"
    output_path.mkdir(parents=True, exist_ok=True)
    make_all_graphs_and_a_report(gpkg_path=gpkg_path, output_path=output_path)


if __name__ == "__main__":
    main()
