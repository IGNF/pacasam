from typing import List, Union
import numpy as np
import pandas as pd
from pandas import DataFrame
from math import floor


def sample_randomly(patches: DataFrame, num_to_sample: int):
    return patches.sample(n=num_to_sample, replace=False, random_state=0)


def sample_with_stratification(patches: DataFrame, num_to_sample: int, keys: Union[str, List[str]] = ["dalle_id"]):
    """Efficient spatial sampling by sampling in each slab, iteratively."""

    if len(patches) == 0:
        return patches

    # Step 1: start by sampling in each strata the minimal number of patches by strata we would want.
    # Sample with replacement to avoid errors, dropping duplicates afterwards.
    # This leads us to be already close to our target num of samples.

    min_n_by_strata = floor(num_to_sample / patches[keys].nunique())
    min_n_by_strata = max(min_n_by_strata, 1)
    # Sample with replacement in case a strata has few patches (e.g. near a water surface).
    sampled_patches = patches.groupby(keys).sample(n=min_n_by_strata, random_state=0, replace=True)
    sampled_patches = sampled_patches.drop_duplicates(subset="id")
    if len(sampled_patches) > num_to_sample:
        # We alreay have all the sample we need (case where num_samples_to_sample < number of stratas, and we got 1 in each tile)
        return sampled_patches.sample(n=num_to_sample, random_state=0)

    # Step 2: Complete, accounting for strata with a small number of patches by removing the already selected
    # ones from the pool, and sampling one tile at each iteration.
    # WARNING: the extreme case is where the is a mega concentration in a specific strata, and then we have to
    # loop to get every tile within (with a maximum of n~400 iterations since it is the max num of tile per strata.)
    while len(sampled_patches) < num_to_sample:
        remaining_ids = patches[~patches["id"].isin(sampled_patches["id"])]
        add_these_ids = remaining_ids.groupby(keys).sample(n=1, random_state=0)

        if len(add_these_ids) + len(sampled_patches) > num_to_sample:
            add_these_ids = add_these_ids.sample(n=num_to_sample - len(sampled_patches), random_state=0)

        sampled_patches: DataFrame = pd.concat([sampled_patches, add_these_ids], verify_integrity=True)

    return sampled_patches


def fps(arr: np.ndarray, num_to_sample: int):
    """
    Adapted from: https://minibatchai.com/sampling/2021/08/07/FPS.html
    points: [N, 3] array containing the whole point cloud
    n_samples: samples you want in the sampled point cloud typically << N
    Current perfs:  10k out of 100k takes around 30 seconds tops.
    15% of 75km² is 4500 samples, so this will work in the general case where targets account for most of the samples..
    TODO: check the FPS algo below.
    """
    arr = np.array(arr)

    # Represent the points by their indices in points
    points_left = np.arange(len(arr))  # [P]

    # Initialise an array for the sampled indices
    sample_inds = np.zeros(num_to_sample, dtype="int")  # [S]

    # Initialise distances to inf
    dists = np.ones_like(points_left) * float("inf")  # [P]

    # Select a point from points by its index, save it
    selected = 0
    sample_inds[0] = points_left[selected]

    # Delete selected
    points_left = np.delete(points_left, selected)  # [P - 1]

    # Iteratively select points for a maximum of n_samples
    for i in range(1, num_to_sample):
        # Find the distance to the last added point in selected
        # and all the others
        last_added = sample_inds[i - 1]

        dist_to_last_added_point = ((arr[last_added] - arr[points_left]) ** 2).sum(-1)  # [P - i]

        # If closer, updated distances
        dists[points_left] = np.minimum(dist_to_last_added_point, dists[points_left])  # [P - i]

        # We want to pick the one that has the largest nearest neighbour
        # distance to the sampled points
        selected = np.argmax(dists[points_left])
        sample_inds[i] = points_left[selected]

        # Update points_left
        points_left = np.delete(points_left, selected)

    return sample_inds
