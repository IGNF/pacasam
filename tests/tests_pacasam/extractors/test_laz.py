from argparse import Namespace
from pathlib import Path
import tempfile

import pytest
from pacasam.extractors.laz import (
    LAZ_FILE_COLNAME,
    PATCH_ID_COLNAME,
    SPLIT_COLNAME,
    all_files_can_be_accessed,
    check_sampling_format,
    define_patch_path_for_extraction,
    extract_dataset_from_sampling,
    extract_patches_from_single_cloud,
    load_sampling_df_with_checks,
)
from pacasam.utils import CONNECTORS_LIBRARY
import geopandas as gpd
import shapely

# idea: for now we create a fake sampling that includes patches from
# toy las. Later on we might automate this and it might become
# its own Connector, that takes LAS as input and returns the metadata
# as outputs.

LEFTY = "tests/data/792000_6272000-50mx100m-left.las"
LEFTY_UP_GEOMETRY = shapely.box(xmin=792000, ymin=6271171 + 50, xmax=792050, ymax=6271271)
LEFTY_DOWN_GEOMETRY = shapely.box(xmin=792000, ymin=6271171, xmax=792050, ymax=6271271 - 50)

RIGHTY = "tests/data/792000_6272000-50mx100m-right.las"
RIGHTY_UP_GEOMETRY = shapely.box(xmin=792050, ymin=6271171 + 50, xmax=792100, ymax=6271271)
RIGHTY_DOWN_GEOMETRY = shapely.box(xmin=792050, ymin=6271171, xmax=792100, ymax=6271271 - 50)

NUM_PATCHED_IN_EACH_FILE = 2

df = gpd.GeoDataFrame(
    data={
        "geometry": [LEFTY_UP_GEOMETRY, LEFTY_DOWN_GEOMETRY, RIGHTY_UP_GEOMETRY, RIGHTY_DOWN_GEOMETRY],
        LAZ_FILE_COLNAME: [LEFTY, LEFTY, RIGHTY, RIGHTY],
        "split": ["train", "val", "train", "val"],
        "id": [0, 1, 2, 3],
    },
    crs="EPSG:2154",
)
TOY_SAMPLING = tempfile.NamedTemporaryFile(suffix=".gpkg")
df.to_file(TOY_SAMPLING)


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
    df_loaded = load_sampling_df_with_checks(TOY_SAMPLING.name)
    assert len(df_loaded)


# This will mark the test as an expected failure only if it fails with an AssertionError.
# If it fails for any other reason, it will be treated as a regular test failure.
# TODO: remove when extraction is implemented.
@pytest.mark.xfail(strict=True)
def test_extract_patches_from_single_cloud():
    with tempfile.TemporaryDirectory() as dataset_root:
        df_loaded = load_sampling_df_with_checks(TOY_SAMPLING.name)

        # Keep only patches relative to a single file
        first_file = df_loaded[LAZ_FILE_COLNAME].iloc[0]
        sampling_of_single_cloud = df_loaded[df_loaded[LAZ_FILE_COLNAME] == first_file]
        list_of_extracted_path = extract_patches_from_single_cloud(sampling_of_single_cloud, Path(dataset_root))

        # Assert that the files were created
        assert len(list_of_extracted_path) == len(sampling_of_single_cloud) == NUM_PATCHED_IN_EACH_FILE
        assert all_files_can_be_accessed(list_of_extracted_path)

        # TODO: check that the content of the file is compliant e.g. that all points in the las are contained in the shape?


def test_extract_dataset_from_sampling():
    # integration test to be sure that all runs smoothly together
    with tempfile.TemporaryDirectory() as dataset_root:
        extract_dataset_from_sampling(TOY_SAMPLING.name, Path(dataset_root))


def test_define_patch_path_for_extraction():
    with tempfile.TemporaryDirectory() as dataset_root:
        split = "train"
        patch_path = define_patch_path_for_extraction(
            Path(dataset_root),
            Path("Anything/here/NAME_OF_LAZ.LAZ"),
            Namespace(
                **{
                    SPLIT_COLNAME: split,
                    PATCH_ID_COLNAME: 42,
                }
            ),
        )
        assert patch_path.stem == "NAME_OF_LAZ---0042"
        assert patch_path.parent.stem == split
        assert patch_path.suffix == ".laz"  # lowercase always
