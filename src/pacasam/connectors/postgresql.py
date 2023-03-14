# copy of https://github.com/IGNF/panini/blob/main/connector.py

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.engine import URL

from pacasam.connectors.synthetic import Connector

log = logging.getLogger(__name__)


class PostgreSQLConnector(Connector):
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
