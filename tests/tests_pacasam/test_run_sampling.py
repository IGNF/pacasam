from pathlib import Path
import tempfile
import pytest
from pacasam.run_sampling import run_sampling
from pacasam.run_sampling import parser
from pacasam.utils import SAMPLERS_LIBRARY


def _run_sampling_by_args(sampler_class, connector_class="SyntheticConnector", config_file="configs/Synthetic.yml", make_html_report="F"):
    args = parser.parse_args(
        args=[
            "--sampler_class",
            sampler_class,
            "--connector_class",
            connector_class,
            "--config_file",
            config_file,
            "--make_html_report",
            make_html_report,
        ]
    )
    with tempfile.TemporaryDirectory() as args.output_path:
        gpkg_path = run_sampling(args)
        return gpkg_path


@pytest.mark.parametrize("sampler_class", SAMPLERS_LIBRARY.keys())
def test_run_sampling_on_synthetic_data(sampler_class):
    """Test the samplers on synthetic data."""
    _run_sampling_by_args(sampler_class)


@pytest.mark.slow  # Creating an html report is slow.
def test_make_html_report_option_after_random_sampler():
    """Integration test of sampling followed by html reporting."""
    _run_sampling_by_args(sampler_class="RandomSampler", make_html_report="Y")


def test_copy_and_then_random_sampling():
    # Get a copy via CopySampler, avoid deletion by keeping reference in scope
    tmp_gpkg_path: Path = _run_sampling_by_args(sampler_class="CopySampler")
    # Run the sampling using the default config that currently only reads Synthetic Geopackage.
    _run_sampling_by_args(
        connector_class="GeopandasConnector", sampler_class="RandomSampler", config_file="configs/Synthetic_as_Geopackage.yml"
    )
