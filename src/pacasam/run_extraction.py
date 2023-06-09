import sys
from pathlib import Path
import argparse

root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from pacasam.connectors.connector import FILE_PATH_COLNAME, GEOMETRY_COLNAME, PATCH_ID_COLNAME
from pacasam.samplers.sampler import SPLIT_COLNAME
from pacasam.extractors.extractor import Extractor
from pacasam.extractors.laz import LAZExtractor
from pacasam.utils import set_log_text_handler, setup_custom_logger

log = setup_custom_logger()

# PARAMETERS

parser = argparse.ArgumentParser()
parser.add_argument(
    "-s",
    "--sampling_path",
    default=None,
    type=lambda p: Path(p).absolute(),
    help=(
        "Path to a valid sampling i.e. a geopackage with columns: "
        f"{FILE_PATH_COLNAME}, {PATCH_ID_COLNAME}, {GEOMETRY_COLNAME}, {SPLIT_COLNAME}"
    ),
)
parser.add_argument(
    "-d", "--dataset_root_path", default=None, type=lambda p: Path(p).absolute(), help="Path to extract data to. Created if needed."
)
parser.add_argument(
    "--samba_filesystem",
    default=False,
    action="store_true",
    help="Use a samba file system (i.e. a data store) instead of the local filesystem.",
)


def run_extraction(args):
    # Prepare logging
    set_log_text_handler(log, args.dataset_root_path)
    log.info("Extraction of a dataset using pacasam (https://github.com/IGNF/pacasam).\n")
    log.info(f"COMMAND: {' '.join(sys.argv)}")
    log.info(f"SAMPLING GEOPACKAGE: {args.sampling_path}")
    log.info(f"OUTPUT DATASET DIR: {args.dataset_root_path}")
    extractor: Extractor = LAZExtractor(
        log=log, sampling_path=args.sampling_path, dataset_root_path=args.dataset_root_path, use_samba=args.samba_filesystem
    )
    extractor.extract()
    log.info(f"Extracted data in {args.dataset_root_path}")


if __name__ == "__main__":
    args = parser.parse_args()
    run_extraction(args)
