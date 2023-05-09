from pathlib import Path
import sys
import pytest
from geopandas import GeoDataFrame

# Add the src subdir to have simple import in the test suite
# e.g. "import pacasam" instead of "import src.pacasam"
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir / "src"))

from pacasam.extractors.laz import FILE_COLNAME, SPLIT_COLNAME
from pacasam.utils import CONNECTORS_LIBRARY
from pacasam.connectors.synthetic import SyntheticConnector


@pytest.fixture(scope="session")
def synthetic_connector() -> SyntheticConnector:
    connector_class = CONNECTORS_LIBRARY.get("SyntheticConnector")
    connector = connector_class(log=None, binary_descriptors_prevalence=[0.1], db_size=10)
    return connector


@pytest.fixture(scope="session")
def tiny_synthetic_sampling(synthetic_connector: SyntheticConnector) -> GeoDataFrame:
    # Add the necessary elements to turn the db into a sampling
    synthetic_connector.db[SPLIT_COLNAME] = "train"
    synthetic_connector.db[FILE_COLNAME] = str(Path("tests/data/792000_6272000-50mx100m-left.las").resolve())
    return synthetic_connector.db
