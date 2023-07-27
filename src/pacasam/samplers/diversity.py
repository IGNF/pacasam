from typing import List
from math import ceil
import pandas as pd

from pacasam.connectors.connector import FILE_ID_COLNAME, PATCH_ID_COLNAME, PATCH_INFO
from pacasam.samplers.algos import fps, normalize_df, yield_chunks
from pacasam.samplers.sampler import Sampler


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
        db = db.sort_values(by=[FILE_ID_COLNAME, PATCH_ID_COLNAME])
        db = db[PATCH_INFO + cols_for_fps]
        db = normalize_df(
            df=db,
            columns=cols_for_fps,
            normalization=self.cf["DiversitySampler"]["normalization"],
            n_quantiles=self.cf["DiversitySampler"]["n_quantiles"],
        )

        # Farthest Point Sampling
        patches = list(self._get_patches_via_fps(db, num_to_sample, cols_for_fps))
        patches = pd.concat(patches, ignore_index=True)
        # ceil(...) might give a tiny amount of patches in excess
        patches = patches.iloc[:num_to_sample]
        self.log.info(f"{self.name}: N={min(num_to_sample, len(patches))}/{num_to_sample} patches.")
        return patches

    def _get_patches_via_fps(self, df: pd.DataFrame, num_to_sample: int, cols_for_fps: List[str]):
        max_chunk_size = self.cf["DiversitySampler"]["max_chunk_size_for_fps"]
        if len(df) > max_chunk_size:
            target_proportion = num_to_sample / len(df)
            for chunk in yield_chunks(df, max_chunk_size):
                num_to_sample_in_chunk = ceil(len(chunk) * target_proportion)
                yield from self._get_patches_via_fps(chunk, num_to_sample=num_to_sample_in_chunk, cols_for_fps=cols_for_fps)
        else:
            # We can't sample more that there is in df, but we still use fps to order the points nicely
            if num_to_sample > len(df):
                num_to_sample = len(df)
            diverse_idx = fps(arr=df[cols_for_fps].values, num_to_sample=num_to_sample)
            # Reset index to be sure our np indices can index the dataframe.
            diverse = df.reset_index(drop=True).loc[diverse_idx, PATCH_INFO]
            diverse["sampler"] = self.name
            diverse = self._set_validation_patches_with_stratification(patches=diverse, keys=FILE_ID_COLNAME)
            diverse = diverse[self.sampling_schema]
            yield diverse
