from math import floor
import pytest
from pacasam.samplers.sampler import SPLIT_COLNAME
from pacasam.samplers.targetted import TargettedSampler
from pacasam.utils import load_sampling_config


def test_targetted_sampler_with_and_without_spatial_completion(synthetic_connector, session_logger):
    conf = load_sampling_config("configs/Synthetic.yml")
    # By default with spatial completion (Proportion of validation set is respected)
    sampler = TargettedSampler(connector=synthetic_connector, sampling_config=conf, log=session_logger)
    selection = sampler.get_patches()
    assert set(selection.sampler.unique()) == {"TargettedSampler", "SpatialSampler"}
    assert len(selection) == conf["target_total_num_patches"]
    assert len(selection[selection[SPLIT_COLNAME] == "val"]) == floor(conf["frac_validation_set"] * conf["target_total_num_patches"])

    # Alternatively : without spatial completion
    sampler = TargettedSampler(connector=synthetic_connector, sampling_config=conf, log=session_logger, complete_with_spatial_sampling=False)
    selection = sampler.get_patches()
    assert set(selection.sampler.unique()) == {"TargettedSampler"}
    assert 0 < len(selection)
    assert len(selection) < conf["target_total_num_patches"]


def test_targetted_sampler_with_too_many_required_patches(synthetic_connector, session_logger):
    conf = load_sampling_config("configs/Synthetic.yml")
    # test when targets are very high and sums above 100% of the total number of patches
    for k in conf["TargettedSampler"]["targets"]:
        conf["TargettedSampler"]["targets"][k]["target_min_samples_proportion"] = 0.99
    sampler = TargettedSampler(connector=synthetic_connector, sampling_config=conf, log=session_logger)
    with pytest.warns(UserWarning, match="Selected more than the desired total"):
        selection = sampler.get_patches()
    assert len(selection) > conf["target_total_num_patches"]
