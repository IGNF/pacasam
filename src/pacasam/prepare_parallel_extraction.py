import os
import sys
from pathlib import Path
import argparse
from mpire import WorkerPool, cpu_count


root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from pacasam.connectors.connector import GEOMETRY_COLNAME, PATCH_ID_COLNAME, SRID_COLNAME
from pacasam.samplers.sampler import SPLIT_COLNAME
from pacasam.extractors.extractor import check_sampling_format, load_sampling
from pacasam.extractors.laz import FILE_PATH_COLNAME


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
    "-d",
    "--sampling_parts_dir",
    default="/tmp/sampling_parts/",
    type=lambda p: Path(p).absolute(),
    help="Path to save one sampling foir each file (e.g. one sampling per LAZ file).",
)

parser.add_argument("-p", "--parts_colname", default=FILE_PATH_COLNAME, type=str, help="By which column to split the sampling.")


def split_sampling_by_file(sampling_path: Path, sampling_parts_dir: Path, parts_colname: str):
    """Split a sampling (typically a geopackage) by its related data file, into n parts, one for each file.

    We do this in order to paralellize the data extraction based on a sampling at the file level. By getting n
    smaller, file-level geopackages with a format identical to the original sampling, we can use the extraction methods
    without any change, and parallelize easely with `parallel`.

    See https://www.gnu.org/software/parallel/parallel.html) for more on `parallel`.
    """

    os.makedirs(sampling_parts_dir, exist_ok=True)

    sampling = load_sampling(sampling_path)
    check_sampling_format(sampling)

    with WorkerPool(n_jobs=cpu_count() // 3) as pool:
        iterable = [
            (sampling_parts_dir, single_file_path, single_file_sampling, sampling_path.suffix)
            for single_file_path, single_file_sampling in sampling.groupby(parts_colname)
        ]
        pool.map(save_single_file_sampling, iterable, progress_bar=True)


def save_single_file_sampling(sampling_parts_dir, single_file_path, single_file_sampling, parts_colname: str, sampling_suffix: str = ".gpkg"):
    """Select the patches of a single data file, and save them as a single file sampling."""
    stem = Path(single_file_path).stem
    sampling_part_filename = (sampling_parts_dir / stem).with_suffix(sampling_suffix)
    single_file_sampling.to_file(sampling_part_filename)


if __name__ == "__main__":
    args = parser.parse_args()
    split_sampling_by_file(args.sampling_path, args.sampling_parts_dir, args.parts_colname)
