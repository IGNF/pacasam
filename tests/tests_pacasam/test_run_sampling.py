import tempfile
import pytest
import geopandas as gpd
from pacasam.connectors.geopandas import GeopandasConnector
from pacasam.run_sampling import run_sampling
from pacasam.run_sampling import parser
from pacasam.samplers.random import RandomSampler
from pacasam.samplers.sampler import Sampler
from pacasam.utils import SAMPLERS_LIBRARY


def _run_sampling_by_args(sampler_class, output_path, connector_class, config_file):
    args = parser.parse_args(
        args=[
            "--sampler_class",
            sampler_class,
            "--connector_class",
            connector_class,
            "--config_file",
            config_file,
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
        gpkg_path = _run_sampling_by_args(
            sampler_class=sampler_class, output_path=output_path, connector_class="SyntheticConnector", config_file="configs/Synthetic.yml"
        )
        # valid for geopandas
        sampling = gpd.read_file(gpkg_path)
        # non empty
        assert len(sampling)
        # good schema
        assert all(c in sampling for c in Sampler.sampling_schema)


@pytest.mark.lipac
@pytest.mark.slow
@pytest.mark.parametrize("sampler_class", SAMPLERS_LIBRARY.keys())
def test_run_sampling_on_lipac(sampler_class):
    """Test the samplers on synthetic data."""
    with tempfile.TemporaryDirectory() as output_path:
        gpkg_path = _run_sampling_by_args(
            sampler_class=sampler_class, output_path=output_path, connector_class="LiPaCConnector", config_file="configs/Lipac.yml"
        )
        # valid for geopandas
        sampling = gpd.read_file(gpkg_path)
        # non empty
        assert len(sampling)
        # good schema
        assert all(c in sampling for c in Sampler.sampling_schema)


def test_sampling_again_from_a_previous_sampling(toy_sampling_file, session_logger):
    """Test sampling from a previous sampling output (geopackage)"""
    TWO_PATCHES_REMAIN_AFTER_SAMPLING = 2
    connector = GeopandasConnector(log=session_logger, gpd_database_path=toy_sampling_file.name, split="any")
    sampler = RandomSampler(
        connector=connector,
        sampling_config={"target_total_num_patches": TWO_PATCHES_REMAIN_AFTER_SAMPLING, "frac_validation_set": 0},
        log=session_logger,
    )
    # Perform sampling
    selection: gpd.GeoDataFrame = sampler.get_patches()
    gdf = connector.extract(selection)
    assert len(gdf) == TWO_PATCHES_REMAIN_AFTER_SAMPLING
