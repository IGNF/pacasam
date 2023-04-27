# copy of https://github.com/IGNF/panini/blob/main/connector.py

import logging
from typing import Generator, Iterable, Optional
import pandas as pd
import geopandas as gpd

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.engine import URL
import yaml
from pacasam.connectors.connector import Connector
from pacasam.samplers.sampler import TILE_INFO


def geometrie_to_geometry_col(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.rename(columns={"geometrie": "geometry"}).set_geometry("geometry")
    return gdf


# TODO: abstract a GeoDataframeConnector that wokr on a geopandas, and inherit from it for SuyntheticConnector and LiPaCConnector
class LiPaCConnector(Connector):
    lambert_93_crs = 2154

    def __init__(
        self,
        log: logging.Logger,
        username: str,
        password: str,
        db_lipac_host: str,
        db_lipac_name: str,
        extraction_sql_query: str,
        max_chunksize_for_postgis_extraction: int = 100000,
    ):
        super().__init__()
        self.log = log
        self.username = username
        self.host = db_lipac_host
        self.db_name = db_lipac_name
        self.create_session(password)
        self.db = self.extract_all_samples_as_a_df(extraction_sql_query, max_chunksize_for_postgis_extraction)
        self.db_size = len(self.db)

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

    def extract_all_samples_as_a_df(self, extraction_sql_query: str, max_chunksize_for_postgis_extraction: int) -> gpd.GeoDataFrame:
        """This function extracts all data from a PostGIS database.

        It uses using the SQL query provided as a parameter, and returns a
        GeoDataFrame containing the results.

        Data is read data the database in blocks of size `CHUNKSIZE_FOR_POSTGIS_REQUESTS`.
        This allows processing the data in blocks rather than loading all of it into memory at once.
        """
        self.log.info(f"Requesting the LiPaC database via the following SQL command: \n {extraction_sql_query}")
        chunks: Generator = gpd.read_postgis(
            text(extraction_sql_query), self.engine.connect(), geom_col="geometrie", chunksize=max_chunksize_for_postgis_extraction
        )
        gdf: gpd.GeoDataFrame = pd.concat(chunks)
        gdf = gdf.set_crs(self.lambert_93_crs)
        gdf = geometrie_to_geometry_col(gdf)
        gdf = gdf.sort_values(by="id")
        return gdf

    def request_patches_by_boolean_indicator(self, bool_descriptor_name) -> gpd.GeoDataFrame:
        return self.db.query(bool_descriptor_name)[TILE_INFO]

    def request_all_other_patches(self, exclude_ids: Iterable):
        """Requests all other patches."""
        other_patches = self.db[TILE_INFO]
        return other_patches[~other_patches["id"].isin(exclude_ids)]

    def extract(self, selection: Optional[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        """Extract using ids. If selection is None, select everything."""
        if selection is None:
            return self.db

        extract = self.db.merge(
            selection,
            how="inner",
            on="id",
        )
        return extract


def load_LiPaCConnector(**lipac_kwargs) -> LiPaCConnector:
    with open(lipac_kwargs["credentials_file_path"], "r") as credentials_file:
        credentials = yaml.safe_load(credentials_file)
    lipac_username = credentials["DB_LOGIN"]
    lipac_password = credentials["DB_PASSWORD"]
    del lipac_kwargs["credentials_file_path"]  # not needed anymore
    return LiPaCConnector(username=lipac_username, password=lipac_password, **lipac_kwargs)
