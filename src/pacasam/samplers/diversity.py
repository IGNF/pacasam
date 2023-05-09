from typing import Dict, List, Optional
import numpy as np
from math import ceil, floor
import pandas as pd
from pandas import DataFrame
from sklearn.preprocessing import QuantileTransformer
from pacasam.connectors.connector import TILE_INFO

from pacasam.samplers.algos import fps
from pacasam.samplers.sampler import SELECTION_SCHEMA, Sampler


class DiversitySampler(Sampler):
    """
    A class for sampling patches via Farthest Point Sampling (FPS).

    Methods:
        get_patches(num_to_sample=1, normalization='standardization', quantile=50):
            Performs a sampling to cover the space of class histogram in order to include the diverse data scenes.

    """

    def get_patches(self, num_to_sample=None):
        """
        Performs a sampling to cover the space of class histogram in order to include the diverse data scenes.
        Class histogram is a proxy for scene content. E.g. highly present building + quasi absent vegetation = urban scene.
        We use Farthest Point Sampling (FPS) as a way to cover the space evenly.

        Parameters:
            num_to_sample (int): The number of point clouds to sample. If None, takes the value of target_total_num_patches.

        Parameters from configuration (under `DiversitySampler`):
            normalization (str): The type of normalization to apply to the class histograms. Must be either 'standardization'
                or 'quantilization'. Defaults to 'standardization'.
            n_quantiles (int): The number of quantiles to use when applying the 'quantilization' normalization. Ignored
                if normalization is set to 'standardization'. Defaults to 50.
            targets (List[str]): The columns considered for patch-to-patch distance in FPS.
            max_chunk_size_for_fps (int): max num of (consecutive) patches to process by FPS.
                Lower chunks means that we look for diversity in
            smaller sets of points, thus yielding a better spatial coverage.

        Returns:
            A pd.DataFrame with selected patches.

        Notes:
            We need to normalize each count of points to map them to class-specific notions from "absent" to "highly present".
            Most importantly, we need each feature to have a somewhat similar impact in sample-to-sample distances.

            Two normalization methods are proposed:
            - Standardization: the full space of histogram shall be covered, including outliers and unusual class histograms.
            - Quantilization: with a high number of quantiles, frequent values are spread out, and might therefore be
              privileged by FPS. On the contrary, outliers might be less represented.

        """

        if num_to_sample is None:
            num_to_sample = self.cf["target_total_num_patches"]

        cols_for_fps = self.cf["DiversitySampler"]["columns"]

        db = self.connector.db
        # We sort by id with the assumption that the chunks are consecutive patches, from consecutive slabs.
        # This enables FPS to have a notion of "diversity" that is spatially specific.
        # TODO: we could add bloc_id to make sure to work on consecutive slabs.
        db = db.sort_values(by=["dalle_id", "id"])
        db = db[TILE_INFO + cols_for_fps]
        db = normalize_df(
            df=db,
            columns=cols_for_fps,
            normalization=self.cf["DiversitySampler"]["normalization"],
            n_quantiles=self.cf["DiversitySampler"]["n_quantiles"],
        )

        # Farthest Point Sampling
        diverse_patches = list(self._get_patches_via_fps(db, num_to_sample, cols_for_fps))
        diverse_patches = pd.concat(diverse_patches, ignore_index=True)
        # ceil(...) might give a tiny amount of patches in excess
        diverse_patches = diverse_patches.iloc[:num_to_sample]
        return diverse_patches

    def _get_patches_via_fps(self, df: pd.DataFrame, num_to_sample: int, cols_for_fps: List[str]):
        max_chunk_size = self.cf["DiversitySampler"]["max_chunk_size_for_fps"]
        if len(df) > max_chunk_size:
            target_proportion = num_to_sample / len(df)
            for chunk in yield_chunks(df, max_chunk_size):
                num_to_sample_in_chunk = ceil(len(chunk) * target_proportion)
                yield from self._get_patches_via_fps(chunk, num_to_sample=num_to_sample_in_chunk, cols_for_fps=cols_for_fps)
        else:
            diverse_idx = fps(arr=df[cols_for_fps].values, num_to_sample=num_to_sample)
            # Reset index to be sure our np indices can index the dataframe.
            diverse = df.reset_index(drop=True).loc[diverse_idx, TILE_INFO]
            diverse["sampler"] = self.name
            diverse["split"] = "test"
            if self.cf["frac_validation_set"] is not None:
                diverse = self._set_validation_patches_on_FPS_sampling(diverse)
            diverse = diverse[SELECTION_SCHEMA]
            yield diverse

    def _set_validation_patches_on_FPS_sampling(self, diverse):
        """Set a binary flag for the validation patches, selected by FPS.

        Note: cice property of FPS: using it on its own output starting from the same
        point would yield the same order. So we take the first n points as test_set
        so that they are well distributed.

        """
        diverse["split"] = "train"
        num_samples_val_set = floor(self.cf["frac_validation_set"] * len(diverse))
        # Reset index to be sure our np indices can index the dataframe.
        diverse = diverse.reset_index(drop=True)
        # TODO: debug and check if this reset is necessary
        diverse.loc[-num_samples_val_set:, ("split",)] = "val"
        return diverse


def yield_chunks(df, max_chunk_size):
    """Generator for splitting the dataframe."""
    for pos in range(0, len(df), max_chunk_size):
        yield df.iloc[pos : pos + max_chunk_size]


def normalize_df(df: DataFrame, columns: List[str], normalization="standardization", n_quantiles: Optional[int] = 50):
    """Normalize columns defining the classes histogram, ignoring zeros values

    Ref: https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.QuantileTransformer.html
    """
    # 1/3 Set zeros as NaN to ignore them.
    df = df.replace(to_replace=0, value=np.nan)

    # 2/3 Normalize columns to define a meaningful distance between histogram patches.

    if normalization == "standardization":
        df.loc[:, columns] = (df.loc[:, columns] - df.loc[:, columns].mean()) / df.loc[:, columns].std()
    else:
        qt = QuantileTransformer(n_quantiles=n_quantiles, random_state=0, subsample=100_000)
        df.loc[:, columns] = qt.fit_transform(df[columns].values)

    # 3/3 Set back zeros to the lowest present value (which comes from a value really close to zero).
    df = df.fillna(df.min())
    return df
