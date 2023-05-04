"""Integration tests : run all samplers on synthetic data."""
from pathlib import Path
import tempfile
import pytest
from pacasam.main import main
from pacasam.main import parser as main_parser

# ref : https://stackoverflow.com/questions/73178047/how-to-pytest-monkeypatch-multiple-argv-arguments


@pytest.mark.parametrize(
    "sampler", ["RandomSampler", "SpatialSampler", "TargettedSampler", "DiversitySampler", "TripleSampler", "OutliersSampler"]
)
def test_all_samplers_on_synthetic_data(sampler):
    # Warning: overrident args should be 
    namespace, _ = main_parser.parse_known_args(args="")  # use defaut parameters only
    namespace.sampler_class = sampler
    namespace.connector_class = "SyntheticConnector"
    namespace.config_file = Path("configs/Synthetic.yml")
    namespace.make_html_report = False
    with tempfile.TemporaryDirectory() as namespace.output_path:
        main(namespace)
