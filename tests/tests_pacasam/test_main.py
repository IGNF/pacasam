"""Integration tests : run all samplers on synthetic data."""
import tempfile
import pytest
from pacasam.main import main
from pacasam.main import parser as main_parser
from pacasam.utils import SAMPLERS_LIBRARY

# ref : https://stackoverflow.com/questions/73178047/how-to-pytest-monkeypatch-multiple-argv-arguments


@pytest.mark.parametrize(
    "sampler_class", SAMPLERS_LIBRARY.keys()
)
@pytest.mark.parametrize("make_html_report", ["N"])
def test_all_samplers_on_synthetic_data(sampler_class, make_html_report):
    """Test all samplers on synthetic data.

    Note: make_html_report is a parameter for activation in test_make_html_report_option_after_random_sampler.

    """
    args = main_parser.parse_args(
        args=[
            "--sampler_class",
            sampler_class,
            "--connector_class",
            "SyntheticConnector",
            "--config_file",
            "configs/Synthetic.yml",
            "--make_html_report",
            make_html_report,
        ]
    )
    with tempfile.TemporaryDirectory() as args.output_path:
        main(args)


def test_make_html_report_option_after_random_sampler():
    """Integration test of sampling followed by html reporting."""
    test_all_samplers_on_synthetic_data(sampler_class="RandomSampler", make_html_report="Y")
