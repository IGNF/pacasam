import logging
from pathlib import Path
import geopandas as gpd

from pacasam.connectors.connector import Connector
from pacasam.samplers.sampler import SAMPLER_COLNAME, SPLIT_COLNAME, SPLIT_POSSIBLE_VALUES


class GeopandasConnector(Connector):
    def __init__(self, log: logging.Logger, gpd_database_path: Path, split: SPLIT_POSSIBLE_VALUES):
        """Connector to interface with any geopandas-compatible file.

        Args:
            log (logging.Logger): shared logger
            gpd_database_path (Path): path to file to connect to (e.g. geopackage file).
            split (str): Unused. For compatibility with other samplers only.

        """

        super().__init__(log=log)
        self.gpd_database_path = Path(gpd_database_path).resolve()
        self._db = None

    @property
    def db(self):
        if self._db is None:
            self._db = gpd.read_file(self.gpd_database_path)
            # Those two columns are present if we read from a sampling (in particular: from the output of CopySampler).
            # We need to drop them to avoid conflicts when sampling again.
            self._db = self._db.drop(columns=[SPLIT_COLNAME, SAMPLER_COLNAME], errors="ignore")
        return self._db
