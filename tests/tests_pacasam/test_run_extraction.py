"""Integration tests : run extraction."""
import os
import tempfile
import pytest
from pacasam.run_extraction import run_extraction, parser
import glob


@pytest.mark.timeout(60)
@pytest.mark.slow
@pytest.mark.geoplateforme
# @pytest.mark.parametrize("num_jobs", ["2", "1"])
@pytest.mark.parametrize("num_jobs", ["1"])
# @pytest.mark.parametrize("toy_sampling_fixture_name", ["toy_sampling_file_with_orthoimagery_filepaths", "toy_sampling_file"])
@pytest.mark.parametrize("toy_sampling_fixture_name", ["toy_sampling_file_with_orthoimagery_filepaths"])
# Parallelization needs to be tested first, else there is some issue with laspy.read
# trying without success to open the cloud that was previously opened successfully in single processing.
def test_run_extraction_laz_colorize(toy_sampling_fixture_name, num_jobs, request):
    with tempfile.TemporaryDirectory(prefix=f"num_jobs_{num_jobs}_") as tmp_output_path:
        toy_sampling_file = request.getfixturevalue(toy_sampling_fixture_name)
        args = parser.parse_args(
            args=[
                "--sampling_path",
                toy_sampling_file.name,
                "--dataset_root_path",
                tmp_output_path,
                "--extractor_class",
                "LAZExtractor",
                "--num_jobs",
                num_jobs,
            ]
        )
        run_extraction(args)
        created_files = glob.glob(str(args.dataset_root_path / "**/*"))
        assert len(created_files) == 4


@pytest.mark.timeout(60)
@pytest.mark.slow
@pytest.mark.geoplateforme
@pytest.mark.parametrize("num_jobs", ["1", "2"])
def test_run_extraction_bd_ortho_today(toy_sampling_file, num_jobs):
    with tempfile.TemporaryDirectory() as tmp_output_path:
        args = parser.parse_args(
            args=[
                "--sampling_path",
                toy_sampling_file.name,
                "--dataset_root_path",
                tmp_output_path,
                "--extractor_class",
                "BDOrthoTodayExtractor",
                "--num_jobs",
                num_jobs,
            ]
        )
        run_extraction(args)
        created_files = glob.glob(str(args.dataset_root_path / "**/*"))
        assert len(created_files) == 4


@pytest.mark.parametrize("num_jobs", ["1", "2"])
def test_run_extraction_bd_ortho_vintage(toy_sampling_file_with_orthoimagery_filepaths, num_jobs):
    os.environ["BD_ORTHO_VINTAGE_VRT_DIR"] = "tests/data/bd_ortho_vintage/"
    os.environ["NUM_JOBS"] = "1"  # default value, here only to give an example
    with tempfile.TemporaryDirectory() as tmp_output_path:
        args = parser.parse_args(
            args=[
                "--sampling_path",
                toy_sampling_file_with_orthoimagery_filepaths.name,
                "--dataset_root_path",
                tmp_output_path,
                "--extractor_class",
                "BDOrthoVintageExtractor",
                "--num_jobs",
                num_jobs,
            ]
        )
        run_extraction(args)
        created_files = glob.glob(str(args.dataset_root_path / "**/*"))
        assert len(created_files) == 2
