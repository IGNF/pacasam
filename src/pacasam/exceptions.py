
from pandas import DataFrame


class UnexpectedNaNValuesError(Exception):
    """In case the df data contains NaN values, raise this informative exception."""

    def __init__(self, df: DataFrame):
        cols_with_nan = df.columns[df.isna().sum() > 0]
        super().__init__(f"Unexpected NaN Values encountered in cols: {', '.join(cols_with_nan)}")