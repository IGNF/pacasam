import pytest
from geopandas import GeoDataFrame

from pacasam.connectors.lipac import filter_lipac_patches_on_split

# Mock data for testing
MOCK_TEST_COLNAME = "test"
NUM_TRUES = 2
NUM_OTHERS = 4
mock_db = GeoDataFrame({MOCK_TEST_COLNAME: [True, None, False, None, True, None], "data": [1, 2, 3, 4, 5, 6]})


def test_filter_lipac_patches_on_split_with_split_any():
    desired_split = "any"  # keep all
    filtered_db = filter_lipac_patches_on_split(mock_db, MOCK_TEST_COLNAME, desired_split)
    assert len(filtered_db) == len(mock_db)


def test_filter_lipac_patches_on_split_with_split_test():
    desired_split = "test"  # keep test
    filtered_db = filter_lipac_patches_on_split(mock_db, MOCK_TEST_COLNAME, desired_split)
    assert len(filtered_db) == NUM_TRUES
    assert all(filtered_db[MOCK_TEST_COLNAME])


def test_filter_lipac_patches_on_split_with_split_train():
    desired_split = "train"
    filtered_db = filter_lipac_patches_on_split(mock_db, MOCK_TEST_COLNAME, desired_split)
    assert len(filtered_db) == NUM_OTHERS
    assert all(filtered_db[MOCK_TEST_COLNAME].isin([False, None]))


def test_filter_lipac_patches_on_split_with_invalid_split():
    desired_split = "invalid"
    with pytest.raises(ValueError):
        filter_lipac_patches_on_split(mock_db, MOCK_TEST_COLNAME, desired_split)
