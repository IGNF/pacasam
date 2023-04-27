import logging
from typing import Iterable
from pandas import Series
from geopandas import GeoDataFrame

from pacasam.samplers.sampler import TILE_INFO

log = logging.getLogger(__name__)


class Connector:
    """
    Connector to the database.
    Field `id` will be an integer ranging from 0 to db_size-1.
    This assumption facilitates random selection but might be excessive.
    """

    db_size: int
    db: GeoDataFrame

    def __init__(self):
        self.name: str = self.__class__.__name__
        self.log = None

    def request_patches_by_boolean_indicator(self) -> GeoDataFrame:
        """Requests patches by boolean indicator. Output schema: [id, dalle_id, geometry]"""
        raise NotImplementedError()

    def request_all_other_patches(self, exclude_ids: Iterable):
        """Requests all other patches."""
        return self.db[~self.db["id"].isin(exclude_ids)][TILE_INFO]

    def extract(self, ids: Series) -> GeoDataFrame:
        """Extract selected ids and geometries from the database."""
        raise NotImplementedError()
