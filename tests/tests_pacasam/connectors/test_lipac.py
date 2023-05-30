import pytest
from geopandas import GeoDataFrame

from pacasam.connectors.lipac import filter_lipac_patches_on_split

split_colname = "split"
# Mock data for testing
mock_db = GeoDataFrame({"split": ["test", "train", "train", None, "test", None], "data": [1, 2, 3, 4, 5, 6]})


def test_filter_lipac_patches_on_split_with_split_any():
    desired_split = "any"
    filtered_db = filter_lipac_patches_on_split(mock_db, split_colname, desired_split)
    assert len(filtered_db) == len(mock_db)


def test_filter_lipac_patches_on_split_with_split_test():
    split_colname = "split"
    desired_split = "test"
    filtered_db = filter_lipac_patches_on_split(mock_db, split_colname, desired_split)
    assert len(filtered_db) == 2
    assert all(filtered_db["split"] == "test")


def test_filter_lipac_patches_on_split_with_split_train():
    split_colname = "split"
    desired_split = "train"
    filtered_db = filter_lipac_patches_on_split(mock_db, split_colname, desired_split)
    assert len(filtered_db) == 4
    assert all(filtered_db["split"].isin(["train", None]))


def test_filter_lipac_patches_on_split_with_invalid_split():
    split_colname = "split"
    desired_split = "invalid"
    with pytest.raises(ValueError):
        filter_lipac_patches_on_split(mock_db, split_colname, desired_split)
