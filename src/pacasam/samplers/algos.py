import geopandas as gpd
import pandas as pd
from math import floor


def sample_randomly(tiles: gpd.GeoDataFrame, num_samples_to_sample: int):
    return tiles.sample(n=num_samples_to_sample, replace=False, random_state=1)


def sample_spatially_by_slab(tiles: gpd.GeoDataFrame, num_samples_to_sample: int):
    """Efficient spatial sampling by sampling in each slab, iteratively."""
    if len(tiles) == 0:
        return tiles
    # Step 1: start by sampling in each slab the minimal number of tiles by slab we would want.
    # Sample with replacement to avoid errors, dropping duplicates afterwards.
    # This leads us to be already close to our target num of samples.

    random_state = 0
    min_n_by_slab = floor(num_samples_to_sample / len(tiles["dalle_id"].unique()))
    min_n_by_slab = max(min_n_by_slab, 1)
    sampled_ids = tiles.groupby("dalle_id").sample(n=min_n_by_slab, random_state=random_state, replace=True)
    sampled_ids = sampled_ids.drop_duplicates(subset="id")
    if len(sampled_ids) > num_samples_to_sample:
        # We alreay have all the sample we need (case where num_samples_to_sample is low and we got 1 in each tile)
        return sampled_ids.sample(n=num_samples_to_sample, random_state=random_state)

    # Step 2: Complete, accounting for slabs with a small number of tiles by removing the already selected
    # ones from the pool, and sampling one tile at each iteration.
    # WARNING: the extreme case is where the is a mega concentration in a specific slab, and then we have to
    # loop to get every tile within (with a maximum of n~400 iterations since it is the max num of tile per slab.)
    while len(sampled_ids) < num_samples_to_sample:
        random_state += 1
        remaining_ids = tiles[~tiles["id"].isin(sampled_ids["id"])]
        add_these_ids = remaining_ids.groupby("dalle_id").sample(n=1, random_state=random_state, replace=False)

        if len(add_these_ids) + len(sampled_ids) > num_samples_to_sample:
            add_these_ids = add_these_ids.sample(n=num_samples_to_sample - len(sampled_ids), random_state=random_state)

        sampled_ids = pd.concat([sampled_ids, add_these_ids])
        # sanity check that ids were already uniques.
        sampled_ids_uniques = sampled_ids.drop_duplicates(subset=["id"])
        assert len(sampled_ids) == len(sampled_ids_uniques)
        sampled_ids = sampled_ids_uniques

    return sampled_ids
