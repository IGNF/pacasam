from glob import glob
import re
import sys
import geopandas as gpd
from pathlib import Path
import pandas as pd
from mpire import WorkerPool, cpu_count
import argparse
from shapely.geometry import box

import rasterio
from tqdm import tqdm

root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
# current_date = date.today().strftime("%Y%m%d")
# OUT = OUTPUTS_DIR / f"{current_date}_file_id_with_path_not_found.csv"


# from pacasam.connectors.connector import FILE_PATH_COLNAME, GEOMETRY_COLNAME, PATCH_ID_COLNAME
# from pacasam.samplers.sampler import SPLIT_COLNAME

parser = argparse.ArgumentParser()
parser.add_argument(
    "-s",
    "--src_dir",
    default="/mnt/store.ign.fr/store-ref/produits/ortho-images/Ortho/",
    type=lambda p: Path(p).absolute(),
    help="Path to BD Ortho dir.",
)
parser.add_argument(
    "-o",
    "--output_catalogue_path",
    default="./outputs/catalogue.gpkg",
    type=lambda p: Path(p).absolute(),
    help=("Path to save the BD Orthos Catalogue."),
)

MIN_TARGET_YEAR = 2017  # inclusive
GLOB_DIRS_MAIN = "/mnt/store-ref/produits/ortho-images/Ortho/D*/20??"  # be specific in case we have random dirs...
JPEG2_FILE_PATTERN = "*.jp2"


# Modalities we look for
ORTHO_TYPE_IRC = "IRC"
ORTHO_TYPE_RVB = "RVB"

# order of priority
ORTHO_RES_0M20 = "0M20"
ORTHO_RES_0M15 = "0M15"
ORTHO_RES_0M50 = "0M50"

# Structure
# Dir : /mnt/store.ign.fr/store-ref/produits/ortho-images/Ortho/D001/2021/
# Subdir : BDORTHO_RVB-0M20_JP2-E100_RGF93LAMB93_D001_2021 (ou IRC). Dallage
# File: 01-2021-0834-6551-LA93-0M20-RVB-E100.jp2  # 1km * 1km


def make_catalogue():
    # Globbing all orthoimages vintages
    vintage_dirs = glob(GLOB_DIRS_MAIN)

    # filter above year
    vintage_dirs = [v for v in vintage_dirs if int(v[-4:]) >= MIN_TARGET_YEAR]

    dfs = []
    for vd in tqdm(vintage_dirs[:3], desc="Vintage"):
        dfs += [get_rgb_nir_paths_from_vintage_dir(vd)]
    # with WorkerPool(n_jobs=cpu_count() // 3) as pool:
    # rgb_and_nir_file_pairs = pool.map(get_rgb_nir_pairs_from_vintage_dir, vintage_dirs, progress_bar=True)

    catalogue = pd.concat(dfs, ignore_index=True)
    return catalogue


def find_rgb_and_irc_dirs(list_of_dirs) -> pd.DataFrame:
    """
    Filtre les répertoires trouvés par la méthode search.
    Renvoie 1 répertoire IRC et 1 répertoire RVB.

    Parameters
    ----------
    liste_of_dirs: list[dict]
        Une liste de répertoire d'Orthos.

    Returns
    -------
    new_df: pd.DataFrame
        Contenu : 1 Répertoire de type IRC
                    1 Répertoire de type RVB
    """
    types = [ORTHO_TYPE_RVB, ORTHO_TYPE_IRC]
    resolutions = (ORTHO_RES_0M20, ORTHO_RES_0M15, ORTHO_RES_0M50)

    # new_df = pd.DataFrame()
    rgb_and_irc_dirs = []
    for ortho_type in types:
        candidates_orthos = [o for o in list_of_dirs if ortho_type in o.name and "E100" in o.name and o.is_dir()]
        match = []
        for resolution in resolutions:
            res_pattern = rf"{resolution}"
            match = [s for s in candidates_orthos if re.search(res_pattern, str(s))]
            if match:
                rgb_and_irc_dirs += [match[0]]
                break

    return rgb_and_irc_dirs


def get_rgb_nir_paths_from_vintage_dir(vintage_dir: str):
    year = vintage_dir.split("/")[-1]
    dept = vintage_dir.split("/")[-2]

    # Find a folder for each modality, prioritizing 20cm > 15cm > 50cm.
    # Always look for E100 qualitys since is is the original data it should exist.
    list_of_dirs = list(Path(vintage_dir).iterdir())
    rgb_dir, irc_dir = find_rgb_and_irc_dirs(list_of_dirs)

    # Find the files
    rgb_files = glob(str(rgb_dir / JPEG2_FILE_PATTERN))  # check the missing /, use Path ?
    irc_files = glob(str(irc_dir / JPEG2_FILE_PATTERN))  # check the missing /, use Path ?
    assert len(rgb_files) == len(irc_files)  # sanity check. Always true if same shapes of files in irc/rgb
    rgb_files = sorted(rgb_files)
    irc_files = sorted(irc_files)

    rows = []
    img_width_of_vintage = None  # may change between vintages
    for rgb_file, irc_file in tqdm(zip(rgb_files, irc_files), leave=False):
        # define coords
        basename_parts = Path(rgb_file).name.split("-")
        min_x = basename_parts[2]
        max_y = basename_parts[3]
        coords = f"{min_x}_{max_y}"

        # define geometry
        if not img_width_of_vintage:
            # Width is unique within a vintage
            bounds = rasterio.open(rgb_file).bounds
            img_width_of_vintage = bounds.top - bounds.bottom
        min_x = int(min_x) * 1000
        max_y = int(max_y) * 1000
        min_y = max_y - img_width_of_vintage
        max_x = min_x + img_width_of_vintage
        geometry = box(min_x, min_y, max_x, max_y)

        # regroup file information for a coordinate.
        rows += [(dept, year, coords, rgb_file, irc_file, geometry)]

    df = gpd.GeoDataFrame(data=rows, columns=["dept", "year", "coords", "rgb_file", "irc_file", "geometry"])
    return df


if __name__ == "__main__":
    args = parser.parse_args()
    catalogue = make_catalogue()
    print(catalogue)
    catalogue.to_file(args.output_catalogue_path)
