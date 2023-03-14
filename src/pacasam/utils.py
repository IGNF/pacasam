import logging
from pathlib import Path
import sys


# def get_logger(__name__):
#     log = logging.getLogger(__name__)
#     handler = logging.StreamHandler(sys.stdout)
#     log.setLevel(logging.DEBUG)
#     log.addHandler(handler)
#     return log

# def set_text_handler(log, outdir: Path):
#     outdir.mkdir(parents=True, exist_ok=True)
#     handler = logging.FileHandler(outdir / "logs.txt")
#     log.addHandler(handler)
#     return outdir


def setup_custom_logger(outdir):
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)

    formatter = logging.Formatter(fmt="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler(outdir / "log.txt", mode="w")
    handler.setFormatter(formatter)
    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(formatter)
    log.addHandler(handler)
    log.addHandler(screen_handler)
    
    return log
