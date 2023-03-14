# copy of https://github.com/IGNF/panini/blob/main/connector.py

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.engine import URL

from pacasam.connectors.synthetic import Connector

log = logging.getLogger(__name__)

CREDENTIALS_FILE_PATH = "credentials.ini"  # with credentials.

# DB_LIPAC_HOST = "localhost"
DB_LIPAC_HOST = "lidar-ia-vm3"
DB_LIPAC_NAME = "lidar_patch_catalogue"

DB_UNI_HOST = "serveurbdudiff.ign.fr"
DB_UNI_NAME = "bduni_france_consultation"

# SRID_DICT = {"Lambert-93": 2154}


class LiPaCConnector(Connector):
    def __init__(self, username, password, host, db_name):
        self.username = username
        self.host = host
        self.db_name = db_name
        self.create_session(password)

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


def load_LiPaCConnector() -> LiPaCConnector:
    import configparser

    config = configparser.ConfigParser()
    config.read(CREDENTIALS_FILE_PATH)
    lipac_username = config["LIDAR_PATCH_CATALOGUE"]["DB_LOGIN"]
    lipac_password = config["LIDAR_PATCH_CATALOGUE"]["DB_PASSWORD"]
    return LiPaCConnector(lipac_username, lipac_password, DB_LIPAC_HOST, DB_LIPAC_NAME)
