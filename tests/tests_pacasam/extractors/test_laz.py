from pathlib import Path
import tempfile
from pacasam.extractors.laz import LAZ_FILE_COLNAME, all_files_can_be_accessed, check_sampling_format, load_sampling_df_with_checks
from pacasam.utils import CONNECTORS_LIBRARY
import geopandas as gpd
import shapely

LEFTY = "tests/data/792000_6272000-50mx100m-left.las"
LEFTY_GEOMETRY = shapely.box(xmin=792000, ymin=6271171, xmax=792050, ymax=6271271)
RIGHTY = "tests/data/792000_6272000-50mx100m-right.las"
RIGHTY_GEOMETRY = shapely.box(xmin=792050, ymin=6271171, xmax=792100, ymax=6271271)


def test_check_files_accessibility():
    # Test when all files exist - we test this with this module's own path.
    file_paths = [LEFTY, RIGHTY]
    assert all_files_can_be_accessed(file_paths)

    # Test when some files do not exist
    file_paths = [LEFTY, Path("non_existing_file.txt"), RIGHTY]
    assert not all_files_can_be_accessed(file_paths)


def test_check_sampling_format_based_on_synthetic_data():
    # Small synthetic data in db
    connector_class = CONNECTORS_LIBRARY.get("SyntheticConnector")
    connector = connector_class(log=None, binary_descriptors_prevalence=[0.1], db_size=10)
    df = connector.db
    df["split"] = "train"
    # TODO: replace with the path to an actual LAZ file
    df[LAZ_FILE_COLNAME] = __file__
    check_sampling_format(df)


# todo: convert the toy data to LAZ format to gain even more space.
def test_load_sampling_df_with_checks_from_toy_data():
    # idea: for now we create a fake sampling that includes patches from
    # toy las. Later on we might automate this and it might become
    # its own Connector, that takes LAS as input and returns the metadata
    # as outputs.
    df = gpd.GeoDataFrame(
        data={
            "geometry": [LEFTY_GEOMETRY, LEFTY_GEOMETRY, RIGHTY_GEOMETRY, RIGHTY_GEOMETRY],
            LAZ_FILE_COLNAME: [LEFTY, LEFTY, RIGHTY, RIGHTY],
            "split": ["train", "val", "train", "val"],
        },
        crs="EPSG:2154",
    )
    temporary_gpkg = tempfile.NamedTemporaryFile(suffix=".gpkg")
    df.to_file(temporary_gpkg)

    # test loading
    df_loaded = load_sampling_df_with_checks(temporary_gpkg.name)
    assert len(df_loaded)
