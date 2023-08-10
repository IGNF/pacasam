from pathlib import Path
import tempfile
from pacasam.analysis.graphs import parser as graphs_parser, main as main_graphs
from pacasam.analysis.stats import Comparer


def test_Comparer(tiny_synthetic_sampling):
    # Override args so that args of pytest are not seen, to use defaults parameters.
    with tempfile.TemporaryDirectory() as tmp_path:
        # Get descriptive statistics by comparing the sampling to itself here.
        comparer = Comparer(output_path=Path(tmp_path) / "stats")
        comparer.compare(tiny_synthetic_sampling, tiny_synthetic_sampling)
