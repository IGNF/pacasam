import logging
import tempfile
import pytest
import geopandas as gpd
from pacasam.connectors.geopandas import GeopandasConnector
from pacasam.run_sampling import run_sampling
from pacasam.run_sampling import parser
from pacasam.samplers.random import RandomSampler
from pacasam.utils import SAMPLERS_LIBRARY
from tests.conftest import LEFTY_RIGHTY_SAMPLING

log = logging.getLogger(__name__)


def _run_sampling_by_args(
    sampler_class, output_path, connector_class="SyntheticConnector", config_file="configs/Synthetic.yml", make_html_report="F"
):
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
            "--output_path",
            output_path,
        ]
    )
    gpkg_path = run_sampling(args)
    return gpkg_path


@pytest.mark.parametrize("sampler_class", SAMPLERS_LIBRARY.keys())
def test_run_sampling_on_synthetic_data(sampler_class):
    """Test the samplers on synthetic data."""
    with tempfile.TemporaryDirectory() as output_path:
        _run_sampling_by_args(sampler_class=sampler_class, output_path=output_path)


@pytest.mark.slow  # Creating an html report is slow.
def test_make_html_report_option_after_random_sampler():
    """Integration test of sampling followed by html reporting."""
    with tempfile.TemporaryDirectory() as output_path:
        _run_sampling_by_args(sampler_class="RandomSampler", output_path=output_path, make_html_report="Y")


def test_sampling_again_from_a_previous_sampling():
    TWO_OUT_OF_FOUR = 2
    connector = GeopandasConnector(log=log, gpd_database_path=LEFTY_RIGHTY_SAMPLING, split="any")
    sampler = RandomSampler(
        connector=connector, sampling_config={"target_total_num_patches": TWO_OUT_OF_FOUR, "frac_validation_set": 0}, log=log
    )
    # Perform sampling
    selection: gpd.GeoDataFrame = sampler.get_patches()
    gdf = connector.extract(selection)
    assert len(gdf) == TWO_OUT_OF_FOUR
