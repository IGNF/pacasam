# /!\ Environnement pacasam à activer avec: conda activate pacasam

# Dans ce Makefile, la variable SAMPLERS contient les noms des quatre échantillonneurs disponibles. 
# La cible all dépend de toutes les cibles définies dans $(SAMPLERS). 
# Une règle générique permet d'exécuter chaque échantillonneur en utilisant la variable $@ qui contient le nom de la cible actuelle.

# Exécutez toutes les tâches en une seule fois en utilisant la commande:
# 	make all.
# Exécutez une tâche spécifique en utilisant le nom de la tâche en tant que cible: make RandomSampler, make SpatialSampler, etc.
# Exécutez sur le jeu de données synthtéiques avec 
#	make all CONNECTOR=SyntheticConnector CONFIG=configs/Synthetic.yml

# Paramètres pour l'échantillonnage
CONNECTOR ?= LiPaCConnector  # LiPaCConnector ou SyntheticConnector
CONFIG ?= configs/Lipac.yml  # configs/Lipac.yml ou configs/Synthetic.yml - Devrait correspondre au connecteur!
REPORTS ?= N # N(o) ou Y(es). No pour des résultats plus rapides.
SAMPLERS = RandomSampler SpatialSampler TargettedSampler DiversitySampler TripleSampler OutliersSampler

# Paramètres pour l'extraction
SAMPLING_PATH ?= outputs/samplings/LiPaCConnector-TripleSampler/LiPaCConnector-TripleSampler-train.gpkg
SAMPLING_PARTS_DIR ?= /tmp/sampling_parts/
DATASET_ROOT_PATH ?= /var/data/${USER}/pacasam_extractions/laz_dataset/
PARALLEL_EXTRACTION_JOBS ?= 75%  # Un entier ou un pourcentage des cpu.

# TODO: describe the new extraction commands.
help:
	@echo "Makefile"
	@echo "------------------------------------"
	@echo "Cibles pour l'échantillonnage:"
	@echo "  $(SAMPLERS) - Exécute chaque échantillonneur individuellement."
	@echo "  all - Exécute tous les samplers pour un connecteur donné (par défaut: connecteur Lipac)"
	@echo "  all CONNECTOR=SyntheticConnector CONFIG=configs/Synthetic.yml - pour passer le connectuer Synthetic"
	@echo "  all_for_all_connectors - 'Make all' pour les deux connecteurs (Lipac et Synthetic)."
	@echo "Note: L'option 'REPORTS=Y' permet la création d'un rapport HTML à partir du sampling."
	@echo "------------------------------------"
	@echo "Cibles pour l'extraction:"
	@echo "  extraction_of_toy_laz_data - Lance une extraction d'un jeu de données laz depuis les données laz de test."
	@echo "  prepare_parallel_extraction - Divise un sampling `SAMPLING_PATH` en n sampling, un par fichier (p.ex. par fichier LAZ), dans `SAMPLING_PARTS_DIR`."
	@echo "  parallel_extraction_of_laz_dataset - Extrait le jeu de donnée à partir des n sampling. Spécifier `SAMPLING_PARTS_DIR` et `DATASET_ROOT_PATH`"
	@echo "------------------------------------"
	@echo "Cleaning:"
	@echo "  clean_extractions - Supprime ./outputs/extractions/"
	@echo "  clean_samplings - Supprime ./outputs/samplings/"



.PHONY: help all all_for_all_connectors $(SAMPLERS) tests tests_no_geoportail_no_slow open_coverage_report 
.PHONY: extraction_of_toy_laz_data prepare_parallel_extraction parallel_extraction_of_laz_dataset
.PHONY: clean_samplings clean_extractions


# TESTS
tests:
	# Run pytest parallelization with at most 6 processes.
	# See https://pytest-xdist.readthedocs.io/en/stable/distribution.html#running-tests-across-multiple-cpus
	# Also, `-s` to show stout is not supported in pytest-xdist - remove paralellization for more logs.
	# See https://pytest-xdist.readthedocs.io/en/stable/known-limitations.html#output-stdout-and-stderr-from-workers
	pytest -s -n auto --dist worksteal --maxprocesses=6

tests_no_geoportail_no_slow:
	# Same, but without test marked with the geoportail marker.
	pytest -s -n auto --dist worksteal --maxprocesses=6 -m "not geoportail and not slow"

open_coverage_report:
	firefox htmlcov/index.html

# SAMPLING

$(SAMPLERS):
	python ./src/pacasam/run_sampling.py --config_file=$(CONFIG) \
		--connector_class=$(CONNECTOR) \
		--sampler_class=$@ \
		--make_html_report=$(REPORTS)

all: $(SAMPLERS)

all_for_all_connectors:
	make all REPORTS=Y
	make all REPORTS=Y CONNECTOR=SyntheticConnector CONFIG=configs/Synthetic.yml


# EXTRACTION
extraction_of_toy_laz_data:
	python ./src/pacasam/run_extraction.py \
		--sampling_path ./tests/data/lefty_righty_sampling.gpkg \
		--dataset_root_path ./outputs/extractions/toy_laz_dataset/

prepare_parallel_extraction:
	# Split sampling into n parts, one for each distinct LAZ file.
	python ./src/pacasam/prepare_parallel_extraction.py \
		--sampling_path="${SAMPLING_PATH}" \
		--sampling_parts_dir="${SAMPLING_PARTS_DIR}"

parallel_extraction_of_laz_dataset:
	# Run extraction in a parallel fashion based on the listing.
	# Single part sampling are removed upon completion of extraction.
	# We can resume extraction without changing the command.
	# Note: another way could be to use option --resume, and we would need to use --joblog beforehand.
	ls -1 -d ${SAMPLING_PARTS_DIR}/* | \
		parallel --jobs ${PARALLEL_EXTRACTION_JOBS} --keep-order --progress --verbose --eta \
			python ./src/pacasam/run_extraction.py \
			--sampling_path {} \
			--dataset_root_path ${DATASET_ROOT_PATH} \
			&& rm {}


# CLEANING
clean_samplings:
	rm -r ./outputs/samplings/

clean_extractions:
	rm -r ./outputs/extractions/