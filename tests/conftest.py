"""
Pytest fixtures.
Run `pytest --fixture` to list them.

_______________

General notes:

Use of tempfile:
    We often return tempfile._TemporaryFileWrapper objects, both in test and in pacasam.
    They need to be kept in the scope to avoid automatic deletion while they are still needed.
    To read and write to the file, most functions will need the name and not the tempfile._TemporaryFileWrapper object.
    The name is accessed with `temp_file_object.name`.

Use pytest-timeout:
    Colorization of small patch is usually almost instantaneous. But sometimes IGN geoportail is unstable
    and in those cases a a few retries are performed in decomp_and_color (every 15 seconds).
    Ref on pytest-timeout: https://pytest-with-eric.com/pytest-best-practices/pytest-timeout/

"""


from pathlib import Path
import tempfile
import sys
from geopandas import GeoDataFrame
import geopandas as gpd
import numpy as np
import shapely
import pytest

# Add the src subdir to have simple import in the test suite
# e.g. "import pacasam" instead of "import src.pacasam"
# Add the tests subdir for the same reason, to import from e.g. conftest.py
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir / "src"))
sys.path.append(str(root_dir / "tests"))


from pacasam.utils import CONNECTORS_LIBRARY
from pacasam.samplers.sampler import SAMPLER_COLNAME, SPLIT_COLNAME
from pacasam.connectors.connector import FILE_ID_COLNAME, GEOMETRY_COLNAME, PATCH_ID_COLNAME, SRID_COLNAME
from pacasam.extractors.laz import FILE_PATH_COLNAME
from pacasam.extractors.bd_ortho_vintage import BDOrthoVintageExtractor
from pacasam.connectors.synthetic import SyntheticConnector


LEFTY = "tests/data/laz/792000_6272000-50mx100m-left.laz"
LEFTY_UP_GEOMETRY = shapely.box(xmin=792000, ymin=6271171 + 50, xmax=792050, ymax=6271271)
LEFTY_DOWN_GEOMETRY = shapely.box(xmin=792000, ymin=6271171, xmax=792050, ymax=6271271 - 50)

RIGHTY = "tests/data/laz/792000_6272000-50mx100m-right.laz"
RIGHTY_UP_GEOMETRY = shapely.box(xmin=792050, ymin=6271171 + 50, xmax=792100, ymax=6271271)
RIGHTY_DOWN_GEOMETRY = shapely.box(xmin=792050, ymin=6271171, xmax=792100, ymax=6271271 - 50)


NUM_TEST_FILES = 2
NUM_PATCHED_IN_EACH_FILE = 2


@pytest.fixture(scope="session")
def toy_sampling_file() -> tempfile._TemporaryFileWrapper:
    """Returns a temporary file of a toy sampling (geopackage).

    Note: We do not return `toy_sampling_file.name: str` directly since this would delete the temporary file
    when existing the scope of toy_sampling_file.
    """
    df = gpd.GeoDataFrame(
        data={
            PATCH_ID_COLNAME: [0, 1, 2, 3],
            GEOMETRY_COLNAME: [
                LEFTY_UP_GEOMETRY,
                LEFTY_DOWN_GEOMETRY,
                RIGHTY_UP_GEOMETRY,
                RIGHTY_DOWN_GEOMETRY,
            ],
            FILE_PATH_COLNAME: [LEFTY, LEFTY, RIGHTY, RIGHTY],
            FILE_ID_COLNAME: [
                "792000_6272000-50mx100m-left",
                "792000_6272000-50mx100m-left",
                "792000_6272000-50mx100m-right",
                "792000_6272000-50mx100m-right",
            ],
            SPLIT_COLNAME: ["train", "val", "train", "val"],
            SRID_COLNAME: [2154, 2154, 2154, 2154],
        },
        crs="EPSG:2154",
    )
    toy_sampling_tmp_file = tempfile.NamedTemporaryFile(suffix=".gpkg", prefix="toy_sampling_tmp_file_")
    df.to_file(toy_sampling_tmp_file)

    # Note: Uncomment to update the saved gpkg.
    # Versionnning this file is intended to facilitate CLI tests by users (see Makefile) and inspection.
    # df.to_file(Path("./tests/data/lefty_righty_sampling.gpkg"))

    return toy_sampling_tmp_file


@pytest.fixture(scope="session")
def toy_sampling_file_for_BDOrthoVintageExtractor(toy_sampling_file) -> tempfile._TemporaryFileWrapper:
    """Returns a temporary file of a toy sampling (geopackage) adapted to BDORthoVintageExtractor.

    This test illustrates that BDOrthoVintageExtractor accepts any rasterio-compatible raster format.
    """
    sampling = gpd.read_file(toy_sampling_file.name)
    sampling = sampling[sampling["file_path"].str.contains("left")]
    sampling = sampling.drop(columns=["file_path", "file_id"])
    sampling[BDOrthoVintageExtractor.rgb_column] = "tests/data/bd_ortho_vintage/rgb/D30-2021.vrt"
    sampling[BDOrthoVintageExtractor.irc_column] = [
        "tests/data/bd_ortho_vintage/irc/792000_6272000-50mx100m-left-patch-0000000.tiff",
        "tests/data/bd_ortho_vintage/irc/792000_6272000-50mx100m-left-patch-0000001.tiff",
    ]

    toy_sampling_tmp_file = tempfile.NamedTemporaryFile(suffix=".gpkg", prefix="toy_sampling_file_for_BDOrthoVintageExtractor")
    sampling.to_file(toy_sampling_tmp_file)

    # Note: Uncomment to update the saved gpkg.
    # Versionnning this file is intended to facilitate CLI tests by users (see Makefile) and inspection.
    # df.to_file(Path("./tests/data/bd_ortho_vintage/lefty_sampling_for_BDOrthoVintageExtractor.gpkg"))

    return toy_sampling_tmp_file


@pytest.fixture(scope="session")
def synthetic_connector() -> SyntheticConnector:
    """Synthetic connector to a (very tiny) fake database."""
    connector_class = CONNECTORS_LIBRARY.get("SyntheticConnector")
    connector = connector_class(log=None, binary_descriptors_prevalence=[0.1], db_size=20, split="train")
    return connector


@pytest.fixture()
def tiny_synthetic_sampling(synthetic_connector: SyntheticConnector) -> GeoDataFrame:
    """Very tiny synthetic database with the columns that make it a sampling."""
    # Add the necessary elements to turn the db into a sampling
    synthetic_connector.db[SPLIT_COLNAME] = np.random.choice(["train", "val", "test"], size=len(synthetic_connector.db), p=[0.5, 0.25, 0.25])
    synthetic_connector.db[FILE_PATH_COLNAME] = str(Path(LEFTY).resolve())
    synthetic_connector.db[SAMPLER_COLNAME] = np.random.choice(["sampler_1", "sampler_2"], size=len(synthetic_connector.db))
    return synthetic_connector.db
