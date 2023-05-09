import logging
from math import ceil
from typing import List, Optional
import numpy as np
import pandas as pd
from pandas import DataFrame
import geopandas as gpd
from shapely.geometry import box

from pacasam.connectors.connector import Connector

# Should match what is in the database. Also used for histograms.
NB_POINTS_COLNAMES = [
    "nb_points_total",
    "nb_points_sol",
    "nb_points_bati",
    "nb_points_vegetation_basse",
    "nb_points_vegetation_moyenne",
    "nb_points_vegetation_haute",
    "nb_points_pont",
    "nb_points_eau",
    "nb_points_sursol_perenne",
    "nb_points_non_classes",
]

log = logging.getLogger(__name__)

SLAB_SIZE = 1000
TILE_SIZE = 50

NUM_PATCHES_BY_SLAB = int((SLAB_SIZE / TILE_SIZE) ** 2)


class SyntheticConnector(Connector):
    def __init__(self, log: Optional[logging.Logger], binary_descriptors_prevalence: List[float], db_size: int = 10000):
        super().__init__()
        self.log = log
        self.db_size = db_size
        # TODO: make db an attribute so that it is created when accessed instead of at initialization of the object.
        df_geom, df_dalle_id = self._make_synthetic_geometries_and_slabs()
        # WARNING: the synthetic geometries will not be compliant with the dalle_id.
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

        self.db["id"] = range(len(self.db))
        self.db["dalle_id"] = df_dalle_id

    def extract(self, selection: Optional[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        """Extract everything using ids."""
        extract = self.db.merge(
            selection,
            how="inner",
            on="id",
        )
        return extract

    def _make_synthetic_geometries_and_slabs(self):
        fake_grid_size = ceil(np.sqrt(self.db_size))
        # Cartesian product of range * tile_size
        df_x = DataFrame({"x": range(fake_grid_size)}) * TILE_SIZE
        df_y = DataFrame({"y": range(fake_grid_size)}) * TILE_SIZE
        df_xy = df_x.merge(df_y, how="cross")

        # limit the size to the desired db_size
        df_xy = df_xy.head(self.db_size)

        df_geom = df_xy.apply(
            lambda row: box(
                row["x"],
                row["y"],
                row["x"] + TILE_SIZE,
                row["y"] + TILE_SIZE,
                ccw=False,
            ),
            axis=1,
        )
        df_dalle_id = (df_xy // SLAB_SIZE).apply(lambda row: str(row["x"]) + "_" + str(row["y"]), axis=1)
        return df_geom, df_dalle_id
