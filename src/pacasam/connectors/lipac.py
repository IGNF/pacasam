import logging
from typing import Generator, Literal, Optional, Union

import pandas as pd
import geopandas as gpd
from geopandas import GeoDataFrame

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.engine import URL
import yaml
from pacasam.connectors.connector import GEOMETRY_COLNAME, Connector
from pacasam.samplers.sampler import PATCH_ID_COLNAME

TEST_COLNAME_IN_LIPAC = "test"
SPLIT_TYPE = Union[Literal["train"], Literal["test"], Literal["any"]]


class LiPaCConnector(Connector):
    lambert_93_crs = 2154

    def __init__(
        self,
        log: logging.Logger,
        username: str,
        password: str,
        db_lipac_host: str,
        db_lipac_name: str,
        extraction_sql_query_path: str,
        split: SPLIT_TYPE,
        max_chunksize_for_postgis_extraction: int = 100000,
    ):
        """Connector to interface with the Lidar-Patch-Catalogue database and perform queries.

        Args:
            log (logging.Logger): _description_
            username (str): username to connect to the database (must have read credentials)
            password (str): password to connect to the database
            db_lipac_host (str): name of the database host machine
            db_lipac_name (str): name of the database
            extraction_sql_query_path (str): path to a .SQL file
            split (str): desired split, among `train`,`test`, or `any`. Will filter based on the `test` variable in Lipac.
            max_chunksize_for_postgis_extraction (int, optional): For chunk-reading the (large) database. Defaults to 100000.

        """
        super().__init__()
        self.log = log
        self.username = username
        self.host = db_lipac_host
        self.db_name = db_lipac_name
        self.create_session(password)
        with open(extraction_sql_query_path, "r") as file:
            extraction_sql_query = file.read()
        self.db = self.extract_all_samples_as_a_df(extraction_sql_query, max_chunksize_for_postgis_extraction)
        self.db = filter_lipac_patches_on_split(db=self.db, test_colname=TEST_COLNAME_IN_LIPAC, desired_split=split)
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
            text(extraction_sql_query), self.engine.connect(), geom_col=GEOMETRY_COLNAME, chunksize=max_chunksize_for_postgis_extraction
        )
        gdf: gpd.GeoDataFrame = pd.concat(chunks)
        gdf = gdf.set_crs(self.lambert_93_crs)
        gdf = gdf.sort_values(by=PATCH_ID_COLNAME)
        return gdf

    def extract(self, selection: Optional[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        """Extract using ids. If selection is None, select everything."""
        extract = self.db.merge(
            selection,
            how="inner",
            on=PATCH_ID_COLNAME,
        )
        return extract


def filter_lipac_patches_on_split(db: GeoDataFrame, test_colname: str, desired_split: SPLIT_TYPE):
    """Filter patches based on the desired split.

    Parameters
    ----------
    db : GeoDataFrame
        The input GeoDataFrame containing the patches to filter.
    split_colname : str
        The name of the column containing the split information.
        It contains True for test patches, and False or None for other patches.
    desired_split : SPLIT_TYPE
        The desired split type to filter patches. Valid options are 'train', 'test', or 'any'.

    Returns
    -------
    GeoDataFrame
        The filtered GeoDataFrame containing the patches matching the desired split.

    Raises
    ------
    ValueError
        If an invalid desired split is provided.

    Notes
    -----
    Following the Lipac design, this function assumes that NaN values in the split column correspond
    to non-test (and therefore train) samples.

    """
    if desired_split == "any":
        return db
    if desired_split == "test":
        return db[db[test_colname] == True]
    if desired_split == "train":
        return db[db[test_colname].isna() | (db[test_colname] == False)]
    else:
        raise ValueError(f"Invalid desired split: `{desired_split}`. Choose among `train`, `test`, or `any`.")


def load_LiPaCConnector(**lipac_kwargs) -> LiPaCConnector:
    with open(lipac_kwargs["credentials_file_path"], "r") as credentials_file:
        credentials = yaml.safe_load(credentials_file)
    lipac_username = credentials["DB_LOGIN"]
    lipac_password = credentials["DB_PASSWORD"]
    del lipac_kwargs["credentials_file_path"]  # not needed anymore
    return LiPaCConnector(username=lipac_username, password=lipac_password, **lipac_kwargs)
