"""


Note on tempfiles: we often return tempfile._TemporaryFileWrapper, which need to be kept in the scope in order
for the underlying file not to be deleted automatically. To read and write to the file, most functions will need
the actual name instead of an tempfile._TemporaryFileWrapper object. It is accessed with `temp_file_object.name`

"""


from pathlib import Path
import tempfile
import sys
from geopandas import GeoDataFrame
import geopandas as gpd
import shapely
import pytest

# Nota: use `pytest --fixture` to list them.

# Add the src subdir to have simple import in the test suite
# e.g. "import pacasam" instead of "import src.pacasam"
# Add the tests subdir for the same reason, to import from e.g. conftest.py
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir / "src"))
sys.path.append(str(root_dir / "tests"))


from pacasam.utils import CONNECTORS_LIBRARY
from pacasam.samplers.sampler import SPLIT_COLNAME
from pacasam.connectors.connector import FILE_COLNAME, GEOMETRY_COLNAME, PATCH_ID_COLNAME
from pacasam.connectors.synthetic import SyntheticConnector


LEFTY = "tests/data/792000_6272000-50mx100m-left.laz"
LEFTY_UP_GEOMETRY = shapely.box(xmin=792000, ymin=6271171 + 50, xmax=792050, ymax=6271271)
LEFTY_DOWN_GEOMETRY = shapely.box(xmin=792000, ymin=6271171, xmax=792050, ymax=6271271 - 50)

RIGHTY = "tests/data/792000_6272000-50mx100m-right.laz"
RIGHTY_UP_GEOMETRY = shapely.box(xmin=792050, ymin=6271171 + 50, xmax=792100, ymax=6271271)
RIGHTY_DOWN_GEOMETRY = shapely.box(xmin=792050, ymin=6271171, xmax=792100, ymax=6271271 - 50)

NUM_PATCHED_IN_EACH_FILE = 2


@pytest.fixture(scope="session")
def toy_sampling_file() -> tempfile._TemporaryFileWrapper:
    """Returns a temporary file of a toy sampling (geopackage).

    Note: We do not return `toy_sampling_file.name: str` directly since this would delete the temporary file
    when existing the scope of toy_sampling_file.
    """
    df = gpd.GeoDataFrame(
        data={
            GEOMETRY_COLNAME: [LEFTY_UP_GEOMETRY, LEFTY_DOWN_GEOMETRY, RIGHTY_UP_GEOMETRY, RIGHTY_DOWN_GEOMETRY],
            FILE_COLNAME: [LEFTY, LEFTY, RIGHTY, RIGHTY],
            SPLIT_COLNAME: ["train", "val", "train", "val"],
            PATCH_ID_COLNAME: [0, 1, 2, 3],
        },
        crs="EPSG:2154",
    )
    toy_sampling_tmp_file = tempfile.NamedTemporaryFile(suffix=".gpkg", prefix="toy_sampling_tmp_file_")
    df.to_file(toy_sampling_tmp_file)
    return toy_sampling_tmp_file


@pytest.fixture(scope="session")
def synthetic_connector() -> SyntheticConnector:
    """Synthetic connector to a (very tiny) fake database."""
    connector_class = CONNECTORS_LIBRARY.get("SyntheticConnector")
    connector = connector_class(log=None, binary_descriptors_prevalence=[0.1], db_size=10)
    return connector


@pytest.fixture(scope="session")
def tiny_synthetic_sampling(synthetic_connector: SyntheticConnector) -> GeoDataFrame:
    """Very tiny synthetic database with the columns that make it a sampling."""
    # Add the necessary elements to turn the db into a sampling
    synthetic_connector.db[SPLIT_COLNAME] = "train"
    synthetic_connector.db[FILE_COLNAME] = str(Path(LEFTY).resolve())
    return synthetic_connector.db
