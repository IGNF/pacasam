import sys
from pathlib import Path
import argparse


root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from pacasam.connectors.connector import GEOMETRY_COLNAME, PATCH_ID_COLNAME, SRID_COLNAME
from pacasam.samplers.sampler import SPLIT_COLNAME
from pacasam.extractors.extractor import Extractor
from pacasam.extractors.laz import LAZExtractor
from pacasam.extractors.bd_ortho_today import BDOrthoTodayExtractor
from pacasam.extractors.bd_ortho_vintage import BDOrthoVintageExtractor
from pacasam.utils import EXTRACTORS_LIBRARY, set_log_text_handler, setup_custom_logger

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
        f"{PATCH_ID_COLNAME}, {GEOMETRY_COLNAME}, {SPLIT_COLNAME}"
        f"and {SRID_COLNAME} (optionaly)"
    ),
)
parser.add_argument(
    "-d", "--dataset_root_path", default=None, type=lambda p: Path(p).absolute(), help="Path where to extract dataset. Created if needed."
)
parser.add_argument(
    "--samba_filesystem",
    default=False,
    action="store_true",
    help="Use a samba file system (i.e. a data store) instead of the local filesystem.",
)
parser.add_argument(
    "--extractor_class", default="LAZExtractor", type=str, help=("Name of class of Extractor to use."), choices=EXTRACTORS_LIBRARY.keys()
)


def run_extraction(args):
    set_log_text_handler(log, args.dataset_root_path)
    log.info("Extraction of a dataset using pacasam (https://github.com/IGNF/pacasam).\n")
    log.info(f"COMMAND: {' '.join(sys.argv)}")
    log.info(f"SAMPLING GEOPACKAGE: {args.sampling_path}")
    log.info(f"OUTPUT DATASET DIR: {args.dataset_root_path}")
    log.info(f"EXTRACTOR CLASS: {args.extractor_class}")
    if args.extractor_class == "LAZExtractor":
        extractor: Extractor = LAZExtractor(
            log=log, sampling_path=args.sampling_path, dataset_root_path=args.dataset_root_path, use_samba=args.samba_filesystem
        )
    elif args.extractor_class == "BDOrthoTodayExtractor":
        extractor: Extractor = BDOrthoTodayExtractor(log=log, sampling_path=args.sampling_path, dataset_root_path=args.dataset_root_path)
    elif args.extractor_class == "BDOrthoVintageExtractor":
        extractor: Extractor = BDOrthoVintageExtractor(log=log, sampling_path=args.sampling_path, dataset_root_path=args.dataset_root_path)
    else:
        raise ValueError(f"Extractor {args.extractor_class} is unknown. See argparse choices with --help.")
    extractor.extract()
    log.info(f"Extracted data in {args.dataset_root_path}")


if __name__ == "__main__":
    args = parser.parse_args()
    run_extraction(args)
