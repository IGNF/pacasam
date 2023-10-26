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
# CopySampler géré séparemment pour éviter copie lourde de LiPaC.
SAMPLERS = RandomSampler SpatialSampler TargettedSampler DiversitySampler TripleSampler OutliersSampler

# Paramètres pour l'extraction
SAMPLING_PATH ?= outputs/samplings/LiPaCConnector-TripleSampler/LiPaCConnector-TripleSampler-train.gpkg  # Chemin vers le sampling à extraire.
SAMPLING_PARTS_DIR ?= /tmp/sampling_parts/  # Où diviser le sampling en n parties, une par fichier de données.
DATASET_ROOT_PATH ?= /var/data/${USER}/pacasam_extractions/laz_dataset/  # Où extraire le jeu de données.
PARALLEL_EXTRACTION_JOBS ?= "75%"  # Niveau de parallélisation. Un entier ou un pourcentage des cpu.

help:
	@echo "Makefile"
	@echo "------------------------------------"
	@echo "Cibles pour les tests:"
	@echo "  tests - Lance tous les tests."
	@echo "  tests_no_geoportail_no_slow"
	@echo "  tests_geoportail_or_slow"
	@echo "  open_coverage_report"
	@echo "------------------------------------"
	@echo "Cibles pour l'échantillonnage (par défaut le connecteur est Lipac)"
	@echo "  $(SAMPLERS) CopySampler - Exécute chaque échantillonneur individuellement."
	@echo "  all - Exécute tous les samplers pour un connecteur donné, sauf le CopySampler."
	@echo "  all_synthetic - Exécute tous les samplers pour le connecteur synthétique"
	@echo "------------------------------------"
	@echo "Cibles pour l'extraction:"
	@echo "  extract_toy_laz_data - Vérifie que tout est OK en extrayant depuis les données LAZ de test."
	@echo "  extract_toy_laz_data_in_parallel_from_parts - Vérifie que tout est OK en extrayant depuis les données LAZ de test de façon parallélisée."
	@echo "  _prepare_parallel_extraction - Divise un sampling `SAMPLING_PATH` en n sampling, un par fichier (p.ex. par fichier LAZ), dans SAMPLING_PARTS_DIR."
	@echo "  _run_extraction_in_parallel_from_parts - Extrait le jeu de donnée à partir des n sampling. Spécifier SAMPLING_PARTS_DIR et DATASET_ROOT_PATH"
	@echo "Note: la cible _run_extraction_in_parallel_from_parts permet aussi de poursuivre une extraction interrompue."
	@echo "------------------------------------"
	@echo "Cleaning:"
	@echo "  clean_extractions - Supprime ./outputs/extractions/"
	@echo "  clean_samplings - Supprime ./outputs/samplings/"


# Une seule session bash est utilisé par cible, ce qui permet de partager des variables d'environnement en les exportant.
.ONESHELL:

.PHONY: help all $(SAMPLERS) tests tests_quick tests_geoportail_or_slow tests_lipac open_coverage_report 
.PHONY: extract_toy_laz_data extract_toy_laz_data_in_parallel_from_parts _prepare_parallel_extraction _run_extraction_in_parallel_from_parts
.PHONY: clean_samplings clean_extractions


# TESTS
tests:
	# Run pytest parallelization with at most 6 processes.
	# See https://pytest-xdist.readthedocs.io/en/stable/distribution.html#running-tests-across-multiple-cpus
	# Also, `-s` to show stout is not supported in pytest-xdist - remove paralellization for more logs.
	# See https://pytest-xdist.readthedocs.io/en/stable/known-limitations.html#output-stdout-and-stderr-from-workers
	pytest -s -n auto --dist worksteal --maxprocesses=6

tests_quick:
	# Same, but without test relying on geoportail or lipac, and without slow tests.
	python -m pytest -s -n auto --dist worksteal --maxprocesses=6 -m "not geoportail and not lipac and not slow"

