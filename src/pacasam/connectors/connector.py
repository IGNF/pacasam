import logging
from typing import Iterable
from pandas import Series
from geopandas import GeoDataFrame


# TODO: document the necessary columns names for the sql request, in particular FILE_COLNAME

FILE_COLNAME = "file_path"
GEOMETRY_COLNAME = "geometry"
PATCH_ID_COLNAME = "id"

# TODO: generalize so that we do not need dalle_id, or at least it is called something else more general
# We could impose that patch_id and file_id are always present.
TILE_INFO = [PATCH_ID_COLNAME, "dalle_id"]

log = logging.getLogger(__name__)


class Connector:
    """
    Connector to the database.
    Field `id` will be an integer ranging from 0 to db_size-1.
    This assumption facilitates random selection but might be excessive.
    """

    db_size: int
    db: GeoDataFrame

    # TODO: log should always be a param here?
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
        return self.db[~self.db[PATCH_ID_COLNAME].isin(exclude_ids)][TILE_INFO]

    def extract(self, ids: Series) -> GeoDataFrame:
        """Extract selected ids and geometries from the database."""
        raise NotImplementedError()
