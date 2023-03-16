import logging
import pandas as pd
import geopandas as gpd

log = logging.getLogger(__name__)


class Connector:
    """
    Connector to the database.
    Field `id` will be an integer ranging from 0 to db_size-1.
    This assumption facilitates random selection but might be excessive.
    """

    db_size: int

    def __init__(self):
        self.name: str = self.__class__.__name__

    # TODO: add abstract decorator
    def request_ids_by_condition(self, where: str) -> gpd.GeoDataFrame:
        """Requests tiles matching conditions. Output schema: [id, dalle_id, geometry]"""
        raise NotImplementedError()

    def select_randomly_without_repetition(self, num_to_add_randomly: int, already_sampled_ids: pd.Series):
        """Selects n *new* samples. Uses the fact that tiles ids are in range(0,db_size).

        WARNING: this is not robust to deletion of single tile due to e.g. filters.
        """
        candidates = {a for a in range(self.db_size) if a not in already_sampled_ids}
        candidates = pd.Series(list(candidates), name="id")
        if num_to_add_randomly >= len(candidates):
            return candidates
        choice = candidates.sample(n=num_to_add_randomly, replace=False, random_state=0)
        return choice

    def extract_using_ids(self, ids: pd.Series) -> gpd.GeoDataFrame:
        """Extract selected ids and geometries from the database."""
        raise NotImplementedError()
