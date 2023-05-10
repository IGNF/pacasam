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
	@echo "Liste des cibles disponibles :"
	@echo "  $(SAMPLERS) - Exécute chaque échantillonneur individuellement."
	@echo "  all - Exécute toutes les tâches pour un connecteur donné. Par défaut: Lipac"
	@echo "  all_for_all_connectors - Make all appliqué aux connecteurs Lipac et Synthetic."
	@echo "  help - Affiche cette aide."
	@echo "Run complet :"
	@echo "  make all REPORTS=Y"
	@echo "  make all REPORTS=Y CONNECTOR=SyntheticConnector CONFIG=configs/Synthetic.yml"

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
	pytest -s

open_coverage_report:
	firefox htmlcov/index.html