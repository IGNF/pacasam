import logging
from math import ceil
from typing import List
import numpy as np
from pandas import DataFrame
import geopandas as gpd
from shapely.geometry import box

from pacasam.connectors.connector import FILE_ID_COLNAME, Connector
from pacasam.connectors.lipac import SPLIT_POSSIBLE_VALUES, TEST_COLNAME_IN_LIPAC, filter_lipac_patches_on_split
from pacasam.samplers.sampler import PATCH_ID_COLNAME

# Should match what is in the Lipac database. Also used for histograms.
NB_POINTS_COLNAMES = [
    "nb_total",
    "nb_sol",
    "nb_bati",
    "nb_vegetation_basse",
    "nb_vegetation_moyenne",
    "nb_vegetation_haute",
    "nb_pont",
    "nb_eau",
    "nb_sursol_perenne",
    "nb_non_classes",
]

SLAB_SIZE = 1000
PATCH_SIZE = 50

NUM_PATCHES_BY_SLAB = int((SLAB_SIZE / PATCH_SIZE) ** 2)
FRAC_OF_TEST_PATCHES_IN_DATABASE = 0.2


class SyntheticConnector(Connector):
    """Connector which creates synthetic data to sample from.

    Creates a set of slabs (1000m x 1000m), composed of patches (50m x 50m).
    Each patch has the following types attributes :
      - Number of points from different classes (e.g. nb_total, nb_sol)
      - Binary descriptors, with specific prevalences (C1, C2...)
      - Mandatory fields as described in connector.py

    """

    def __init__(
        self,
        log: logging.Logger,
        binary_descriptors_prevalence: List[float],
        split: SPLIT_POSSIBLE_VALUES,
        db_size: int = 10000,
    ):
        """Initialization.

        Args:
            log (logging.Logger): shared logger.
            binary_descriptors_prevalence (List[float]): a list of prevalences to create synthetic boolean descriptors.
            split (str): desired split, among `train`,`test`, or `any`.
            db_size (int, optional): Desired size of the synthetic database. Defaults to 10000.

            Note that the actual synthetuc database to sample from will be smaller than given db_size, if the split
            is either train or val.

        """
        super().__init__(log=log)
        df_geom, df_file_ids = make_synthetic_geometries_and_slabs(db_size)
        # WARNING: the synthetic geometries will not be compliant with the FILE_ID_COLNAME.
        self.db = gpd.GeoDataFrame(
            geometry=df_geom,
            crs="EPSG:2154",
        )
        for idx, t in enumerate(binary_descriptors_prevalence):
            n_target = ceil(t * db_size)
            d = np.concatenate([np.ones(shape=(n_target,)).astype(bool), np.zeros(shape=(db_size - n_target,)).astype(bool)])
            np.random.shuffle(d)
            self.db[f"C{idx}"] = d

        for nb_point_colname in NB_POINTS_COLNAMES:
            d = np.random.randint(low=0, high=60_000, size=(db_size,)).astype(int)
            self.db[nb_point_colname] = d

        self.db[PATCH_ID_COLNAME] = range(len(self.db))
        self.db[FILE_ID_COLNAME] = df_file_ids

        # create a test columns that flags "reserved" patches (i.e. reserved for test set)
        n_target = int(db_size * FRAC_OF_TEST_PATCHES_IN_DATABASE)
        d = np.concatenate([np.ones(shape=(n_target,)).astype(bool), np.full(shape=(db_size - n_target,), fill_value=np.nan)])
        np.random.shuffle(d)
        self.db[TEST_COLNAME_IN_LIPAC] = d
        self.db = filter_lipac_patches_on_split(db=self.db, split_colname=TEST_COLNAME_IN_LIPAC, desired_split=split)


def make_synthetic_geometries_and_slabs(db_size: int):
    fake_grid_size = ceil(np.sqrt(db_size))
    # Cartesian product of range * tile_size
    df_x = DataFrame({"x": range(fake_grid_size)}) * PATCH_SIZE
    df_y = DataFrame({"y": range(fake_grid_size)}) * PATCH_SIZE
    df_xy = df_x.merge(df_y, how="cross")

    # limit the size to the desired db_size
    df_xy = df_xy.head(db_size)

    df_geom = df_xy.apply(
        lambda row: box(
            row["x"],
            row["y"],
            row["x"] + PATCH_SIZE,
            row["y"] + PATCH_SIZE,
            ccw=False,
        ),
        axis=1,
    )
    df_file_ids = (df_xy // SLAB_SIZE).apply(lambda row: str(row["x"]) + "_" + str(row["y"]), axis=1)
    return df_geom, df_file_ids
