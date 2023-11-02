import glob
import tempfile
from pathlib import Path
import geopandas as gpd
from pacasam.extractors.laz import FILE_PATH_COLNAME
from pacasam.prepare_parallel_extraction import split_sampling_by_file
from conftest import NUM_TEST_FILES


def test_split_sampling_by_file():
    sampling_path = Path("./tests/data/lefty_righty_sampling.gpkg")
    with tempfile.TemporaryDirectory() as sampling_parts_dir:
        sampling_parts_dir = Path(sampling_parts_dir)
        split_sampling_by_file(sampling_path, Path(sampling_parts_dir), FILE_PATH_COLNAME)

        # Check that all files are created in sampling_parts_dir
        created_files = glob.glob(str(sampling_parts_dir / "*"))
        assert len(created_files) == NUM_TEST_FILES
        # Check that no patch is lost
        sampling = gpd.read_file(sampling_path)
        sampling_parts = [gpd.read_file(f) for f in created_files]
        assert sum(len(part) for part in sampling_parts) == len(sampling)
        # check that the columns are the same
        for part in sampling_parts:
            assert all(sampling.columns == part.columns)
