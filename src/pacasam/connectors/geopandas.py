import logging
from pathlib import Path
from typing import Optional
import geopandas as gpd

from pacasam.connectors.connector import Connector


# TODO: add some simple tests.
class GeopandasConnector(Connector):
    def __init__(self, log: Optional[logging.Logger], gpd_database_path: Path):
        super().__init__(log=log)
        self.log = log
        self.gpd_database_path = gpd_database_path
        self._db = None

    @property
    def db(self):
        if self._db is None:
            self._db = gpd.read_file(self.gpd_database_path)
            # TODO: check does it work if the data is in a store?
        return self._db
