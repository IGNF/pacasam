"""Integration tests : run all samplers on synthetic data."""
from pathlib import Path
import tempfile
import pytest
from pacasam.main import main
from pacasam.main import parser as main_parser

# ref : https://stackoverflow.com/questions/73178047/how-to-pytest-monkeypatch-multiple-argv-arguments


@pytest.mark.parametrize(
    "sampler_class", ["RandomSampler", "SpatialSampler", "TargettedSampler", "DiversitySampler", "TripleSampler", "OutliersSampler"]
)
@pytest.mark.parametrize("make_html_report", ["N"])
def test_all_samplers_on_synthetic_data(sampler_class, make_html_report):
    # Warning: overrident args should be already casted to Path and bool
    # TODO: could refactor by parsing args and adding them to the previously created namespace
    # so that we can give make_html_report="N" for instance.
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
    test_all_samplers_on_synthetic_data(sampler="RandomSampler", make_html_report="Y")
