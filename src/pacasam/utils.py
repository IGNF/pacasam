import logging
from pathlib import Path
import sys


LOGGING_FORMATTER = logging.Formatter(fmt="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


def setup_custom_logger():
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)

    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(LOGGING_FORMATTER)
    log.addHandler(screen_handler)

    return log


def set_log_text_handler(log: logging.Logger, outdir: Path, log_file_name: str = "log.txt"):
    """Use in main(), to setup a specific log folder."""
    outdir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(outdir / log_file_name, mode="w")
    handler.setFormatter(LOGGING_FORMATTER)
    log.addHandler(handler)
    return log


def get_class_name(instance):
    return str(instance.__class__.__name__)
