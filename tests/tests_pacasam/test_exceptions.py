import numpy as np
import pandas as pd
import pytest
from pacasam.exceptions import UnexpectedNaNValuesError


def test_UnexpectedNaNValuesError_with_bad_df():
    df = pd.DataFrame(data=[[0, 0], [np.nan, 0]], columns=["good_without_nan", "bad_with_nan"])
    with pytest.raises(UnexpectedNaNValuesError):
        raise UnexpectedNaNValuesError(df)
