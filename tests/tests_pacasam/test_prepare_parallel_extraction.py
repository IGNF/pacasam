import glob
import tempfile
from pathlib import Path
import geopandas as gpd
from pacasam.prepare_parallel_extraction import get_stem_from_any_file_format, split_sampling_by_file
from tests.conftest import NUM_TEST_FILES


def test_get_stem_from_any_file_format_unix():
    file_path = "/path/to/file.txt"
    expected_stem = "file"
    result = get_stem_from_any_file_format(file_path)
    assert result == expected_stem


def test_get_stem_from_any_file_format_samba():
    file_path = r"\\store.ign.fr\store-lidarhd\file.laz"
    expected_stem = "file"
    result = get_stem_from_any_file_format(file_path)
    assert result == expected_stem


def test_split_sampling_by_file():
    sampling_path = Path("./tests/data/lefty_righty_sampling.gpkg")
    with tempfile.TemporaryDirectory() as sampling_parts_dir:
        sampling_parts_dir = Path(sampling_parts_dir)
        split_sampling_by_file(sampling_path, Path(sampling_parts_dir))

        # Check that all files are created in sampling_parts_dir
        created_files = glob.glob(str(sampling_parts_dir / "*"))
        assert len(created_files) == NUM_TEST_FILES
        # Check that no patch is lost
        sampling=gpd.read_file(sampling_path)
        sampling_parts = [gpd.read_file(f) for f in created_files]
        assert sum(len(part) for part in sampling_parts) == len(sampling)
        # check that the num of columns are the same
        for part in sampling_parts:
            assert all(sampling.columns == part.columns)
