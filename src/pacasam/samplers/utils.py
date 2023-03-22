import logging
import yaml

log = logging.getLogger(__name__)


def load_optimization_config(config_file):
    with open(config_file, "r") as file:
        cf = yaml.safe_load(file)
    return cf
