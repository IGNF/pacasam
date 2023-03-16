# copy of https://github.com/IGNF/panini/blob/main/connector.py

import logging
import pandas as pd
import geopandas as gpd

from sqlalchemy import create_engine, text
import sqlalchemy
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.engine import URL
from pacasam.connectors.synthetic import Connector

log = logging.getLogger(__name__)

CREDENTIALS_FILE_PATH = "credentials.ini"  # with credentials.

# SRID_DICT = {"Lambert-93": 2154}
CHUNKSIZE_FOR_EXTRACTION = 10000


class LiPaCConnector(Connector):
    def __init__(self, username: str, password: str, db_lipac_host: str, db_lipac_name: str):
        super().__init__()

        self.username = username
        self.host = db_lipac_host
        self.db_name = db_lipac_name
        self.create_session(password)
        self.db_size = self.session.execute(text('SELECT count(*) FROM "vignette"')).all()[0][0]

    def create_session(self, password):
        url = URL.create(
            drivername="postgresql",
            username=self.username,
            password=password,
            host=self.host,
            database=self.db_name,
        )

        self.engine = create_engine(url)
        self.session = scoped_session(sessionmaker())
        self.session.configure(bind=self.engine, autoflush=False, expire_on_commit=False)

    def request_ids_by_condition(self, where: str) -> pd.Series:
        # TODO: enables reading by chunk to anticipate larger database.

        query = text(f'Select "id", "geometrie" FROM "vignette" WHERE {where}')
        gdf = gpd.read_postgis(query, self.engine.connect(), geom_col="geometrie")

        return gdf

    def extract_using_ids(self, selected_ids: pd.Series) -> gpd.GeoDataFrame:
        """Extract using ids."""
        # Method by chunk :

        extract = []
        query = text('Select * FROM "vignette"')
        for chunk in gpd.read_postgis(
            query,
            self.engine.connect(),
            geom_col="geometrie",
            chunksize=CHUNKSIZE_FOR_EXTRACTION,
        ):
            # TODO: consider a merge to leverage hash values (?)
            extract += [chunk[chunk["id"].isin(selected_ids)]]
        return pd.concat(extract)


def load_LiPaCConnector(lipac_kwargs) -> LiPaCConnector:
    import configparser

    config = configparser.ConfigParser()
    config.read(CREDENTIALS_FILE_PATH)
    lipac_username = config["LIDAR_PATCH_CATALOGUE"]["DB_LOGIN"]
    lipac_password = config["LIDAR_PATCH_CATALOGUE"]["DB_PASSWORD"]
    return LiPaCConnector(username=lipac_username, password=lipac_password, **lipac_kwargs)
