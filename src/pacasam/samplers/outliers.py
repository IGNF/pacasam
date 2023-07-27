from typing import Optional
import numpy as np
from pacasam.connectors.connector import FILE_ID_COLNAME, PATCH_INFO

from pacasam.samplers.diversity import normalize_df
from pacasam.samplers.sampler import Sampler

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
        df = df[PATCH_INFO + cols_for_clustering]
        # Always use the default normalization method : standardization,
        # because it is the only one that gives good outliers.
        df = normalize_df(df=df, columns=self.cf["OutliersSampler"]["columns"])

        df["cluster_id"], df["outlier_scores"] = cluster(
            array=df[cols_for_clustering].values, hdbscan_kwargs=self.cf["OutliersSampler"]["hdbscan_kwargs"]
        )
        # We keep the most "outliers" points i.e. supposedly the most different and informative points.
        df = df.sort_values(by="outlier_scores", ascending=False).head(num_to_sample)

        patches = df[PATCH_INFO + ["cluster_id", "outlier_scores"]]
        patches["sampler"] = self.name
        self._set_validation_patches_with_stratification(patches=patches, keys=["cluster_id", FILE_ID_COLNAME])
        self.log.info(f"{self.name}: N={min(num_to_sample, len(patches))}/{num_to_sample} patches.")

        # UNCOMMENT FOR DEBUG: cluster_id et "outlier_scores" can be returned for visual exploration.
        # return patches[self.sampling_schema + ["cluster_id", "outlier_scores"]]
        return patches[self.sampling_schema]


def cluster(array: np.ndarray, hdbscan_kwargs: dict):
    clusterer = hdbscan.HDBSCAN(**hdbscan_kwargs)
    clusterer = clusterer.fit(array)
    return clusterer.labels_, clusterer.outlier_scores_
