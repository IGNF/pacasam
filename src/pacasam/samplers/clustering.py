from typing import Dict
import numpy as np
from math import ceil, floor
import pandas as pd
from sklearn.preprocessing import QuantileTransformer
from pacasam.connectors.connector import TILE_INFO

from pacasam.samplers.algos import fps, sample_with_stratification
from pacasam.samplers.diversity import normalize_df
from pacasam.samplers.sampler import SELECTION_SCHEMA, Sampler

import hdbscan


class ClusteringSampler(Sampler):
    """
    A class for sampling patches via Clustering

    Methods:
        get_patches(num_diverse_to_sample=1, normalization='standardization', quantile=50):
            Performs a sampling to cover the space of class histogram in order to include the diverse data scenes.

    """

    def get_patches(self, num_diverse_to_sample=None):
        """
        Performs a sampling to cover the space of class histogram in order to include the diverse data scenes.
        Class histogram is a proxy for scene content. E.g. highly present building + quasi absent vegetation = urban scene.
        We use KMmeans.

        See DiversitySampler for more information.

        """

        if num_diverse_to_sample is None:
            num_diverse_to_sample = self.cf["target_total_num_patches"]

        cols_for_clustering = self.cf["DiversitySampler"]["columns"]

        df = self.connector.db
        df = df[TILE_INFO + cols_for_clustering]
        df = normalize_df(df=df, normalization_config=self.cf["DiversitySampler"])
        MIN_CLUSTER_SIZE = 20
        n_clusters = num_diverse_to_sample / MIN_CLUSTER_SIZE
        df["cluster_id"] = cluster(
            array=df[cols_for_clustering].values, normalization_config=self.cf["DiversitySampler"], n_clusters=int(n_clusters)
        )

        df = df[TILE_INFO + ["cluster_id"]]  # get lighter

        patches = sample_with_stratification(patches=df, num_to_sample=num_diverse_to_sample, keys="cluster_id")
        self._set_validation_patches_with_stratification(patches=patches, keys=["cluster_id"])
        patches["sampler"] = self.name
        # TODO: add some log
        return patches[SELECTION_SCHEMA]


def cluster(array: np.ndarray, normalization_config: dict, n_clusters: int):
    # normalization_config not used but could contain args for clustering.
    # https://hdbscan.readthedocs.io/en/latest/parameter_selection.html#leaf-clustering"
    # cluster_selection_method = "leaf" so we do not create ultra large clusters but rather smaller ones
    # that cover the space.
    # to have more small clusters.
    # low min_samples -> less points ignored as noise.
    # Try out flat clustering based on DBSCAN
    # https://stackoverflow.com/a/68763150/8086033
    # https://github.com/scikit-learn-contrib/hdbscan/blob/master/notebooks/Flat%20clustering.ipynb

    clusterer = hdbscan.HDBSCAN(min_cluster_size=10, min_samples=10, cluster_selection_method="leaf")
    clusterer = clusterer.fit(array)
    from hdbscan import flat

    clusterer = flat.HDBSCAN_flat(array, clusterer=clusterer, n_clusters=n_clusters)
    # Then we can sample both in the representative regions and in the outer regions.    # curently we simply keep the noise as a cluster. Its impacyt will be low since we sample with stratification.
    return clusterer.labels_
