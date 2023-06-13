"""Integration tests : run extraction."""
import tempfile
import pytest
from pacasam.run_extraction import run_extraction, parser
import glob


@pytest.mark.timeout(60)
@pytest.mark.slow
@pytest.mark.geoportail  # This tests requests the geoportail
def test_run_extraction_laz(toy_sampling_file):
    """Run them

    Note: make_html_report is a parameter for activation in test_make_html_report_option_after_random_sampler.

    """
    with tempfile.TemporaryDirectory() as tmp_output_path:
        args = parser.parse_args(args=["--sampling_path", toy_sampling_file.name, "--dataset_root_path", tmp_output_path])
        run_extraction(args)
        created_files = glob.glob(str(args.dataset_root_path / "**/*"))
        # Only test num of files to avoid changing this test everytime we change the
        # format of the name of extracted files.
        assert len(created_files) == 4
