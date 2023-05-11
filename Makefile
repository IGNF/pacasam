# /!\ Environnement pacasam à activer avec: conda activate pacasam

# Dans ce Makefile, la variable SAMPLERS contient les noms des quatre échantillonneurs disponibles. 
# La cible all dépend de toutes les cibles définies dans $(SAMPLERS). 
# Une règle générique permet d'exécuter chaque échantillonneur en utilisant la variable $@ qui contient le nom de la cible actuelle.

# Exécutez toutes les tâches en une seule fois en utilisant la commande:
# 	make all.
# Exécutez une tâche spécifique en utilisant le nom de la tâche en tant que cible: make RandomSampler, make SpatialSampler, etc.
# Exécutez sur le jeu de données synthtéiques avec 
#	make all CONNECTOR=SyntheticConnector CONFIG=configs/Synthetic.yml

CONNECTOR ?= LiPaCConnector  # LiPaCConnector ou SyntheticConnector
CONFIG ?= configs/Lipac.yml  # configs/Lipac.yml ou configs/Synthetic.yml - Devrait correspondre au connecteur!
REPORTS ?= N # N(o) ou Y(es). No pour des résultats plus rapides.
SAMPLERS = RandomSampler SpatialSampler TargettedSampler DiversitySampler TripleSampler OutliersSampler

help:
	@echo "Makefile"
	@echo "------------------------------------"
	@echo "Cibles pour l'échantillonnage:"
	@echo "  $(SAMPLERS) - Exécute chaque échantillonneur individuellement."
	@echo "  all - Exécute tous les samplers pour un connecteur donné (par défaut: connecteur Lipac)"
	@echo "  all CONNECTOR=SyntheticConnector CONFIG=configs/Synthetic.yml - pour passer le connectuer Synthetic"
	@echo "  all_for_all_connectors - 'Make all' pour les deux connecteurs (Lipac et Synthetic)."
	@echo "  clean_extractions - Supprime ./outputs/samplings/"
	@echo "Note: L'option 'REPORTS=Y' permet la création d'un rapport HTML à partir du sampling."
	@echo "------------------------------------"
	@echo "Cibles pour l'extraction:"
	@echo "  extraction_of_laz_test_data - Lance une extraction d'un jeu de données laz depuis les données laz de test."
	@echo "  clean_extractions - Supprime ./outputs/extractions/"
	@echo "------------------------------------"


.PHONY: all help $(SAMPLERS) tests open_coverage_report

all: $(SAMPLERS)

$(SAMPLERS):
	python ./src/pacasam/run_sampling.py --config_file=$(CONFIG) \
		--connector_class=$(CONNECTOR) \
		--sampler_class=$@ \
		--make_html_report=$(REPORTS)

all_for_all_connectors:
	make all REPORTS=Y
	make all REPORTS=Y CONNECTOR=SyntheticConnector CONFIG=configs/Synthetic.yml

tests:
	# Runb pytest- paralellization with at most 6 processes.
	# See https://pytest-xdist.readthedocs.io/en/stable/distribution.html#running-tests-across-multiple-cpus
	# Also, `-s` to show stout is not supported in pytest-xdist - remove paralellization for more logs.
	# See https://pytest-xdist.readthedocs.io/en/stable/known-limitations.html#output-stdout-and-stderr-from-workers
	pytest -s -n auto --dist worksteal --maxprocesses=6

open_coverage_report:
	firefox htmlcov/index.html

extraction_of_laz_test_data:
	python ./src/pacasam/run_extraction.py \
		--sampling_path ./tests/data/lefty_righty_sampling.gpkg \
		--dataset_root_path ./outputs/extractions/toy_laz_dataset/

clean_samplings:
	rm -r ./outputs/samplings/

clean_extractions:
	rm -r ./outputs/extractions/