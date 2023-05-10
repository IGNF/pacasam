from argparse import Namespace
from pathlib import Path
import tempfile
import numpy as np
from pdaltools.color import decomp_and_color
import laspy
import pytest

from pacasam.extractors.laz import (
    FILE_COLNAME,
    PATCH_ID_COLNAME,
    SPLIT_COLNAME,
    GEOMETRY_COLNAME,
    all_files_can_be_accessed,
    check_sampling_format,
    colorize_all_patches,
    format_new_patch_path,
    extract_laz_dataset,
    extract_patches_from_single_cloud,
    load_sampling_with_checks,
)
from conftest import LEFTY, NUM_PATCHED_IN_EACH_FILE, RIGHTY

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


# todo: convert the toy data to LAZ format to gain even more space.
def test_load_sampling_with_checks_from_toy_sampling(toy_sampling):
    df_loaded = load_sampling_with_checks(toy_sampling.name)
    assert len(df_loaded)


def test_extract_patches_from_single_cloud(toy_sampling):
    with tempfile.TemporaryDirectory() as dataset_root:
        # Keep only patches relative to a single file
        df_loaded = load_sampling_with_checks(toy_sampling.name)
        first_file = df_loaded[FILE_COLNAME].iloc[0]
        sampling_of_single_cloud = df_loaded[df_loaded[FILE_COLNAME] == first_file]

        # Perform extraction
        list_of_extracted_path = extract_patches_from_single_cloud(sampling_of_single_cloud, Path(dataset_root))
        # Assert that the files were created
        assert len(list_of_extracted_path) == len(sampling_of_single_cloud) == NUM_PATCHED_IN_EACH_FILE
        assert all_files_can_be_accessed(list_of_extracted_path)
        # Check that files are compliant laz files.
        for file_path in list_of_extracted_path:
            cloud = laspy.read(file_path)
            for dim in ["x", "y"]:
                assert cloud[dim].max() - cloud[dim].min() == pytest.approx(PATCH_WIDTH_METERS, abs=ONE_METER_ABS_TOLERANCE)


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
@pytest.mark.parametrize("cloud_path", [LEFTY, RIGHTY])
def test_colorize_single_patch(cloud_path):
    """Tests RGB+NIR colorization from orthoimages using pdaltools package.

    Why we use pytest-timeout:
        Colorization of small patch is usually almost instantaneous. But sometimes the geoportail is unstable
        and in those cases a a few retries are performed in decomp_and_color (every 15 seconds).
        Ref on pytest-timeout: https://pytest-with-eric.com/pytest-best-practices/pytest-timeout/

    """
    with tempfile.NamedTemporaryFile(suffix=".LAZ", prefix="copy_of_test_data_") as tmp_copy:
        # Copy to be extra safe that we do not modify input test files.
        decomp_and_color(cloud_path, tmp_copy.name)
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


def test_extract_dataset_from_toy_sampling(toy_sampling):
    """Test integration: end-to-end extraction+colorization"""
    with tempfile.TemporaryDirectory() as dataset_root:
        extract_laz_dataset(toy_sampling.name, Path(dataset_root))


@pytest.mark.parametrize("cloud_path", [LEFTY, RIGHTY])
def test_define_patch_path_for_extraction(cloud_path):
    with tempfile.TemporaryDirectory() as dataset_root:
        split = "train"
        patch_path = format_new_patch_path(
            Path(dataset_root),
            Path(cloud_path),
            Namespace(
                **{
                    SPLIT_COLNAME: split,
                    PATCH_ID_COLNAME: 42,
                }
            ),
        )
        assert patch_path.stem == f"{Path(cloud_path).stem}---0042"
        assert patch_path.parent.stem == split
        assert patch_path.suffix == ".laz"  # lowercase, always laz
