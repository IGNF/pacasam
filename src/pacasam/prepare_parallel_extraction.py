import os
import sys
from pathlib import Path
import argparse
from argparse import Namespace
from tempfile import TemporaryDirectory


root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from pacasam.connectors.connector import FILE_PATH_COLNAME, GEOMETRY_COLNAME, PATCH_ID_COLNAME
from pacasam.samplers.sampler import SPLIT_COLNAME
from pacasam.extractors.extractor import load_sampling


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
    "-d",
    "--sampling_parts_dir",
    default="/tmp/sampling_parts/",
    type=lambda p: Path(p).absolute(),
    help="Path to save one sampling foir each file (e.g. one sampling per LAZ file).",
)


def split_sampling_by_file(args: Namespace):
    """Split a sampling (typically a geopackage) by its related data file, into n parts, one for each file.

    We do this in order to paralellize the data extraction based on a sampling at the file level. By getting n
    smaller, file-level geopackages with a format identical to the original sampling, we can use the extraction methods
    without any change, and parallelize easely with `parallel`.

    See https://www.gnu.org/software/parallel/parallel.html) for more on `parallel`.

    Note: there should be not other print since we want to pipe directly from this function.
    """
    sp_dir = args.sampling_parts_dir
    os.makedirs(sp_dir, exist_ok=True)
    sampling = load_sampling(args.sampling_path)
    sampling_suffix: str = args.sampling_path.suffix
    for single_file_path, single_file_sampling in sampling.groupby(FILE_PATH_COLNAME):
        sampling_part_filename = sp_dir / Path(get_stem_from_any_file_format(single_file_path)).with_suffix(sampling_suffix)
        single_file_sampling[FILE_PATH_COLNAME] = single_file_sampling[FILE_PATH_COLNAME].apply(
            str
        )  # Path object cannot be savec by geopandas/fiona
        single_file_sampling.to_file(sampling_part_filename)
        # Printing for piping the list of gpkg_parts with `python ... > gpkg_parts.lst`
        print(sampling_part_filename)


# TODO: make unit tests to support both unix like and samba like paths
# Example '\\\\store.ign.fr\\store-lidarhd\\production\\reception\\QO\\donnees_classees\\livraison10p\\Livraison_20230116\\02_SemisClasse\\Semis_2021_0936_6346_LA93_IGN69.laz'
def get_stem_from_any_file_format(file_path: str):
    file_path_unix_format = str(file_path).replace("\\", "/")
    return Path(file_path_unix_format.split("/")[-1]).stem


if __name__ == "__main__":
    args = parser.parse_args()
    split_sampling_by_file(args)
