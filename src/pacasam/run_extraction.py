import sys
from pathlib import Path
import numpy as np
import yaml
from pacasam.extractors.extractor import Extractor
from pacasam.extractors.laz import LAZExtractor


root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
from pacasam.utils import set_log_text_handler, setup_custom_logger

log = setup_custom_logger()

# PARAMETERS
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--sampling_path", default=None, type=lambda p: Path(p).absolute())
parser.add_argument("-d", "--dataset_root_path", default="./outputs/laz_dataset/", type=lambda p: Path(p).absolute())


def run_extraction(args):
    # Prepare logging
    set_log_text_handler(log, args.dataset_root_path)
    log.info("Extraction of a dataset using pacasam (https://github.com/IGNF/pacasam).\n")
    log.info(f"COMMAND: {' '.join(sys.argv)}")
    log.info(f"SAMPLING GEOPACKAGE: {args.sampling_path}")
    log.info(f"OUTPUT DATASET DIR: {args.dataset_root_path}")

    extractor: Extractor = LAZExtractor(log=log, sampling_path=args.sampling_path, dataset_root_path=args.dataset_root_path)
    extractor.make_dataset()
    log.info(f"Extracted data in {args.dataset_root_path}")


if __name__ == "__main__":
    args = parser.parse_args()
    run_extraction(args)
