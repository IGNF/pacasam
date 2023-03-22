import logging
import yaml
import geopandas as gpd

log = logging.getLogger(__name__)

# TODO/ better logging : https://stackoverflow.com/a/15729700/8086033


def load_optimization_config(config_file):
    with open(config_file, "r") as file:
        cf = yaml.safe_load(file)

    # Calculate target size of test set
    # n = cf["num_tiles_in_sampled_dataset"]
    # log.info(f"Target dataset size: {n} tiles (S={(n*50*50/(1000*1000)):.2f})km2")
    # cf["size_of_test_set"] = floor(n * cf["frac_test_set"])
    # if isinstance(t, float):
    #     assert t < 1
    #     int_t = floor(n * t)
    #     cf["size_of_test_set"] = int_t
    # # log.info(f'Target test set size: {cf["size_of_test_set"]} tiles (frac={(int_t/n):.2f})')

    return cf


def drop_duplicates_by_id_and_log_sampling_attrition(log: logging.Logger, gdf: gpd.GeoDataFrame, sampling_name: str = "Targeted Sampling"):
    n_sampled = len(gdf)
    gdf = gdf.drop_duplicates(subset=["id"])
    n_distinct = len(gdf)
    log.info(f"{sampling_name}: {n_sampled} ids --> {n_distinct} distinct ids (redundancy ratio: {n_distinct/n_sampled:.03f}) ")
    return gdf
