# /!\ Environnement pacasam à activer avec: conda activate pacasam

# Dans ce Makefile, la variable SAMPLERS contient les noms des quatre échantillonneurs disponibles. 
# La cible all dépend de toutes les cibles définies dans $(SAMPLERS). 
# Une règle générique permet d'exécuter chaque échantillonneur en utilisant la variable $@ qui contient le nom de la cible actuelle.

# Exécutez toutes les tâches en une seule fois en utilisant la commande make all.
# Exécutez une tâche spécifique en utilisant le nom de la tâche en tant que cible: make RandomSampler, make SpatialSampler, etc.

# Les échantillonnages sont sauvegardés sous /outputs/samplings/\{sampler_class\}-\{connector_class\}

CONNECTOR ?= LiPaCConnector  # LiPaCConnector ou SyntheticConnector
CONFIG ?= configs/Lipac.yml  # configs/Lipac.yml ou configs/Synthetic.yml - Devrait correspondre au connecteur!
REPORTS ?= N # N(o) ou Y(es). No pour des résultats plus rapides.
SAMPLERS = RandomSampler SpatialSampler DiversitySampler TripleSampler TargettedSampler

.PHONY: all help $(SAMPLERS)

all: $(SAMPLERS)

help:
	@echo "Liste des cibles disponibles :"
	@echo "  all - Exécute toutes les tâches."
	@echo "  $(SAMPLERS) - Exécute chaque échantillonneur individuellement."
	@echo "  help - Affiche cette aide."

$(SAMPLERS):
	python ./src/pacasam/main.py --config_file=$(CONFIG) \
		--connector_class=$(CONNECTOR) \
		--sampler_class=$@ \
		--make_html_report=$(REPORTS)
