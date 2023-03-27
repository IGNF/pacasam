import logging
from math import ceil
from typing import List, Optional
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box

from pacasam.connectors.connector import Connector
from pacasam.describe import NB_POINTS_COLNAMES

log = logging.getLogger(__name__)

SLAB_SIZE = 1000
TILE_SIZE = 50

NUM_TILES_BY_SLAB = int((SLAB_SIZE / TILE_SIZE) ** 2)


class SyntheticConnector(Connector):
    def __init__(self, binary_descriptors_prevalence: List[float], db_size: int = 10000):
        super().__init__()

        self.db_size = db_size

        data = []
        for t in binary_descriptors_prevalence:
            n_target = ceil(t * db_size)
            d = np.concatenate([np.ones(shape=(n_target,)), np.zeros(shape=(db_size - n_target,))])
            np.random.shuffle(d)
            data += [d]
        for _ in NB_POINTS_COLNAMES:
            d = np.random.randint(low=0, high=30_000, size=(db_size,)).astype(int)
            data += [d]
        data = np.column_stack(data)
        self.descriptor_names = [f"C{idx}" for idx in range(len(binary_descriptors_prevalence))] + NB_POINTS_COLNAMES
        # WARNING: the synthetic geometries will not be compliant with the dall_id.
        df_geom, df_dalle_id = self._make_synthetic_geometries_and_slabs()
        self.synthetic_df = gpd.GeoDataFrame(
            data,
            columns=self.descriptor_names,
            geometry=df_geom,
            crs="EPSG:2154",
        )
        self.synthetic_df["id"] = range(len(self.synthetic_df))
        self.synthetic_df["dalle_id"] = df_dalle_id

    def request_tiles_by_condition(self, where: str) -> pd.Series:
        """Requests id based on a where sql-like query.

        For instance: query = 'C0 > 0'.
        Cf. https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.query.html
        """
        return self.synthetic_df.query(where)[["id", "geometry", "dalle_id"]]

    def request_all_other_tiles(self, exclude_ids: pd.Series):
        """Requests all tiles. Should work for both synthetic and Lipac."""
        all_tiles = self.request_tiles_by_condition(where="id")
        return all_tiles[~all_tiles["id"].isin(exclude_ids)]

    def extract(self, selection: Optional[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        """Extract everything using ids."""
        if selection is None:
            return self.synthetic_df

        extract = self.synthetic_df.merge(
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
