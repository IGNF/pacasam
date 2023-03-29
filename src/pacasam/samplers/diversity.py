import numpy as np
from math import ceil, floor
from sklearn.preprocessing import QuantileTransformer

from pacasam.samplers.algos import fps
from pacasam.samplers.sampler import SELECTION_SCHEMA, TILE_INFO, Sampler


class DiversitySampler(Sampler):
    """
    A class for sampling patches via Farthest Point Sampling (FPS).

    Attributes:
        data (np.ndarray): A 2D numpy array representing the point cloud data.
        classes (np.ndarray): A 1D numpy array representing the class labels for each point.

    Methods:
        get_tiles(num_diverse_to_sample=1, normalization='standardization', quantile=50):
            Performs a sampling to cover the space of class histogram in order to include the diverse data scenes.

    """

    def get_tiles(self, num_diverse_to_sample=None):
        """
        Performs a sampling to cover the space of class histogram in order to include the diverse data scenes.
        Class histogram is a proxy for scene content. E.g. highly present building + quasi absent vegetation = urban scene.
        We use Farthest Point Sampling (FPS) as a way to cover the space evenly.

        Parameters:
            num_diverse_to_sample (int): The number of point clouds to sample. Defaults to 1.

        Parameters from configuration (under `DiversitySampler`):
            normalization (str): The type of normalization to apply to the class histograms. Must be either 'standardization'
                or 'quantilization'. Defaults to 'standardization'.
            n_quantiles (int): The number of quantiles to use when applying the 'quantilization' normalization. Ignored
                if normalization is set to 'standardization'. Defaults to 50.
            targets (List[str]): The columns considered for patch-to-patch distance in FPS.
            max_chunk_size_for_fps (int): max num of (consecutive) patches to process by FPS. Lower chunks means that we look for diversity in
            smaller sets of points, thus yielding les diverse points. In particular, lower chunks tend to exclude more rural areas since
            the most diverse histograms arer primarly found in anthropogenic areas.

        Returns:
            A list of length `num_diverse_to_sample` containing the indices of the sampled points.

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
            num_diverse_to_sample = self.cf["num_tiles_in_sampled_dataset"]
        cols_for_fps = self.cf["DiversitySampler"]["columns"]

        df = self.connector.extract(selection=None)
        df = df[TILE_INFO + cols_for_fps]
        # 1/2 Set zeros as NaN to ignore them in the quantile transforms.
        df = df.replace(to_replace=0, value=np.nan)

        normalization = self.cf["DiversitySampler"]["normalization"]
        if normalization == "standardization":
            df.loc[:, cols_for_fps] = (df.loc[:, cols_for_fps] - df.loc[:, cols_for_fps].mean()) / df.loc[:, cols_for_fps].std()
        else:
            n_quantiles = self.cf["DiversitySampler"]["n_quantiles"]
            # https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.QuantileTransformer.html
            qt = QuantileTransformer(n_quantiles=n_quantiles, random_state=0, subsample=100_000)
            df.loc[:, cols_for_fps] = qt.fit_transform(df[cols_for_fps].values)

        # 2/2 Set back zeros where they were.
        df = df.fillna(0)

        # Farthest Point Sampling
        # Nice property of FPS: using it on its own output starting from the same
        # point would yield the same order. So we take the first n points as test_set
        # so that they are well distributed.

        # Set indices to a range to be sure that np indices = pandas indices.
        df = df.reset_index(drop=True)
        max_chunk_size = self.cf["DiversitySampler"]["max_chunk_size_for_fps"]
        # Using
        if len(df) > max_chunk_size:
            proportion_to_sample = num_diverse_to_sample / len(df)

            diverse_idx = []
            test_set_idx = []
            for chunk in self.chunker(df, max_chunk_size):
                # select in chunk with FPS
                num_diverse_to_sample_in_chunk = ceil(len(chunk) * proportion_to_sample)
                idx_in_chunk = fps(arr=chunk.loc[:, cols_for_fps].values, num_to_sample=num_diverse_to_sample_in_chunk)
                idx_in_df = chunk.index[idx_in_chunk].values

                # add to lists
                diverse_idx += [idx_in_df]
                num_samples_test_set_in_chunk = floor(self.cf["frac_test_set"] * num_diverse_to_sample_in_chunk)
                test_set_idx += [idx_in_df[:num_samples_test_set_in_chunk]]

            # concatenate
            diverse_idx = np.concatenate(diverse_idx)
            test_set_idx = np.concatenate(test_set_idx)
            # Warning: Use of loc is only possible because we reset the index earlier.
            diverse = df.loc[diverse_idx, TILE_INFO]
        else:
            diverse_idx = fps(arr=df.loc[:, cols_for_fps].values, num_to_sample=num_diverse_to_sample)
            diverse = df.loc[diverse_idx, TILE_INFO]

            num_samples_test_set = floor(self.cf["frac_test_set"] * len(diverse))
            test_set_idx = diverse.index[:num_samples_test_set]

        diverse["split"] = "train"
        diverse.loc[test_set_idx, ("split",)] = "test"

        diverse["sampler"] = self.name
        return diverse[SELECTION_SCHEMA]

    def chunker(self, df, max_chunk_size):
        """Generator for splitting the dataframe."""
        for pos in range(0, len(df), max_chunk_size):
            yield df.iloc[pos : pos + max_chunk_size]
