# import pytest
from pacasam.prepare_parallel_extraction import get_stem_from_any_file_format


def test_get_stem_from_any_file_format_unix():
    file_path = "/path/to/file.txt"
    expected_stem = "file"
    result = get_stem_from_any_file_format(file_path)
    assert result == expected_stem


def test_get_stem_from_any_file_format_samba():
    file_path = r"\\store.ign.fr\store-lidarhd\file.laz"
    expected_stem = "file"
    result = get_stem_from_any_file_format(file_path)
    assert result == expected_stem
