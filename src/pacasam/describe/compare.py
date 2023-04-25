from pathlib import Path
import pandas as pd


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
        output_csv = self.output_path / "comparison-bool_descriptors.csv"
        comparison_df = self.compare_bools(df_database, df_sampling)
        comparison_df.to_csv(output_csv, index=False)

        # With some stratification
        for key in ["sampler", "split"]:
            if df_sampling[key].nunique() == 1:
                continue
            comparison_df_by_sampler = self.compare_bools_by_key(df_database, df_sampling, key)
            output_csv = self.output_path / f"comparison-bool_descriptors-by_{key}.csv"
            comparison_df_by_sampler.to_csv(output_csv)

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
        comparison_df = comparison_df.reset_index(names=["descriptor_name"])
        # comparison_df = comparison_df.reset_index(names=["descriptor_index"])
        comparison_df["ratio"] = (comparison_df["df_sampling"] / comparison_df["df_database"]).round(decimals=2)
        return comparison_df

    def compare_bools_by_key(self, df_database, df_sampling, key):
        """Like compare_bools but with a groupby(key) to compare different subsets of the sampling."""
        dfs = []
        for sampler, df_subset in df_sampling.groupby(key):
            comparison_df_sampler = self.compare_bools(df_database, df_subset)
            comparison_df_sampler.insert(0, key, sampler)
            dfs += [comparison_df_sampler]
        comparison_df_by_sampler = pd.concat(dfs, ignore_index=False)
        comparison_df_by_sampler = comparison_df_by_sampler.set_index(["descriptor_name", key]).sort_index()
        return comparison_df_by_sampler
