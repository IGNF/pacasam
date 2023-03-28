import numpy as np
from math import floor
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

        # TODO: extract could be done in a single big sql formula, by chunk.
        # TODO: clean out the comments once this is stable
        # WARNING: Here we put everything in memory
        # TODO: Might not scale with more than 100k tiles ! we need to do this by chunk...
        # Or test with synthetic data, but we would need to create the fields.

        extract = self.connector.extract(selection=None)
        extract = extract[TILE_INFO + cols_for_fps]
        # 1/2 Set zeros as NaN to ignore them in the quantile transforms.
        extract = extract.replace(to_replace=0, value=np.nan)

        normalization = self.cf["DiversitySampler"]["normalization"]
        if normalization == "standardization":
            extract.loc[:, cols_for_fps] = (extract.loc[:, cols_for_fps] - extract.loc[:, cols_for_fps].mean()) / extract.loc[
                :, cols_for_fps
            ].std()
        else:
            n_quantiles = self.cf["DiversitySampler"]["n_quantiles"]
            # https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.QuantileTransformer.html
            qt = QuantileTransformer(n_quantiles=n_quantiles, random_state=0, subsample=100_000)
            extract.loc[:, cols_for_fps] = qt.fit_transform(extract[cols_for_fps].values)

        # 2/2 Set back zeros where they were.
        extract = extract.fillna(0)

        # Farthest Point Sampling
        # Set indices to a range to be sure that np indices = pandas indices.
        extract = extract.reset_index(drop=True)
        diverse_idx = fps(arr=extract.loc[:, cols_for_fps].values, num_to_sample=num_diverse_to_sample)
        diverse = extract.loc[diverse_idx, TILE_INFO]

        # Nice property of FPS: using it on its own output starting from the same
        # point would yield the same order. So we take the first n points as test_set
        # so that they are well distributed.
        num_samples_test_set = floor(self.cf["frac_test_set"] * len(diverse))
        diverse["split"] = "train"
        diverse.loc[diverse.index[:num_samples_test_set], ("split",)] = "test"

        diverse["sampler"] = self.name
        return diverse[SELECTION_SCHEMA]
