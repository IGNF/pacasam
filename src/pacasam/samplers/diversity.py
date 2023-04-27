import numpy as np
from math import ceil, floor
import pandas as pd
from sklearn.preprocessing import QuantileTransformer
from pacasam.connectors.connector import TILE_INFO

from pacasam.samplers.algos import fps
from pacasam.samplers.sampler import SELECTION_SCHEMA, Sampler


class DiversitySampler(Sampler):
    """
    A class for sampling patches via Farthest Point Sampling (FPS).

    Attributes:
        data (np.ndarray): A 2D numpy array representing the point cloud data.
        classes (np.ndarray): A 1D numpy array representing the class labels for each point.

    Methods:
        get_patches(num_diverse_to_sample=1, normalization='standardization', quantile=50):
            Performs a sampling to cover the space of class histogram in order to include the diverse data scenes.

    """

    def get_patches(self, num_diverse_to_sample=None):
        """
        Performs a sampling to cover the space of class histogram in order to include the diverse data scenes.
        Class histogram is a proxy for scene content. E.g. highly present building + quasi absent vegetation = urban scene.
        We use Farthest Point Sampling (FPS) as a way to cover the space evenly.

        Parameters:
            num_diverse_to_sample (int): The number of point clouds to sample. If None, takes the value of target_total_num_patches.

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

            Note that rare classes are already targeted spatially via sequential sampling. Adding them to the columns might give
            them a high weight, but it can still be done.

        """

        if num_diverse_to_sample is None:
            num_diverse_to_sample = self.cf["target_total_num_patches"]

        self.cols_for_fps = self.cf["DiversitySampler"]["columns"]

        db = self.connector.db.copy()
        # We sort by id with the assumption that the chunks are consecutive patches, from consecutive slabs.
        # This enables FPS to have a notion of "diversity" that is spatially specific.
        # TODO: we could add bloc_id to make sure to work on consecutive slabs.
        db = db.sort_values(by=["dalle_id", "id"])
        db = db[TILE_INFO + self.cols_for_fps]
        db = self.normalize_df(db, self.cols_for_fps)

        # Farthest Point Sampling
        diverse_patches = list(self._get_patches_via_fps(db, num_diverse_to_sample))
        diverse_patches = pd.concat(diverse_patches, ignore_index=True)
        # ceil(...) might give a tiny amount of patches in excess
        diverse_patches = diverse_patches.iloc[:num_diverse_to_sample]
        return diverse_patches

    def _get_patches_via_fps(self, df: pd.DataFrame, num_to_sample: int):
        max_chunk_size = self.cf["DiversitySampler"]["max_chunk_size_for_fps"]
        if len(df) > max_chunk_size:
            target_proportion = num_to_sample / len(df)
            for chunk in self.chunker(df, max_chunk_size):
                num_to_sample_in_chunk = ceil(len(chunk) * target_proportion)
                yield from self._get_patches_via_fps(chunk, num_to_sample=num_to_sample_in_chunk)
        else:
            diverse_idx = fps(arr=df[self.cols_for_fps].values, num_to_sample=num_to_sample)
            # Reset index to be sure our np indices can index the dataframe.
            diverse = df.reset_index(drop=True).loc[diverse_idx, TILE_INFO]
            diverse["sampler"] = self.name
            diverse["split"] = "test"
            if self.cf["frac_validation_set"] is not None:
                self._set_validation_patches_on_FPS_sampling(diverse)
            diverse = diverse[SELECTION_SCHEMA]
            yield diverse

    def _set_validation_patches_on_FPS_sampling(self, diverse):
        """(Inplace) Set a binary flag for the validation patches, selected by FPS.

        Note: cice property of FPS: using it on its own output starting from the same
        point would yield the same order. So we take the first n points as test_set
        so that they are well distributed.

        # TODO: is this the right way? Risk of setting to val all the most diverse patches?
        """
        diverse["split"] = "train"
        num_samples_val_set = floor(self.cf["frac_validation_set"] * len(diverse))
        diverse.reset_index(drop=True, inplace=True)
        # Reset index to be sure our np indices can index the dataframe.
        # TODO: debug and check if this reset is necessary
        diverse.loc[:num_samples_val_set, ("split",)] = "val"

    def normalize_df(self, df, cols_for_fps):
        """Normalize columns defining the classes histogram, ignoring zeros values

        Ref: https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.QuantileTransformer.html
        """
        # 1/3 Set zeros as NaN to ignore them.
        df = df.replace(to_replace=0, value=np.nan)

        # 2/3 Normalize columns to define a meaningful distance between histogram patches.
        normalization = self.cf["DiversitySampler"]["normalization"]
        if normalization == "standardization":
            df.loc[:, cols_for_fps] = (df.loc[:, cols_for_fps] - df.loc[:, cols_for_fps].mean()) / df.loc[:, cols_for_fps].std()
        else:
            n_quantiles = self.cf["DiversitySampler"]["n_quantiles"]
            qt = QuantileTransformer(n_quantiles=n_quantiles, random_state=0, subsample=100_000)
            df.loc[:, cols_for_fps] = qt.fit_transform(df[cols_for_fps].values)

        # 3/3 Set back zeros where they were.
        df = df.fillna(0)
        return df

    def chunker(self, df, max_chunk_size):
        """Generator for splitting the dataframe."""
        for pos in range(0, len(df), max_chunk_size):
            yield df.iloc[pos : pos + max_chunk_size]
