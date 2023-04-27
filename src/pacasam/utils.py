import logging
from pathlib import Path
import yaml
import sys
from pacasam.connectors.lipac import load_LiPaCConnector
from pacasam.connectors.synthetic import SyntheticConnector
from pacasam.samplers.kmeans import KMeansSampler
from pacasam.samplers.spatial import SpatialSampler
from pacasam.samplers.diversity import DiversitySampler
from pacasam.samplers.random import RandomSampler
from pacasam.samplers.targetted import TargettedSampler
from pacasam.samplers.triple import TripleSampler


LOGGING_FORMATTER = logging.Formatter(fmt="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


def setup_custom_logger():
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)

    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(LOGGING_FORMATTER)
    log.addHandler(screen_handler)

    return log


def set_log_text_handler(log: logging.Logger, outdir: Path, log_file_name: str = "runtime.log"):
    """Use in main(), to setup a specific log folder."""
    outdir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(outdir / log_file_name, mode="w")
    handler.setFormatter(LOGGING_FORMATTER)
    log.addHandler(handler)
    return log


def get_class_name(instance):
    return str(instance.__class__.__name__)


def load_sampling_config(config_file):
    with open(config_file, "r") as file:
        cf = yaml.safe_load(file)
    return cf


# Dictionnaries to parametrize the access to object via configs.

SAMPLERS_LIBRARY = {
    "TripleSampler": TripleSampler,
    "TargettedSampler": TargettedSampler,
    "DiversitySampler": DiversitySampler,
    "SpatialSampler": SpatialSampler,
    "RandomSampler": RandomSampler,
    "KMeansSampler": KMeansSampler,
}

CONNECTORS_LIBRARY = {
    "LiPaCConnector": load_LiPaCConnector,
    "SyntheticConnector": SyntheticConnector,
}
