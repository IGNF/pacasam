import logging
from math import ceil
from typing import List
import numpy as np
import pandas as pd
import geopandas as gpd

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
        raise NotImplementedError()

    def extract_using_ids(self, ids: pd.Series) -> gpd.GeoDataFrame:
        """Extract using ids."""
        raise NotImplementedError()


# TODO: choose if ids should be manipulated as sets instead of a pd.Series.
# Pros for pd.Series : sample operation.


class SyntheticConnector(Connector):
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
        self.synthetic_df = gpd.GeoDataFrame(data, columns=self.descriptor_names, geometry=None)
        self.synthetic_df["id"] = range(len(self.synthetic_df))

        # fake_grid_size = np.sqrt(db_size)
        self.synthetic_df["geometry"] = None

    def request_ids_where_above_zero(self, descriptor_name) -> pd.Series:
        return self.synthetic_df[self.synthetic_df[descriptor_name] > 0]["id"]

    def select_randomly_without_repetition(self, num_to_add_randomly: int, already_sampled_ids: pd.Series):
        # TODO: could be done with Series instead.
        candidates = set(range(self.db_size)) - set(i for i in already_sampled_ids)
        candidates = pd.Series(list(candidates), name="id")
        if num_to_add_randomly >= len(candidates):
            return candidates

        choice = candidates.sample(n=num_to_add_randomly, replace=False, random_state=0)
        return choice

    def extract_using_ids(self, ids: pd.Series) -> gpd.GeoDataFrame:
        """Extract everything using ids."""
        extract = self.synthetic_df.merge(
            ids,
            how="inner",
            on="id",
        )
        return extract
