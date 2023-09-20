"""Integration tests : run extraction."""
import tempfile
import pytest
from pacasam.run_extraction import run_extraction, parser
import glob

from conftest import BD_ORTHO_VINTAGE_SAMPLING


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
def test_run_extraction_bd_ortho_vintage():
    # TODO: this test operates directly on a mounted store-ref for now but will need change that for a local .jp2 file later
    with tempfile.TemporaryDirectory() as tmp_output_path:
        args = parser.parse_args(
            args=[
                "--sampling_path",
                BD_ORTHO_VINTAGE_SAMPLING,
                "--dataset_root_path",
                tmp_output_path,
                "--extractor_class",
                "BDOrthoVintageExtractor",
            ]
        )
        run_extraction(args)
        created_files = glob.glob(str(args.dataset_root_path / "**/*"))
        # Only test num of files to avoid changing this test everytime we change the
        # format of the name of extracted files.
        assert len(created_files) == 5


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
