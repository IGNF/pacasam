from pathlib import Path
import tempfile
from pacasam.analysis.graphs import parser as graphs_parser, main


def test_main_graphs(tiny_synthetic_sampling):
    # Override args so that args of pytest are not seen, to use defaults parameters.
    with tempfile.TemporaryDirectory() as output_path:
        # save synthetic dataset
        sampling_path = Path(output_path) / "synthetic_sampling_for_graphs.gpkg"
        tiny_synthetic_sampling.to_file(sampling_path)

        # Run main
        namespace, _ = graphs_parser.parse_known_args(args="")
        namespace.gpkg_path = sampling_path
        namespace.output_path = Path(output_path)
        main(namespace)
