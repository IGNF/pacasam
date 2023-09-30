"""Integration tests : run extraction."""
import os
import tempfile
import pytest
from pacasam.run_extraction import run_extraction, parser
import glob


@pytest.mark.timeout(60)
@pytest.mark.slow
@pytest.mark.geoportail
def test_run_extraction_laz(toy_sampling_file):
    with tempfile.TemporaryDirectory() as tmp_output_path:
        args = parser.parse_args(
            args=["--sampling_path", toy_sampling_file.name, "--dataset_root_path", tmp_output_path, "--extractor_class", "LAZExtractor"]
        )
        run_extraction(args)
        created_files = glob.glob(str(args.dataset_root_path / "**/*"))
        assert len(created_files) == 4


@pytest.mark.timeout(60)
@pytest.mark.slow
@pytest.mark.geoportail
def test_run_extraction_bd_ortho_today(toy_sampling_file):
    with tempfile.TemporaryDirectory() as tmp_output_path:
        args = parser.parse_args(
            args=[
                "--sampling_path",
                toy_sampling_file.name,
                "--dataset_root_path",
                tmp_output_path,
                "--extractor_class",
                "BDOrthoTodayExtractor",
            ]
        )
        run_extraction(args)
        created_files = glob.glob(str(args.dataset_root_path / "**/*"))
        assert len(created_files) == 4


def test_run_extraction_bd_ortho_vintage(toy_sampling_file_for_BDOrthoVintageExtractor):
    os.environ["BD_ORTHO_VINTAGE_VRT_DIR"] = "tests/data/bd_ortho_vintage/"
    os.environ["NUM_JOBS"] = "1"  # default value, here only to give an example
    with tempfile.TemporaryDirectory() as tmp_output_path:
        args = parser.parse_args(
            args=[
                "--sampling_path",
                toy_sampling_file_for_BDOrthoVintageExtractor.name,
                "--dataset_root_path",
                tmp_output_path,
                "--extractor_class",
                "BDOrthoVintageExtractor",
            ]
        )
        run_extraction(args)
        created_files = glob.glob(str(args.dataset_root_path / "**/*"))
        assert len(created_files) == 2
