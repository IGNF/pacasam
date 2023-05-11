from typing import List, Optional, Union
import numpy as np
import pandas as pd
from pandas import DataFrame
from math import floor

from sklearn.preprocessing import QuantileTransformer

from pacasam.connectors.connector import FILE_ID_COLNAME, PATCH_ID_COLNAME
from pacasam.exceptions import UnexpectedNaNValuesError

GLOBAL_RANDOM_STATE = 0
# To avoid DIV0 leading to nan values
EPSILON = 10e-6

def sample_randomly(patches: DataFrame, num_to_sample: int):
    if num_to_sample > len(patches):
        num_to_sample = len(patches)
    return patches.sample(n=num_to_sample, replace=False, random_state=GLOBAL_RANDOM_STATE)


def sample_with_stratification(patches: DataFrame, num_to_sample: int, keys: Union[str, List[str]] = FILE_ID_COLNAME):
    """Efficient spatial sampling by sampling in each slab, iteratively."""

    if len(patches) <= num_to_sample:
        return patches

    # Step 1: start by sampling in each strata the minimal number of patches by strata we would want.
    # Sample with replacement to avoid errors, dropping duplicates afterwards.
    # This leads us to be already close to our target num of samples.
    nunique = len(patches[keys].value_counts())
    min_n_by_strata = floor(num_to_sample / nunique)
    min_n_by_strata = max(min_n_by_strata, 1)
    # Sample with replacement in case a strata has few patches (e.g. near a water surface).
    sampled_patches = patches.groupby(keys).sample(n=min_n_by_strata, random_state=GLOBAL_RANDOM_STATE, replace=True)
    sampled_patches = sampled_patches.drop_duplicates(subset=PATCH_ID_COLNAME)

    # Case where we  have all the sample we need (i.e. num_samples_to_sample < number of stratas, and we got 1 in each tile)
    if len(sampled_patches) > num_to_sample:
        return sampled_patches.sample(n=num_to_sample, random_state=GLOBAL_RANDOM_STATE)

    # Step 2: Complete, accounting for strata with a small number of patches by removing the already selected
    # ones from the pool, and sampling one tile at each iteration.
    # WARNING: the extreme case is where the is a mega concentration in a specific strata, and then we have to
    # loop to get every tile within (with a maximum of n~400 iterations since it is the max num of tile per strata.)
    while len(sampled_patches) < num_to_sample:
        remaining_ids = patches[~patches[PATCH_ID_COLNAME].isin(sampled_patches[PATCH_ID_COLNAME])]
        add_these_ids = remaining_ids.groupby(keys).sample(n=1, random_state=GLOBAL_RANDOM_STATE)

        if len(add_these_ids) + len(sampled_patches) > num_to_sample:
            add_these_ids = add_these_ids.sample(n=num_to_sample - len(sampled_patches), random_state=GLOBAL_RANDOM_STATE)

        sampled_patches: DataFrame = pd.concat([sampled_patches, add_these_ids], verify_integrity=True)

    return sampled_patches



def yield_chunks(df, max_chunk_size):
    """Generator for splitting the dataframe."""
    for pos in range(0, len(df), max_chunk_size):
        yield df.iloc[pos : pos + max_chunk_size]


def normalize_df(df: DataFrame, columns: List[str], normalization="standardization", n_quantiles: Optional[int] = 50):
    """Normalize columns defining the classes histogram, ignoring zeros values

    Ref: https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.QuantileTransformer.html
    """

    # Sanity check: normalization methods here expect all columns to have some values
    if any(df.isna().sum() > 0):
        raise UnexpectedNaNValuesError(df)

    # 1/3 Set zeros as NaN to ignore them during
    df = df.replace(to_replace=0, value=np.nan)

    # 2/3 Normalize columns to define a meaningful distance between histogram patches.

    if normalization == "standardization":
        df.loc[:, columns] = (df.loc[:, columns] - df.loc[:, columns].mean()) / (df.loc[:, columns].std() + EPSILON)
    else:
        qt = QuantileTransformer(n_quantiles=n_quantiles, random_state=GLOBAL_RANDOM_STATE, subsample=100_000)
        df.loc[:, columns] = qt.fit_transform(df[columns].values)

    # 3/3 Set back zeros to the lowest present value (which comes from a value really close to zero).
    # Fillna with zero in case all input values where zero (typically when debugging with small data)
    fillna_values = df.min(numeric_only=True).fillna(0)
    df = df.fillna(fillna_values)
    return df


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
