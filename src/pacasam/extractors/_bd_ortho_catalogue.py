from datetime import date
from glob import glob
import re
import warnings
import argparse
from pathlib import Path
import pandas as pd
import geopandas as gpd
from shapely.geometry import box
import rasterio
from mpire import WorkerPool, cpu_count

current_date = date.today().strftime("%Y%m%d")

MIN_TARGET_YEAR = 2017  # inclusive

parser = argparse.ArgumentParser()
parser.add_argument(
    "-s",
    "--src_dir",
    default="/mnt/store-ref/produits/ortho-images/Ortho/",
    type=lambda p: str(Path(p).absolute()),
    help="Path to BD Ortho dir.",
)
parser.add_argument(
    "-o",
    "--output_catalogue_path",
    default=f"./outputs/{current_date}_bd_ortho_catalogue_since_{MIN_TARGET_YEAR}.gpkg",
    type=lambda p: Path(p).absolute(),
    help=("Path to save the BD Orthos Catalogue."),
)

GLOB_DIRS_MAIN = "{src_dir}/D*/20??"  # to-be formatted pattern

JPEG2_FILE_PATTERN = "*.jp2"

# Modalities we look for
ORTHO_TYPE_IRC = "IRC"
ORTHO_TYPE_RVB = "RVB"

# order of priority
ORTHO_RES_0M20 = "0M20"
ORTHO_RES_0M15 = "0M15"
ORTHO_RES_0M50 = "0M50"

# Expected structure in store-ref is
# Dir : /mnt/store.ign.fr/store-ref/produits/ortho-images/Ortho/D001/2021/
# Subdir : BDORTHO_RVB-0M20_JP2-E100_RGF93LAMB93_D001_2021 (ou IRC). Dallage
# File: 01-2021-0834-6551-LA93-0M20-RVB-E100.jp2  # 1km * 1km or other !


def make_catalogue(src_dir: str):
    # Globbing all orthoimages vintages
    vintage_dirs = glob(GLOB_DIRS_MAIN.format(src_dir=src_dir))

    # filter above min target year (inclusive)
    vintage_dirs = [v for v in vintage_dirs if int(v[-4:]) >= MIN_TARGET_YEAR]

    dfs = []
    tqdm_args = {"desc": "Cataloguing", "unit": "vintages"}
    # for vd in tqdm(vintage_dirs[:3], **tqdm_args):
    #     dfs += [get_rgb_nir_paths_from_vintage_dir(vd)]
    # with WorkerPool(n_jobs=2) as pool:
        with WorkerPool(n_jobs=cpu_count() // 3) as pool:
        dfs = pool.map(get_rgb_nir_paths_from_vintage_dir, vintage_dirs, progress_bar=True, progress_bar_options=tqdm_args)

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
    try:
        rgb_dir, irc_dir = find_rgb_and_irc_dirs(list_of_dirs)
    except ValueError:
        warnings.warn(f"No rgb/irc files were found for {vintage_dir}")
        return pd.DataFrame()

    # Find the files
    rgb_files = glob(str(rgb_dir / JPEG2_FILE_PATTERN))
    irc_files = glob(str(irc_dir / JPEG2_FILE_PATTERN))
    try:
        assert len(rgb_files) == len(irc_files)  # sanity check. Always true if same shapes of files in irc/rgb.
    except AssertionError:
        warnings.warn(f"Not same length {vintage_dir} : rgb={len(rgb_files)} vs. irc={len(irc_files)}")
        return pd.DataFrame()

    rgb_files = sorted(rgb_files)  # sort to align them with each other based on L93 coordinates
    irc_files = sorted(irc_files)

    rows = []
    img_width_of_vintage = None  # may change between vintages
    for rgb_file, irc_file in zip(rgb_files, irc_files):
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
    catalogue = make_catalogue(args.src_dir)
    print(catalogue)
    catalogue.to_file(args.output_catalogue_path)
