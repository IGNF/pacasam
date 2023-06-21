import logging
from typing import Iterable
from pandas import Series
from geopandas import GeoDataFrame

# Those are the necessary columns that are needed in the database to perform a sampling.

FILE_PATH_COLNAME = "file_path"  # path for later extraction e.g. "/path/to/file.LAZ"
GEOMETRY_COLNAME = "geometry"  # Shapely geometry (note: only rectangular shapes aligend with x/y are supported)
PATCH_ID_COLNAME = "patch_id"  # Unique identifier to each patch
FILE_ID_COLNAME = "file_id"  # Unique identifier to each file.

# TODO: turn this into an attribute of Connector. Reference accordingly.
PATCH_INFO = [PATCH_ID_COLNAME, FILE_ID_COLNAME]

log = logging.getLogger(__name__)


class Connector:
    """Connector to a patch database."""

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
        return self.db.query(bool_descriptor_name)[PATCH_INFO]

    def request_all_other_patches(self, exclude_ids: Iterable) -> GeoDataFrame:
        """Requests all other patches."""
        return self.db[~self.db[PATCH_ID_COLNAME].isin(exclude_ids)][PATCH_INFO]

    def request_all_patches(self) -> GeoDataFrame:
        """Request all patches i.e. without excluding any patch."""
        return self.db[PATCH_INFO]

    def extract(self, ids: Series) -> GeoDataFrame:
        """Extract selected ids and geometries from the database."""
        raise NotImplementedError()
