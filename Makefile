# /!\ Environnement pacasam à activer avec: conda activate pacasam
# Echantillonnages sauvegardés sous /outputs/samplings/{sampler_class}-{connector_class}

CONNECTOR ?= LiPaCConnector  # LiPaCConnector ou SyntheticConnector
CONFIG ?= configs/Lipac.yml  # configs/Lipac.yml ou configs/Synthetic.yml - Should match the Connector!
REPORTS ?= N # N(o) ou Y(es). No for faster results.

.PHONY: all
all: RandomSampler SpatialSampler DiversitySampler TripleSampler

RandomSampler:
	python ./src/pacasam/main.py --config_file=$(CONFIG) \
		--connector_class=$(CONNECTOR) \
		--sampler_class=RandomSampler \
		--make_html_report=$(REPORTS)

SpatialSampler:
	python ./src/pacasam/main.py --config_file=$(CONFIG) \
		--connector_class=$(CONNECTOR) \
		--sampler_class=SpatialSampler \
		--make_html_report=$(REPORTS)

DiversitySampler:
	python ./src/pacasam/main.py --config_file=$(CONFIG) \
		--connector_class=$(CONNECTOR) \
		--sampler_class=DiversitySampler \
		--make_html_report=$(REPORTS)

TripleSampler:
	python ./src/pacasam/main.py --config_file=$(CONFIG) \
		--connector_class=$(CONNECTOR) \
		--sampler_class=TripleSampler \
		--make_html_report=$(REPORTS)