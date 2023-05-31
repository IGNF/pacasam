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
SAMPLING_PATH ?= outputs/samplings/LiPaCConnector-TripleSampler/LiPaCConnector-TripleSampler-train.gpkg  # Chemin vers le sampling à extraire.
SAMPLING_PARTS_DIR ?= /tmp/sampling_parts/  # Où diviser le sampling en n parties, une par fichier de données.
DATASET_ROOT_PATH ?= /var/data/${USER}/pacasam_extractions/laz_dataset/  # Où extraire le jeu de données.
PARALLEL_EXTRACTION_JOBS ?= 75%  # Niveua de parallélisation. Un entier ou un pourcentage des cpu.
SAMBA_CREDENTIALS_PATH ?= "credentials.yml"  # Requis pour données dans un store Samba

help:
	@echo "Makefile"
	@echo "------------------------------------"
	@echo "Cibles pour l'échantillonnage:"
	@echo "  $(SAMPLERS) - Exécute chaque échantillonneur individuellement."
	@echo "  all - Exécute tous les samplers pour un connecteur donné (par défaut: connecteur Lipac)"
	@echo "  all_synthetic - Exécute tous les samplers pour le connecteur synthtéique"
	@echo "Note: L'option 'REPORTS=Y' permet la création d'un rapport HTML à partir du sampling."
	@echo "------------------------------------"
	@echo "Cibles pour l'extraction:"
	@echo "  run_extraction_of_toy_laz_data - Vérifie que tout est OK en extrayant depuis les données LAZ de test."
	@echo "  run_extraction_of_toy_laz_data_in_parallel - Vérifie que tout est OK en extrayant depuis les données LAZ de test de façon parallélisée."
	@echo "  prepare_parallel_extraction - Divise un sampling `SAMPLING_PATH` en n sampling, un par fichier (p.ex. par fichier LAZ), dans `SAMPLING_PARTS_DIR`."
	@echo "  run_extraction_in_parallel - Extrait le jeu de donnée à partir des n sampling. Spécifier `SAMPLING_PARTS_DIR` et `DATASET_ROOT_PATH`"
	@echo Note: la cible `run_extraction_in_parallel` est séparée de `prepare_parallel_extraction`, pour pouvoir poursuivre l'extraction en l'appelant."
	@echo "------------------------------------"
	@echo "Cleaning:"
	@echo "  clean_extractions - Supprime ./outputs/extractions/"
	@echo "  clean_samplings - Supprime ./outputs/samplings/"



.PHONY: help all all_for_all_connectors_with_reports $(SAMPLERS) tests tests_no_geoportail_no_slow open_coverage_report 
.PHONY: run_extraction_of_toy_laz_data run_extraction_of_toy_laz_data_in_parallel prepare_parallel_extraction run_extraction_in_parallel
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

# By default: run all sampling from Lipac database.
all: $(SAMPLERS)

all_synthetic:
	make all CONNECTOR=SyntheticConnector CONFIG=configs/Synthetic.yml


# EXTRACTION

run_extraction_of_toy_laz_data:
	python ./src/pacasam/run_extraction.py \
		--sampling_path ./tests/data/lefty_righty_sampling.gpkg \
		--dataset_root_path ./outputs/extractions/toy_laz_dataset/

run_extraction_of_toy_laz_data_in_parallel:
	make prepare_parallel_extraction \
		SAMPLING_PATH=./tests/data/lefty_righty_sampling.gpkg \
		SAMPLING_PARTS_DIR="/tmp/sampling_parts_toy_dataset/"
	
	make run_extraction_in_parallel \
		SAMPLING_PARTS_DIR="/tmp/sampling_parts_toy_dataset/" \
		DATASET_ROOT_PATH=./outputs/extractions/toy_laz_dataset/ \
		PARALLEL_EXTRACTION_JOBS=2 \
		SAMBA_CREDENTIALS_PATH='""'

prepare_parallel_extraction:
	# Split sampling into n parts, one for each distinct LAZ file.
	python ./src/pacasam/prepare_parallel_extraction.py \
		--sampling_path="${SAMPLING_PATH}" \
		--sampling_parts_dir="${SAMPLING_PARTS_DIR}"

run_extraction_in_parallel:
	# Run extraction in a parallel fashion based on the listing.
	# Single part sampling are removed upon completion of extraction.
	# We can resume extraction without changing the command.
	# Note: another way could be to use option --resume, and we would need to use --joblog beforehand.
	# Note: Need to simple quote the SAMBA_CREDENTIALS_PATH variable to explicitly give an empty string when etxracting toy_dataset.
	# Note: we need to double quote the whole command, including deletion, so that they happen together.
	ls -1 -d ${SAMPLING_PARTS_DIR}/* | \
		parallel --jobs ${PARALLEL_EXTRACTION_JOBS} --keep-order --progress --verbose --eta \
			"python ./src/pacasam/run_extraction.py \
			--sampling_path {} \
			--dataset_root_path ${DATASET_ROOT_PATH} \
			--samba_credentials_path '${SAMBA_CREDENTIALS_PATH}' \
			&& rm {}"


# CLEANING
clean_samplings:
	rm -r ./outputs/samplings/

clean_extractions:
	rm -r ./outputs/extractions/