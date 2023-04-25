from pathlib import Path
import pandas as pd


class Comparer:
    """Compare two pandas dataframes using boolean descriptors.
    
    We use a class for possible extension of capabilities.
    """

    def __init__(self):
        ...

    def compare(self, df_database: pd.DataFrame, df_sampling: pd.DataFrame):
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
        comparison_df["ratio"] = (comparison_df["df_sampling"] / comparison_df["df_database"]).round(decimals=2)
        return comparison_df
