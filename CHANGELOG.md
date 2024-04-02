# PACASAM - CHANGELOG

# 1.1.0
- `TargettedSampler` is completed by `SpatialSampler` to reach target num of patches and target validation proportion.

# 1.0.0
- `LAZExtractor` supports colorization via sources files (rgb_file + irc_file) in addition to the Géoplateforme WMS.

## 0.13.0
- Update ign-pdal-tools to V1.5 to remove the conflict between 'mpire' and 'subprocess' when coloring point clouds.
- Remove all mentions of geopackage splitting for file-level parallelism, to prefer MPIRE parallelism.

## 0.12.0
- `BDOrthoVintageExtractor`: does not assume the use of VRT but instead relies on specified rgb_file and irc_file

### 0.11.3
- LAZ patches now have format `{SPLIT}-{patch_id}.laz`, ignoring file_id, for coherence with imagery extractors.
- fix: Rewrite LiPaC's convert_samba_path_to_mounted_path due to inexplicable regression of the method.

### 0.11.2
- Do not set crs of LiPaC since n>1 distinct SRIDs might be used in the future.

### 0.11.1
- Get rid of VS Code configurations.

### 0.11.0
- Get rid of complex smbprotocol in favor of a store-lidarhd always mounted under /mnt/ for Lipac data.

### 0.10.3
- fix: Use shutil.copy instead of shutil.move to avoid invalid cross-device link error.

### 0.10.2
- Log the pacasam version and the git commit SHA when doing a sampling or an extraction.

### 0.10.1
- Add tests for run_sampling with LipacConnector, to run locally.

## 0.10.0
- `OrthoimageExtractor` becomes `BDOrthoTodayExtractor`
- New `BDOrthoTodayVintageExtractor` relying on a folder with `irc`/`rvb` subdirs of VRTs of BD ORtho vintages.
- Implement parallelization for all extractors via the num_jobs argument.
- Enable resuming an extraction by checking beforehand if a patch was already extracted, and by having only atomic extractions.
- fix: Have a tiny_synthetic_sampling fixture intact as input for all tests (scope=test).

### 0.9.4
- Refactor: move all laz-specific logics (e.g. use of file_path) to the right places. 

### 0.9.3
- Rename extractor: `orthoimages` to `bd_ortho_today.`

### 0.9.2
- Drop duplicates patches by patch_id right after download to anticipate potential duplicates in Lipac.

### 0.9.1
- Update ign-pdal-tools version dependency to avoid cluttered /tmp/ folder.

## 0.9.0
- Implement the `BDOrthoTodayExtractor`

## 0.8.0
- Keep only patches that are in France using the new LiPaC attribute VIGNETTE.EN_FRANCE

### 0.7.2
- Drop unused graphs.py and remove all reference to it

### 0.7.1
- Stats: save comparison-bool_descriptors.csv with its index

## 0.7.0
- Refactor SQL using Common-Term-Expression for better maintainability

## 0.6.0
- Parallelization of test_prepare_parallel_extraction.py using MPIRE

### 0.5.3
- EPSG:0 is now interpreted as an unknown SRID in LAZ files, and the SRID is taken from the LAZ file direcly.

### 0.5.2
- Corrected split value (test and not train/val) when frac_validation_set=0.0

### 0.5.1
- Ignore empty patches (num_nodes=0) when requesting Lipac.

## 0.5.0
- Semantic Versionning in _python.py file
- `CHANGELOG.md`
