from typing import Dict, Optional
import numpy as np
from math import ceil, floor
import pandas as pd
from sklearn.preprocessing import QuantileTransformer
from pacasam.connectors.connector import TILE_INFO

from pacasam.samplers.algos import fps, sample_with_stratification
from pacasam.samplers.diversity import normalize_df
from pacasam.samplers.sampler import SELECTION_SCHEMA, Sampler

import hdbscan


class OutliersSampler(Sampler):
    """
    A class for sampling patches via Clustering

    Methods:
        get_patches(num_diverse_to_sample=1, normalization='standardization', quantile=50):
            Performs a sampling to cover the space of class histogram in order to include the diverse data scenes.

    """

    def get_patches(self, num_to_sample: Optional[int] = None):
        """
        Performs a sampling to cover the space of class histogram in order to include the diverse data scenes.
        Class histogram is a proxy for scene content. E.g. highly present building + quasi absent vegetation = urban scene.
        We use KMmeans.

        See DiversitySampler for more information.

        """

        if num_to_sample is None:
            num_to_sample = self.cf["target_total_num_patches"]

        cols_for_clustering = self.cf["OutliersSampler"]["columns"]

        df = self.connector.db
        df = df[TILE_INFO + cols_for_clustering]
        # Always use the default normalization method : standardization,
        # because it is the only one that gives good outliers.
        df = normalize_df(df=df, columns=self.cf["OutliersSampler"]["columns"])
        df["cluster_id"], df["outlier_scores"] = cluster(
            array=df[cols_for_clustering].values, hdbscan_kwargs=self.cf["OutliersSampler"]["hdbscan_kwargs"]
        )
        # We keep the most "outliers" points i.e. supposedly the most different and informative points.
        df = df.sort_values(by="outlier_scores", ascending=False).head(num_to_sample)

        patches = df[TILE_INFO + ["cluster_id", "outlier_scores"]]
        self._set_validation_patches_with_stratification(patches=patches, keys=["cluster_id", "dalle_id"])
        patches["sampler"] = self.name
        self.log.info(f"{self.name}: N={num_to_sample} patches.")

        # cluster_id et "outlier_scores" can be returned for visual exploration.
        # return patches[SELECTION_SCHEMA + ["cluster_id", "outlier_scores"]]
        return patches[SELECTION_SCHEMA]


def cluster(array: np.ndarray, hdbscan_kwargs: dict):
    # TODO: have own config for lcustering that is not OutliersSampler.
    clusterer = hdbscan.HDBSCAN(
        **hdbscan_kwargs
    )
    clusterer = clusterer.fit(array)
    return clusterer.labels_, clusterer.outlier_scores_