from pathlib import Path
import pandas as pd

SURFACE_OF_A_KM2 = 1000 * 1000


class Comparer:
    """Compare two pandas dataframes using boolean descriptors.

    We use a class for possible extension of capabilities. We could also use n different "compare" methods,
    all with same signature (df_database, df_sampling), called sequentially to make different stats.
    Could be added in an excel file.

    """

    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.output_path.mkdir(parents=True, exist_ok=True)

    def compare(self, df_database: pd.DataFrame, df_sampling: pd.DataFrame):
        # Compare prevalence of all boolean descriptors.
        output_csv = self.output_path / "comparison-bool_descriptors.csv"
        comparison_df = self.compare_bools(df_database, df_sampling)
        comparison_df.to_csv(output_csv, index=False)

        # Prepare to compare areas and couts of patches.
        for df in [df_database, df_sampling]:
            df["area_km2"] = df.area / SURFACE_OF_A_KM2
            df["num_patches"] = 1
        comparison_df = self.compare_sizes(df_database, df_sampling)
        output_csv = self.output_path / "comparison-areas.csv"

        # With some stratification
        for key in ["sampler", "split"]:
            if df_sampling[key].nunique() == 1:
                continue
            # Compare prevalence of all boolean descriptors.
            comparison_df_by_key = self.compare_by_key(df_database, df_sampling, key, self.compare_bools)
            output_csv = self.output_path / f"comparison-bool_descriptors-by_{key}.csv"
            comparison_df_by_key.to_csv(output_csv)

            # Compara areas
            comparison_df_by_key = self.compare_by_key(df_database, df_sampling, key, self.compare_sizes)
            output_csv = self.output_path / f"comparison-sizes-by_{key}.csv"
            comparison_df_by_key.to_csv(output_csv)

    def compare_bools(self, df_database: pd.DataFrame, df_sampling: pd.DataFrame):
        """Compares the prevalence of boolean descriptors in two pandas dataframes.

        Args:
            df_database (pandas.DataFrame): The database (e.g. LiPaC)
            df_sampling (pandas.DataFrame): The sampling to be compared to the database.

        Returns:
            pandas.DataFrame: A dataframe with prevalence values for each boolean descriptor in each input dataframe,
            as well as the ratio of prevalence between the two dataframes.

        """
        # Generate list of boolean descriptor names present in the base dataframe
        boolean_descriptors_names = df_database.select_dtypes(include=bool).columns

        # Calculate prevalence (proportion) of each boolean descriptor for each dataframe
        prevalence_base = pd.DataFrame(df_database[boolean_descriptors_names].mean(), columns=["df_database"])
        prevalence_sampling = pd.DataFrame(df_sampling[boolean_descriptors_names].mean(), columns=["df_sampling"])

        # Concatenate prevalence dataframes horizontally to create comparison dataframe
        comparison_df = pd.concat([prevalence_base, prevalence_sampling], axis=1)
        # comparison_df = comparison_df.reset_index(names=["descriptor_name"])
        comparison_df["ratio"] = (comparison_df["df_sampling"] / comparison_df["df_database"]).round(decimals=2)
        return comparison_df

    def compare_sizes(self, df_database: pd.DataFrame, df_sampling: pd.DataFrame):
        sizes_base = pd.DataFrame(df_database[["area_km2", "num_patches"]].sum(), columns=["df_database"])
        sizes_sampling = pd.DataFrame(df_sampling[["area_km2", "num_patches"]].sum(), columns=["df_sampling"])
        comparison_df = pd.concat([sizes_base, sizes_sampling], axis=1)
        comparison_df["ratio"] = (comparison_df["df_sampling"] / comparison_df["df_database"]).round(decimals=2)
        return comparison_df

    def compare_by_key(self, df_database, df_sampling, key, method):
        """Use a mehode (e.g. compare_bools) with a groupby(key) to compare different subsets of the sampling."""
        dfs = []
        for key_value, df_subset in df_sampling.groupby(key):
            comparison_df_sampler = method(df_database, df_subset)
            comparison_df_sampler.insert(0, key, key_value)
            dfs += [comparison_df_sampler]
        comparison_df_by_sampler = pd.concat(dfs, ignore_index=False)
        comparison_df_by_sampler = comparison_df_by_sampler.set_index(
            [comparison_df_by_sampler.index.rename("descriptor"), key]
        ).sort_index()
        return comparison_df_by_sampler
