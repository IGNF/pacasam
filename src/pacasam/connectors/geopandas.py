import logging
from pathlib import Path
from typing import Optional
import geopandas as gpd

from pacasam.connectors.connector import Connector
from pacasam.samplers.sampler import SPLIT_POSSIBLE_VALUES


# TODO: add some tests.
class GeopandasConnector(Connector):
    def __init__(self, log: Optional[logging.Logger], gpd_database_path: Path, split: SPLIT_POSSIBLE_VALUES):
        super().__init__(log=log)
        self.log = log
        self.gpd_database_path = Path(gpd_database_path).resolve()
        self._db = None

    @property
    def db(self):
        if self._db is None:
            # TODO: check that we do not have any remaining columns related to sampling :
            # split, sampler. We can ditch them here, or be sure elsewhere that it does not conflict.
            self._db = gpd.read_file(self.gpd_database_path)
            # TODO: check if it works if the data is in a store
        return self._db
