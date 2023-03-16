# copy of https://github.com/IGNF/panini/blob/main/connector.py

import logging
import pandas as pd
import geopandas as gpd

from sqlalchemy import create_engine, select, text
import sqlalchemy
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.engine import URL
from sqlalchemy import MetaData
from pacasam.connectors.synthetic import Connector

log = logging.getLogger(__name__)

CREDENTIALS_FILE_PATH = "credentials.ini"  # with credentials.

# DB_LIPAC_HOST = "localhost"
DB_LIPAC_HOST = "lidar-ia-vm3"
DB_LIPAC_NAME = "lidar_patch_catalogue_new"

DB_UNI_HOST = "serveurbdudiff.ign.fr"
DB_UNI_NAME = "bduni_france_consultation"

# SRID_DICT = {"Lambert-93": 2154}
CHUNKSIZE_FOR_EXTRACTION = 10000


class LiPaCConnector(Connector):
    name: str = "LiPaCConnector"

    def __init__(self, username, password, host, db_name):
        self.username = username
        self.host = host
        self.db_name = db_name
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

    def request_ids_where_above_zero(self, descriptor_name) -> pd.Series:
        # TODO: support override of the selection statement in vignette by a "where" argument.
        # This enables flexible descriptor, and no descriptors with "where TRUE".

        query = text(f'Select "id", "geometrie" FROM "vignette" WHERE "{descriptor_name}" > 0')
        try:
            gdf = gpd.read_postgis(query, self.engine.connect(), geom_col="geometrie")
        except sqlalchemy.exc.ProgrammingError:
            # TODO: Lipac needs to be updated to have integer-coding of booleans. Then we can get rid of this.
            query = text(f'Select "id", "geometrie" FROM "vignette" WHERE "{descriptor_name}" is true')
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


def load_LiPaCConnector() -> LiPaCConnector:
    # TODO: this loader should enable override of the DB_LIPAC_NAME and HOST, from the optimization config file.
    import configparser

    config = configparser.ConfigParser()
    config.read(CREDENTIALS_FILE_PATH)
    lipac_username = config["LIDAR_PATCH_CATALOGUE"]["DB_LOGIN"]
    lipac_password = config["LIDAR_PATCH_CATALOGUE"]["DB_PASSWORD"]
    return LiPaCConnector(lipac_username, lipac_password, DB_LIPAC_HOST, DB_LIPAC_NAME)
