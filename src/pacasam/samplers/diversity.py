import numpy as np
from math import floor
from sklearn.preprocessing import QuantileTransformer

from pacasam.samplers.algos import fps
from pacasam.samplers.sampler import SELECTION_SCHEMA, TILE_INFO, Sampler


class DiversitySampler(Sampler):
    def get_tiles(self, num_to_sample: int):
        """A sampling to cover the space of class histogram in order to include the diverse data scenes.
        Class histogram is a proxy for scene content. E.g. highly present building, quasi absent vegetation --> urban scene?
        We need to normalize each count of points to map them to class-specific notions from "absent" to "highly present".
        To do so we use quantiles computed on tiles where the class is present.
        We use a high number of quantiles so that signal is preserved between elements with close values.
        With q=50, we get for 4 classes 50**4 potential bins. Tests show on 100k tiles that most (>99%) are unique, so
        FPS will have the signal it requires to sample.
        # TODO: check the behavior of QuantileTransform : no need fo q=50 if signal remains withing bins.

        NB: Rare classes are already targeted spatially via sequential sampling. Adding them here might give them a high weight...
        but may be done.

        # TODO: make this configurable in the optimization config.
        # Could be done with an API similar to the sequential one, with a num_quantile arg. Each
        # col can be obtained via a sql query (sum included),
        """

        # TODO: extract could be done in a single big sql formula, by chunk.
        # TODO: clean out the comments once this is stable
        extract = self.connector.extract(selection=None)
        # WARNING: Here we put everything in memory
        # TODO: Might not scale with more than 100k tiles ! we need to do this by chunk...
        # Or test with synthetic data, but we would need to create the fields.

        vegetation_columns = ["nb_points_vegetation_basse", "nb_points_vegetation_moyenne", "nb_points_vegetation_haute"]
        # Therefore we do not need to sample them by the amount of points.
        extract["nb_points_vegetation"] = extract[vegetation_columns].sum(axis=1)
        # TODO: get back medium and high vegetation, which are informative !!
        nb_points_cols = [
            "nb_points_sol",
            "nb_points_bati",
            "nb_points_non_classes",
            "nb_points_vegetation",
            # "nb_points_pont",
            # "nb_points_eau",
            # "nb_points_sursol_perenne",
        ]
        extract = extract[TILE_INFO + nb_points_cols]
        # 1/2 Set zeros as NaN to ignore them in the quantile transforms.
        extract = extract.replace(to_replace=0, value=np.nan)
        qt = QuantileTransformer(n_quantiles=50, random_state=0, subsample=100_000)
        # https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.QuantileTransformer.html

        extract.loc[:, nb_points_cols] = qt.fit_transform(extract[nb_points_cols].values)

        # 2/2 Set back zeros where they were.
        extract = extract.fillna(0)

        # Farthest Point Sampling
        # Set indices to a range to be sure that np indices = pandas indices.
        extract = extract.reset_index(drop=True)
        diverse_idx = fps(arr=extract.loc[:, nb_points_cols].values, num_to_sample=num_to_sample)
        diverse = extract.loc[diverse_idx, TILE_INFO]

        # Nice property of FPS: using it on its own output starting from the same
        # point would yield the same order. So we take the first n points as test_set
        # so that they are well distributed.
        num_samples_test_set = floor(self.cf["frac_test_set"] * len(diverse))
        diverse["is_test_set"] = 0
        diverse.loc[diverse.index[:num_samples_test_set], ("is_test_set",)] = 1

        return diverse[SELECTION_SCHEMA]
