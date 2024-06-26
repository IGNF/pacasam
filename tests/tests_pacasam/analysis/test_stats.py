from pathlib import Path
import tempfile
from pacasam.analysis.stats import Comparer


def test_Comparer(synthetic_sampling):
    # Override args so that args of pytest are not seen, to use defaults parameters.
    with tempfile.TemporaryDirectory() as tmp_path:
        # Get descriptive statistics by comparing the sampling to itself here.
        comparer = Comparer(output_path=Path(tmp_path))
        comparer.compare(synthetic_sampling, synthetic_sampling)
        assert all(
            (Path(tmp_path) / basename).exists()
            for basename in [
                "comparison-bool_descriptors-by_sampler.csv",
                "comparison-bool_descriptors-by_split.csv",
                "comparison-bool_descriptors.csv",
                "comparison-sizes-by_sampler.csv",
                "comparison-sizes-by_split.csv",
            ]
        )
