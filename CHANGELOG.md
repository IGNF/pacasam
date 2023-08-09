# dev

# 0.7.0
- Refactor SQL using Common-Term-Expression for better maintanability

# 0.6.0
- Parallelization of test_prepare_parallel_extraction.py using MPIRE

# 0.5.3
- EPSG:0 is now interpreted as an unknown SRID in LAZ files, and the SRID is taken from the LAZ file direcly.

# 0.5.2
- Corrected split value (test and not train/val) when frac_validation_set=0.0

# 0.5.1
- Ignore empty patches (num_nodes=0) when requesting Lipac.

# 0.5.0
- Semantic Versionning in _python.py file
- CHANGELOG.md