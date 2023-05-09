import logging
from typing import Iterable
from pandas import Series
from geopandas import GeoDataFrame

# We need at least these information to perform sampling
TILE_INFO = ["id", "dalle_id"]

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

    def request_patches_by_boolean_indicator(self, bool_descriptor_name) -> GeoDataFrame:
        if self.db[bool_descriptor_name].dtype != "bool":
            raise KeyError(
                f"Descriptor `{bool_descriptor_name}` is not a boolean." "Only boolean descriptor are supported for targetting patches."
            )
        return self.db.query(bool_descriptor_name)[TILE_INFO]

    def request_all_other_patches(self, exclude_ids: Iterable):
        """Requests all other patches."""
        return self.db[~self.db["id"].isin(exclude_ids)][TILE_INFO]

    def extract(self, ids: Series) -> GeoDataFrame:
        """Extract selected ids and geometries from the database."""
        raise NotImplementedError()
