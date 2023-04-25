import logging
from math import ceil
from typing import Iterable, List, Optional
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box

from pacasam.connectors.connector import Connector

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

NUM_TILES_BY_SLAB = int((SLAB_SIZE / TILE_SIZE) ** 2)


class SyntheticConnector(Connector):
    def __init__(self, log, binary_descriptors_prevalence: List[float], db_size: int = 10000):
        super().__init__()
        self.log = log
        self.db_size = db_size
        df_geom, df_dalle_id = self._make_synthetic_geometries_and_slabs()
        # WARNING: the synthetic geometries will not be compliant with the dalle_id.
        self.df = gpd.GeoDataFrame(
            geometry=df_geom,
            crs="EPSG:2154",
        )

        for idx, t in enumerate(binary_descriptors_prevalence):
            n_target = ceil(t * db_size)
            d = np.concatenate([np.ones(shape=(n_target,)).astype(bool), np.zeros(shape=(db_size - n_target,)).astype(bool)])
            np.random.shuffle(d)
            self.df[f"C{idx}"] = d

        for nb_point_colname in NB_POINTS_COLNAMES:
            d = np.random.randint(low=0, high=60_000, size=(db_size,)).astype(int)
            self.df[nb_point_colname] = d

        self.df["id"] = range(len(self.df))
        self.df["dalle_id"] = df_dalle_id

    def request_tiles_by_boolean_indicator(self, bool_descriptor_name) -> pd.Series:
        """Cf. https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.query.html"""
        return self.df.query(bool_descriptor_name)

    def request_all_other_tiles(self, exclude_ids: Iterable):
        """Requests all other tiles."""
        all_tiles = self.request_tiles_by_boolean_indicator(where="id")
        return all_tiles[~all_tiles["id"].isin(exclude_ids)]

    def extract(self, selection: Optional[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        """Extract everything using ids."""
        if selection is None:
            return self.df

        extract = self.df.merge(
            selection,
            how="inner",
            on="id",
        )
        return extract

    def _make_synthetic_geometries_and_slabs(self):
        fake_grid_size = ceil(np.sqrt(self.db_size))
        # Cartesian product of range * tile_size
        df_x = pd.DataFrame({"x": range(fake_grid_size)}) * TILE_SIZE
        df_y = pd.DataFrame({"y": range(fake_grid_size)}) * TILE_SIZE
        df_xy = df_x.merge(df_y, how="cross")

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
