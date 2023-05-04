from pathlib import Path
import tempfile
from pacasam.analysis.graphs import parser as graphs_parser, main
import pytest


@pytest.mark.xfail(reason="Test not implemented yet")
def test_main_graphs():
    namespace, _ = graphs_parser.parse_known_args(args="")  # use defaut parameters only
    # TODO: use a fixture that makes a synthetic sampling. It is also used in test_check_sampling_format_based_on_synthetic_data so it can be a fixture.
    # Here we need all the columns to simply test this.
    namespace.gpkg_path = Path(...)
    with tempfile.TemporaryDirectory() as output_path:
        namespace.output_path = Path(output_path)
        main(namespace)
