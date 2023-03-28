import logging
from typing import Iterable
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
    def request_tiles_by_condition(self, where: str) -> gpd.GeoDataFrame:
        """Requests tiles matching conditions. Output schema: [id, dalle_id, geometry]"""
        raise NotImplementedError()

    def request_all_other_tiles(self, exclude_ids: Iterable):
        """Requests all tiles except the ones whose id is in exclude."""
        raise NotImplementedError()

    def extract(self, ids: pd.Series) -> gpd.GeoDataFrame:
        """Extract selected ids and geometries from the database."""
        raise NotImplementedError()
