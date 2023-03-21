from pathlib import Path
import sys

from sqlalchemy import MetaData
import sqlalchemy

directory = Path(__file__).resolve().parent.parent
sys.path.append(str(directory))

from pacasam.connectors.lipac import Connector, load_LiPaCConnector
from sqlalchemy.sql import text  # https://stackoverflow.com/a/75309321/8086033

import geopandas as gpd
import configparser

from pacasam.utils import load_config

# config = configparser.ConfigParser()
# config.read(c.CONFIG_FILE_NAME)
# lipac_username = config["LIDAR_PATCH_CATALOGUE"]["DB_LOGIN"]
# lipac_password = config["LIDAR_PATCH_CATALOGUE"]["DB_PASSWORD"]

config_file = Path("configs/lipac-optimization-config.yml")
optimization_config = load_config(config_file)
connector = load_LiPaCConnector(optimization_config["connector_kwargs"])
query = text('Select * into "#vignette_valid" FROM "vignette" WHERE nb_points_total > 50000')
connector.session.execute(query)


gdf = gpd.read_postgis(query, connector.engine.connect(), geom_col="geometrie")
print(gdf)

with connector.session.begin() as con:
    df = gpd.read_sql_query(query, con)