tests_geoportail_or_slow:
	# The slower tests, and the ones relying on geoportail , excluding the ones relying on LiPaC 
	python -m pytest -s -n auto --dist worksteal --maxprocesses=6 -m "(geoportail or slow) and not lipac"

tests_lipac:
	python -m pytest -s -n auto --dist worksteal --maxprocesses=6 -m "lipac"


open_coverage_report:
	# firefox htmlcov/index.html
	xdg-open htmlcov/index.html

# SAMPLING

all: $(SAMPLERS)

$(SAMPLERS):
	python ./src/pacasam/run_sampling.py --config_file=$(CONFIG) \
		--connector_class=$(CONNECTOR) \
		--sampler_class=$@

CopySampler:
	python ./src/pacasam/run_sampling.py --config_file=$(CONFIG) \
		--connector_class=$(CONNECTOR) \
		--sampler_class=CopySampler

all_synthetic:
	make all CONNECTOR=SyntheticConnector CONFIG=configs/Synthetic.yml
	make CopySampler CONNECTOR=SyntheticConnector CONFIG=configs/Synthetic.yml

# Extraction en deux étapes : 
# - Le sampling initial est divisé en autant de parties qu'il y a de fichiers LAZ initiaux concernés.
# Cette étape préliminaire permet une parallélisation au niveau du fichier sans changement du code d'extraction. 
# - La parallélisation est effectuée avec (`GNU parallel`)[https://www.gnu.org/software/parallel/parallel.html].

_prepare_parallel_extraction:
	# Split sampling into n parts, one for each distinct LAZ file.
	python ./src/pacasam/prepare_parallel_extraction.py \
		--sampling_path="${SAMPLING_PATH}" \
		--sampling_parts_dir="${SAMPLING_PARTS_DIR}"

_run_extraction_in_parallel_from_parts:
	# Run extraction in a parallel fashion based on the listing.
	# Single part sampling are removed upon completion of extraction.
	# We can resume extraction without changing the command.
	# Note: another way could be to use option --resume, and we would need to use --joblog beforehand.
	# Note: we need to double quote the whole command, including deletion, so that they happen together.
	ls -1 -d ${SAMPLING_PARTS_DIR}/* | \
		parallel --jobs ${PARALLEL_EXTRACTION_JOBS} --keep-order --progress --verbose --eta \
			"python ./src/pacasam/run_extraction.py \
			--sampling_path {} \
			--dataset_root_path ${DATASET_ROOT_PATH} \
			&& rm {}"

# EXTRACTION ON TOY DATA

extract_toy_laz_data:
	python ./src/pacasam/run_extraction.py \
		--sampling_path ./tests/data/lefty_righty_sampling.gpkg \
		--dataset_root_path ./outputs/extractions/toy_laz_dataset/

extract_toy_laz_data_in_parallel:
	python ./src/pacasam/run_extraction.py \
		--sampling_path ./tests/data/lefty_righty_sampling.gpkg \
		--dataset_root_path ./outputs/extractions/toy_laz_dataset/ \
		--num_jobs=2

extract_toy_laz_data_in_parallel_from_parts:
	# Extraction parallélisée depuis les données de test.
	# En théorie .ONESHELL: fait qu'on n'a pas besoin d'exporter les variables.
	# Mais cela semble créer des erreurs ici... 
	export SAMPLING_PATH=./tests/data/lefty_righty_sampling.gpkg
	export SAMPLING_PARTS_DIR="/tmp/sampling_parts_toy_dataset/"
	export DATASET_ROOT_PATH=./outputs/extractions/toy_laz_dataset/
	export PARALLEL_EXTRACTION_JOBS=2
	make _prepare_parallel_extraction
	make _run_extraction_in_parallel_from_parts

# CLEANING
clean_samplings:
	rm -r ./outputs/samplings/

clean_extractions:
	rm -r ./outputs/extractions/