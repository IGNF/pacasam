"""Integration tests : run extraction."""
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
        # Only test num of files to avoid changing this test everytime we change the
        # format of the name of extracted files.
        assert len(created_files) == 4


@pytest.mark.timeout(60)
@pytest.mark.slow
@pytest.mark.geoportail
def test_run_extraction_orthoimages(toy_sampling_file):
    with tempfile.TemporaryDirectory() as tmp_output_path:
        args = parser.parse_args(
            args=[
                "--sampling_path",
                toy_sampling_file.name,
                "--dataset_root_path",
                tmp_output_path,
                "--extractor_class",
                "OrthoimagesExtractor",
            ]
        )
        run_extraction(args)
        created_files = glob.glob(str(args.dataset_root_path / "**/*"))
        # Only test num of files to avoid changing this test everytime we change the
        # format of the name of extracted files.
        assert len(created_files) == 4
