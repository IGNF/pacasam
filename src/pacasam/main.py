import shutil
import sys
from pathlib import Path
import numpy as np
import geopandas as gpd
import yaml

root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
from pacasam.utils import CONNECTORS_LIBRARY, SAMPLERS_LIBRARY, set_log_text_handler, load_optimization_config, setup_custom_logger
from pacasam.describe.report import make_all_graphs_and_a_report
from pacasam.describe.compare import Comparer

log = setup_custom_logger()
# Make sure that random operations in numpy (and pandas!) are deterministic.
np.random.seed(0)

# PARAMETERS
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--config_file", default="configs/Lipac.yml", type=lambda p: Path(p).absolute())

parser.add_argument("--connector_class", default="LiPaCConnector", choices=CONNECTORS_LIBRARY.keys())
parser.add_argument("--sampler_class", default="TripleSampler", choices=SAMPLERS_LIBRARY.keys())

parser.add_argument("--output_path", default="outputs/samplings", type=lambda p: Path(p).absolute())
parser.add_argument("--make_html_report", default="Y", choices=[True, False], type=lambda choice: choice == "Y")


def main():
    # config_file = Path("configs/Lipac.yml")
    args = parser.parse_args()
    conf = load_optimization_config(args.config_file)

    # Prepare logging
    task_name = f"{args.sampler_class}-{args.connector_class}"
    set_log_text_handler(log, args.output_path, log_file_name=task_name + ".log")
    log.info("Performing a sampling with pacasam (https://github.com/IGNF/pacasam)\n")
    log.info(f"COMMAND: {' '.join(sys.argv)}")
    log.info(f"CONFIGURATION FILE: {args.config_file}")
    copy_to = args.output_path / args.config_file.name
    shutil.copy(args.config_file, copy_to)
    log.info(f"CONFIGURATION FILE COPY: {copy_to}")
    log.info(f"CONFIGURATION: \n {yaml.dump(conf, indent=4)}\n")

    # Connector
    connector_class = CONNECTORS_LIBRARY.get(args.connector_class)
    connector = connector_class(log=log, **conf["connector_kwargs"])

    # Sampler
    sampler_class = SAMPLERS_LIBRARY.get(args.sampler_class)
    sampler = sampler_class(connector=connector, optimization_config=conf, log=log)

    # Perform sampling
    selection: gpd.GeoDataFrame = sampler.get_tiles()
    gdf = connector.extract(selection)
    gpkg_path = args.output_path / f"{task_name}-extract.gpkg"
    log.info(f"Saving N={len(gdf)} patches into {gpkg_path}")
    gdf.to_file(gpkg_path)

    # Get descriptive statistics
    comparer = Comparer(output_path=args.output_path / f"{task_name}-stats")
    comparer.compare(connector.db, gdf)

    # (Optionnaly) make a html report with descriptive stats.
    if args.make_html_report:
        output_path = args.output_path / f"{task_name}/dataviz/"
        log.info(f"Making an html report, saved at {output_path}")
        make_all_graphs_and_a_report(gpkg_path=gpkg_path, output_path=output_path)


if __name__ == "__main__":
    main()
