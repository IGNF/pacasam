from pacasam.samplers.targetted import TargettedSampler
from pacasam.utils import load_sampling_config
import geopandas as gpd


def test_targetted_sampler_with_and_without_spatial_completion(synthetic_connector, session_logger):
    conf = load_sampling_config("configs/Synthetic.yml")
    # By default: with spatial completion
    sampler = TargettedSampler(connector=synthetic_connector, sampling_config=conf, log=session_logger)
    selection: gpd.GeoDataFrame = sampler.get_patches()
    assert set(selection.sampler.unique()) == {"TargettedSampler", "SpatialSampler"}
    assert len(selection) == conf["target_total_num_patches"]

    # Alternatively : without spatial completion
    sampler = TargettedSampler(connector=synthetic_connector, sampling_config=conf, log=session_logger, complete_with_spatial_sampling=False)
    selection: gpd.GeoDataFrame = sampler.get_patches()
    assert set(selection.sampler.unique()) == {"TargettedSampler"}
    assert len(selection) < conf["target_total_num_patches"]
