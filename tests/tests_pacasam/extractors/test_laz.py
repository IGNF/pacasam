from pathlib import Path
import tempfile
import numpy as np
import laspy
import pytest
import requests
from pacasam.extractors.extractor import (
    check_all_files_exist,
    check_sampling_format,
    load_sampling,
)

from pacasam.extractors.laz import (
    GEOMETRY_COLNAME,
    colorize_single_patch,
    extract_single_patch_from_LasData,
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
    check_all_files_exist(file_paths)

    # Test when some files do not exist
    file_paths = [LEFTY, "fake_non_existing_filetxt", RIGHTY]
    with pytest.raises(FileNotFoundError):
        check_all_files_exist(file_paths)


def test_check_sampling_format(synthetic_sampling):
    # test the check function on a tiny synthetic sampling that we now is compliant
    sampling = synthetic_sampling
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


def test_load_sampling(toy_sampling_file):
    df_loaded = load_sampling(toy_sampling_file.name)
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
@pytest.mark.slow  # This tests is somewhat slow
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
    assert np.array_equal(lefty.Red, np.full_like(lefty.Red, fill_value=WHITE_COLOR_VALUE))
    assert np.array_equal(lefty.Red, lefty.Green)
    assert np.array_equal(lefty.Red, lefty.Blue)


@pytest.mark.geoplateforme
@pytest.mark.timeout(60)
@pytest.mark.parametrize("cloud_path", [Path(LEFTY), Path(RIGHTY)])
@pytest.mark.parametrize("srid", [2154, 0, None])
def test_colorize_single_patch(cloud_path, srid):
    """Tests RGB+NIR colorization from orthoimages using pdaltools package."""
    with tempfile.NamedTemporaryFile(suffix=".LAZ", prefix="copy_of_test_data_") as tmp_copy:
        colorize_single_patch(cloud_path, Path(tmp_copy.name), srid=srid)
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


@pytest.mark.geoplateforme
@pytest.mark.timeout(60)
def test_colorize_with_bad_srid_raises_error():
    with tempfile.NamedTemporaryFile(suffix=".LAZ", prefix="copy_of_test_data_") as tmp_copy:
        cloud_path = Path(LEFTY)
        with pytest.raises(requests.exceptions.HTTPError) as _:
            colorize_single_patch(cloud_path, Path(tmp_copy.name), 123456789)
