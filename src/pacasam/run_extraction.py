import sys
from pathlib import Path
import argparse


root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from pacasam.connectors.connector import FILE_PATH_COLNAME, GEOMETRY_COLNAME, PATCH_ID_COLNAME
from pacasam.samplers.sampler import SPLIT_COLNAME
from pacasam.extractors.extractor import Extractor
from pacasam.extractors.laz import LAZExtractor
from pacasam.extractors.orthoimages import OrthoimagesExtractor
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
        f"{FILE_PATH_COLNAME}, {PATCH_ID_COLNAME}, {GEOMETRY_COLNAME}, {SPLIT_COLNAME}"
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

parser.add_argument(
    "--n_jobs",
    default=1,
    type=int,
    help="Num of processors to use for parallelization of the extraction with MPIRE.",
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
            log=log,
            sampling_path=args.sampling_path,
            dataset_root_path=args.dataset_root_path,
            use_samba=args.samba_filesystem,
            n_jobs=args.n_jobs,
        )
    elif args.extractor_class == "OrthoimagesExtractor":
        extractor: Extractor = OrthoimagesExtractor(
            log=log, sampling_path=args.sampling_path, dataset_root_path=args.dataset_root_path, n_jobs=args.n_jobs
        )
    else:
        raise ValueError(f"Extractor {args.extractor_class} is unknown. See argparse choices with --help.")
    extractor.extract()
    log.info(f"Extracted data in {args.dataset_root_path}")


if __name__ == "__main__":
    args = parser.parse_args()
    run_extraction(args)
