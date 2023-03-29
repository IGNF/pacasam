# copy of https://github.com/IGNF/panini/blob/main/connector.py

import logging
from typing import Any, Generator, Iterable, Optional, Union
import pandas as pd
import geopandas as gpd

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.engine import URL
from pacasam.connectors.connector import Connector
from pacasam.samplers.sampler import TILE_INFO

log = logging.getLogger(__name__)

# TODO: should be a lipac kwargs as well.
CREDENTIALS_FILE_PATH = "credentials.ini"  # with credentials.
CHUNKSIZE_FOR_POSTGIS_REQUESTS = 100000


def geometrie_to_geometry_col(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.rename(columns={"geometrie": "geometry"}).set_geometry("geometry")
    return gdf


# TODO: abstract a GeoDataframeConnector that has everything to wokr on a geopandas, and inherit from it for SuyntheticConnector and LiPaCOfflineConnector
class LiPaCOfflineConnector(Connector):
    lambert_93_crs = 2154

    def __init__(
        self, username: str, password: str, db_lipac_host: str, db_lipac_name: str, extraction_sql_query: str = 'SELECT * FROM "vignette"'
    ):
        super().__init__()

        self.username = username
        self.host = db_lipac_host
        self.db_name = db_lipac_name
        self.create_session(password)
        self.db_size = self.session.execute(text('SELECT count(*) FROM "vignette"')).all()[0][0]
        self.df = self.extract_all(extraction_sql_query)

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

    def extract_all_samples_as_a_df(self, extraction_sql_query: str) -> gpd.GeoDataFrame:
        chunks: Generator = gpd.read_postgis(
            text(extraction_sql_query), self.engine.connect(), geom_col="geometrie", chunksize=CHUNKSIZE_FOR_POSTGIS_REQUESTS
        )
        gdf: gpd.GeoDataFrame = pd.concat(chunks)
        gdf = gdf.set_crs(self.lambert_93_crs)
        gdf = geometrie_to_geometry_col(gdf)
        return gdf

    def request_tiles_by_condition(self, where: str) -> gpd.GeoDataFrame:
        # dataframe need diff query than sql : use == instead of =,
        return self.df.query(where)[TILE_INFO]

    def request_all_other_tiles(self, exclude_ids: Iterable):
        """Requests all other tiles."""
        other_tiles = self.df[TILE_INFO]
        return other_tiles[~other_tiles["id"].isin(exclude_ids)]

    def extract(self, selection: Optional[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        """Extract using ids. If selection is None, select everything."""
        if selection is None:
            return self.df

        extract = self.df.merge(
            selection,
            how="inner",
            on="id",
        )
        return extract


def load_LiPaCOfflineConnector(**lipac_kwargs) -> LiPaCOfflineConnector:
    import configparser

    config = configparser.ConfigParser()
    config.read(CREDENTIALS_FILE_PATH)
    lipac_username = config["LIDAR_PATCH_CATALOGUE"]["DB_LOGIN"]
    lipac_password = config["LIDAR_PATCH_CATALOGUE"]["DB_PASSWORD"]
    return LiPaCOfflineConnector(username=lipac_username, password=lipac_password, **lipac_kwargs)
