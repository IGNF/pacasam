import geopandas as gpd
from pacasam.connectors.lipac import Connector
import pacasam.connectors.lipac_constants as c

from sqlalchemy.sql import text  # https://stackoverflow.com/a/75309321/8086033


import configparser

config = configparser.ConfigParser()
config.read(c.CONFIG_FILE_NAME)
lipac_username = config["LIDAR_PATCH_CATALOGUE"]["DB_LOGIN"]
lipac_password = config["LIDAR_PATCH_CATALOGUE"]["DB_PASSWORD"]
lipac_connector = Connector(lipac_username, lipac_password, c.DB_LIPAC_HOST, c.DB_LIPAC_NAME)

query = text('Select * FROM "Vignettes" WHERE "nb points bâti" >= 50')
lipac_connector.session.execute(query)

gdf = gpd.read_postgis(query, lipac_connector.engine.connect(), geom_col="geometrie")
print(gdf)

with lipac_connector.session.begin() as con:
    df = gpd.read_sql_query(query, con)
