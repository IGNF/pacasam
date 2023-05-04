from pathlib import Path
from pacasam.extractors.laz import LAZ_FILE_COLNAME, all_files_can_be_accessed, check_sampling_format
from pacasam.utils import CONNECTORS_LIBRARY

LEFTY = Path("tests/data/792000_6272000-50mx100m-left.las")
RIGHTY = Path("tests/data/792000_6272000-50mx100m-right.las")


def test_check_files_accessibility():
    # Test when all files exist - we test this with this module's own path.
    file_paths = [LEFTY, RIGHTY]
    assert all_files_can_be_accessed(file_paths)

    # Test when some files do not exist
    file_paths = [LEFTY, Path("non_existing_file.txt"), RIGHTY]
    assert not all_files_can_be_accessed(file_paths)


def test_check_sampling_format_based_on_synthetic_data():
    # Small synthetic data in db
    connector_class = CONNECTORS_LIBRARY.get("SyntheticConnector")
    connector = connector_class(log=None, binary_descriptors_prevalence=[0.1], db_size=10)
    df = connector.db
    df["split"] = "train"
    # TODO: replace with the path to an actual LAZ file
    df[LAZ_FILE_COLNAME] = __file__
    check_sampling_format(df)
