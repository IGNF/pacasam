import logging
from math import ceil
from typing import List
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box

log = logging.getLogger(__name__)


class Connector:
    # TODO: use an interface.
    """
    Connector to the database.
    Field `id` will be an integer ranging from 0 to db_size-1.
    This assumption facilitates random selection but might be excessive.
    """
    db_size: int

    def request_ids_where_above_zero(self, descriptor_name) -> pd.Series:
        raise NotImplementedError()

    def select_randomly_without_repetition(self, num_to_add_randomly: int, already_sampled_ids: pd.Series):
        """Selects n *new* samples. Uses the fact that tiles ids are in range(0,db_size)."""
        candidates = set(range(self.db_size)) - set(i for i in already_sampled_ids)
        candidates = pd.Series(list(candidates), name="id")
        if num_to_add_randomly >= len(candidates):
            return candidates
        choice = candidates.sample(n=num_to_add_randomly, replace=False, random_state=0)
        return choice

    def extract_using_ids(self, ids: pd.Series) -> gpd.GeoDataFrame:
        """Extract using ids."""
        raise NotImplementedError()


class SyntheticConnector(Connector):
    # TODO: name should be an attribute of the base abstract class,n calculated with __class__.__name__
    name: str = "SyntheticConnector"

    def __init__(self, binary_descriptors_prevalence: List[float], db_size: int = 10000):
        self.db_size = db_size
        data = []
        for t in binary_descriptors_prevalence:
            n_target = ceil(t * db_size)
            d = np.concatenate([np.ones(shape=(n_target,)), np.zeros(shape=(db_size - n_target,))])
            np.random.shuffle(d)
            data += [d]
        data = np.column_stack(data)
        self.descriptor_names = [f"C{idx}" for idx in range(len(binary_descriptors_prevalence))]
        self.synthetic_df = gpd.GeoDataFrame(
            data, columns=self.descriptor_names, geometry=self._make_synthetic_geometries(), crs="EPSG:2154"
        )
        self.synthetic_df["id"] = range(len(self.synthetic_df))

    def request_ids_where_above_zero(self, descriptor_name) -> pd.Series:
        return self.synthetic_df[self.synthetic_df[descriptor_name] > 0][["id", "geometry"]]

    def extract_using_ids(self, ids: pd.Series) -> gpd.GeoDataFrame:
        """Extract everything using ids."""
        extract = self.synthetic_df.merge(
            ids,
            how="inner",
            on="id",
        )
        return extract

    def _make_synthetic_geometries(self):
        fake_grid_size = ceil(np.sqrt(self.db_size))
        # Cartesian product of range * tile_size
        tile_size = 50
        df_x = pd.DataFrame({"x": range(fake_grid_size)}) * tile_size
        df_y = pd.DataFrame({"y": range(fake_grid_size)}) * tile_size
        df_xy = df_x.merge(df_y, how="cross")
        df_geom = df_xy.apply(
            lambda row: box(row["x"], row["y"], row["x"] + tile_size, row["y"] + tile_size, ccw=False),
            axis=1,
        )

        return df_geom
