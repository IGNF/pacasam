"""Integration tests : run all samplers on synthetic data."""
import tempfile
import pytest
from pacasam.run_sampling import run_sampling
from pacasam.run_sampling import parser
from pacasam.utils import SAMPLERS_LIBRARY


@pytest.mark.parametrize("sampler_class", SAMPLERS_LIBRARY.keys())
@pytest.mark.parametrize("make_html_report", ["N"])
def test_all_samplers_on_synthetic_data(sampler_class, make_html_report):
    """Test all samplers on synthetic data.

    Note: make_html_report is a parameter for activation in test_make_html_report_option_after_random_sampler.

    """
    args = parser.parse_args(
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
        run_sampling(args)


@pytest.mark.slow  # Creating an html report is slow.
def test_make_html_report_option_after_random_sampler():
    """Integration test of sampling followed by html reporting."""
    test_all_samplers_on_synthetic_data(sampler_class="RandomSampler", make_html_report="Y")
