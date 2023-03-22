import logging
import yaml
import geopandas as gpd

log = logging.getLogger(__name__)

# TODO/ better logging : https://stackoverflow.com/a/15729700/8086033


def load_optimization_config(config_file):
    with open(config_file, "r") as file:
        cf = yaml.safe_load(file)
    return cf
