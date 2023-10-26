import shutil
import sys
from pathlib import Path
import geopandas as gpd
import yaml
from dotenv import load_dotenv
import argparse
import git

root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
from pacasam.utils import CONNECTORS_LIBRARY, SAMPLERS_LIBRARY, set_log_text_handler, load_sampling_config, setup_custom_logger
from pacasam.analysis.stats import Comparer
from pacasam.connectors.connector import Connector
from pacasam.samplers.sampler import Sampler, save_gpd_to_any_filesystem
from pacasam._version import __version__

repo = git.Repo(search_parent_directories=True)
sha = repo.head.object.hexsha  # Git SHA to track the exact version of the code.
load_dotenv()
log = setup_custom_logger()

# PARAMETERS
parser = argparse.ArgumentParser()
parser.add_argument("--config_file", default="configs/Lipac.yml", type=lambda p: Path(p).absolute())
parser.add_argument("--connector_class", default="LiPaCConnector", choices=CONNECTORS_LIBRARY.keys())
parser.add_argument("--sampler_class", default="TripleSampler", choices=SAMPLERS_LIBRARY.keys())
parser.add_argument("--output_path", default=None)


def run_sampling(args):
    # config_file = Path("configs/Lipac.yml")
    task_name = f"{args.connector_class}-{args.sampler_class}"
    args.output_path = args.output_path if args.output_path is not None else f"outputs/samplings/{task_name}/"
    args.output_path = Path(args.output_path).absolute()

    # Prepare logging
    set_log_text_handler(log, args.output_path)
    log.info("Performing a sampling with pacasam (https://github.com/IGNF/pacasam).\n")
    log.info(f"Pacasam version is {__version__} at commit https://github.com/IGNF/pacasam/tree/{sha}.\n")
    log.info(f"COMMAND: {' '.join(sys.argv)}")
    conf = load_sampling_config(args.config_file)
    log.info(f"CONFIGURATION FILE: {args.config_file}")
    copy_to = args.output_path / args.config_file.name
    shutil.copy(args.config_file, copy_to)
    log.info(f"CONFIGURATION FILE COPY: {copy_to}")
    log.info(f"CONFIGURATION: \n {yaml.dump(conf, indent=4)}\n")

    # Connector
    connector_class = CONNECTORS_LIBRARY.get(args.connector_class)
    connector: Connector = connector_class(log=log, **conf["connector_kwargs"])

    # Sampler
    sampler_class = SAMPLERS_LIBRARY.get(args.sampler_class)
    sampler: Sampler = sampler_class(connector=connector, sampling_config=conf, log=log)

    # Perform sampling
    selection: gpd.GeoDataFrame = sampler.get_patches()
    gdf = connector.extract(selection)
    split_name = conf["connector_kwargs"]["split"]
    gpkg_name = f"{task_name}-{split_name}.gpkg"
    gpkg_path = args.output_path / gpkg_name
    log.info(f"Saving N={len(gdf)} patches into {gpkg_path}")
    save_gpd_to_any_filesystem(gdf, gpkg_path)

    # Get descriptive statistics by comparing the database and the sampling
    comparer = Comparer(output_path=args.output_path / "stats")
    comparer.compare(connector.db, gdf)

    return gpkg_path


if __name__ == "__main__":
    args = parser.parse_args()
    run_sampling(args)
