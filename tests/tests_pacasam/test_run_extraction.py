"""Integration tests : run extraction."""
import tempfile
from pacasam.run_extraction import run_extraction, parser

# ref : https://stackoverflow.com/questions/73178047/how-to-pytest-monkeypatch-multiple-argv-arguments


def test_run_extraction_laz(toy_sampling_file):
    """Run them

    Note: make_html_report is a parameter for activation in test_make_html_report_option_after_random_sampler.

    """
    with tempfile.TemporaryDirectory() as tmp_output_path:
        args = parser.parse_args(args=["--sampling_path", toy_sampling_file.name, "--dataset_root_path", tmp_output_path])
        run_extraction(args)
