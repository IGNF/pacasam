# idea: for now we create a fake sampling that includes patches from
# toy las. Later on we might automate this and it might become
# its own Connector, that takes LAS as input and returns the metadata
# as outputs.

import tempfile
import geopandas as gpd
import shapely
import pytest

from pacasam.samplers.sampler import FILE_COLNAME

LEFTY = "tests/data/792000_6272000-50mx100m-left.las"
LEFTY_UP_GEOMETRY = shapely.box(xmin=792000, ymin=6271171 + 50, xmax=792050, ymax=6271271)
LEFTY_DOWN_GEOMETRY = shapely.box(xmin=792000, ymin=6271171, xmax=792050, ymax=6271271 - 50)

RIGHTY = "tests/data/792000_6272000-50mx100m-right.las"
RIGHTY_UP_GEOMETRY = shapely.box(xmin=792050, ymin=6271171 + 50, xmax=792100, ymax=6271271)
RIGHTY_DOWN_GEOMETRY = shapely.box(xmin=792050, ymin=6271171, xmax=792100, ymax=6271271 - 50)

NUM_PATCHED_IN_EACH_FILE = 2


@pytest.fixture(scope="session")
def toy_sampling():
    """Returns the temporary files to a toy sampling."""
    df = gpd.GeoDataFrame(
        data={
            "geometry": [LEFTY_UP_GEOMETRY, LEFTY_DOWN_GEOMETRY, RIGHTY_UP_GEOMETRY, RIGHTY_DOWN_GEOMETRY],
            FILE_COLNAME: [LEFTY, LEFTY, RIGHTY, RIGHTY],
            "split": ["train", "val", "train", "val"],
            "id": [0, 1, 2, 3],
        },
        crs="EPSG:2154",
    )
    toy_sampling_path = tempfile.NamedTemporaryFile(suffix=".gpkg")
    df.to_file(toy_sampling_path)
    return toy_sampling_path
