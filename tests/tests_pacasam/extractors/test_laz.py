from pathlib import Path
import tempfile
import numpy as np
import laspy
import pytest
from pacasam.extractors.extractor import all_files_can_be_accessed, check_sampling_format, load_sampling_with_checks

from pacasam.extractors.laz import (
    GEOMETRY_COLNAME,
    colorize_single_patch,
    extract_single_patch_from_LasData
)
from conftest import (
    LEFTY,
    LEFTY_DOWN_GEOMETRY,
    LEFTY_UP_GEOMETRY,
    RIGHTY,
    RIGHTY_DOWN_GEOMETRY,
    RIGHTY_UP_GEOMETRY,
)
from pacasam.samplers.sampler import SPLIT_COLNAME

# Useful constants to avoid magic numbers
WHITE_COLOR_VALUE = 65280
PATCH_WIDTH_METERS = 50
ONE_METER_ABS_TOLERANCE = 1
RANDOM_INT = 55


def test_check_files_accessibility():
    # Test when all files exist - we test this with this module's own path.
    file_paths = [LEFTY, RIGHTY]
    assert all_files_can_be_accessed(file_paths)

    # Test when some files do not exist
    file_paths = [LEFTY, Path("fake_non_existing_file.txt"), RIGHTY]
    assert not all_files_can_be_accessed(file_paths)


def test_check_sampling_format(tiny_synthetic_sampling):
    # test the check function on a tiny synthetic sampling that we now is compliant
    sampling = tiny_synthetic_sampling
    check_sampling_format(sampling)

    # bad type
    bad_split_type = sampling.copy()
    bad_split_type[SPLIT_COLNAME] = RANDOM_INT
    with pytest.raises(TypeError):
        check_sampling_format(bad_split_type)

    # bad type
    bad_geom_type = sampling.copy()
    bad_geom_type[GEOMETRY_COLNAME] = RANDOM_INT
    with pytest.raises(TypeError):
        check_sampling_format(bad_geom_type)

    # missing column
    del sampling[SPLIT_COLNAME]
    with pytest.raises(ValueError):
        check_sampling_format(sampling)


def test_load_sampling_with_checks(toy_sampling_file):
    df_loaded = load_sampling_with_checks(toy_sampling_file.name)
    assert len(df_loaded)


@pytest.mark.parametrize(
    "cloud_path_and_bounds",
    [
        (LEFTY, LEFTY_UP_GEOMETRY.bounds),
        (LEFTY, LEFTY_DOWN_GEOMETRY.bounds),
        (RIGHTY, RIGHTY_UP_GEOMETRY.bounds),
        (RIGHTY, RIGHTY_DOWN_GEOMETRY.bounds),
    ],
)
def test_extract_single_patch_from_LasData(cloud_path_and_bounds):
    cloud_path, patch_bounds = cloud_path_and_bounds
    """Test the extraction of a single patch to the tmp file, based on bounds."""
    cloud = laspy.read(cloud_path)
    nocolor_patch_tmp_file: tempfile._TemporaryFileWrapper = extract_single_patch_from_LasData(cloud, cloud.header, patch_bounds)
    patch_data = laspy.read(nocolor_patch_tmp_file.name)
    # Test that non empty and the right size
    assert len(patch_data) > 0
    for dim in ["x", "y"]:
        assert patch_data[dim].max() - patch_data[dim].min() == pytest.approx(PATCH_WIDTH_METERS, abs=ONE_METER_ABS_TOLERANCE)


@pytest.mark.parametrize("cloud_path", [LEFTY, RIGHTY])
def test_lefty_and_righty_color_are_white_and_equal(cloud_path):
    """Verifies that test data is pure white (R==G==B, filled with 65280).

    Note: This is useful to tets colorization in test_colorize_single_patch.

    """
    lefty = laspy.read(cloud_path)
    assert np.array_equal(lefty.red, np.full_like(lefty.red, fill_value=WHITE_COLOR_VALUE))
    assert np.array_equal(lefty.red, lefty.green)
    assert np.array_equal(lefty.red, lefty.blue)


@pytest.mark.timeout(60)
@pytest.mark.parametrize("cloud_path", [Path(LEFTY), RIGHTY])
def test_colorize_single_patch(cloud_path):
    """Tests RGB+NIR colorization from orthoimages using pdaltools package."""
    with tempfile.NamedTemporaryFile(suffix=".LAZ", prefix="copy_of_test_data_") as tmp_copy:
        colorize_single_patch(cloud_path, Path(tmp_copy.name))
        cloud = laspy.read(tmp_copy.name)

        # Assert presence of all necessary fields.
        assert "red" in cloud.point_format.dimension_names
        assert "blue" in cloud.point_format.dimension_names
        assert "green" in cloud.point_format.dimension_names
        assert "nir" in cloud.point_format.dimension_names

        # Assert both non-white (i.e. colorization *did* happen) and non-trivial colorization
        for dim in ["red", "green", "blue", "nir"]:
            assert not np.array_equal(cloud[dim], np.full_like(cloud[dim], fill_value=WHITE_COLOR_VALUE))
            assert not np.array_equal(cloud[dim], np.full_like(cloud[dim], fill_value=0))
