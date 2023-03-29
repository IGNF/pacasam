# Override with
# CONNECTOR=SyntheticCConnector CONFIG="./configs/Synthetic.yml" bash ./run_all.sh
CONNECTOR=${CONNECTOR:-LiPaCConnector}
CONFIG=${CONFIG:-"configs/Lipac.yml"}
REPORTS=${REPORTS:-"N"}

python ./src/pacasam/main.py --config_file=${CONFIG} \
    --connector_class=${CONNECTOR} \
    --sampler_class=RandomSampler \
    --make_html_report=${REPORTS}

python ./src/pacasam/main.py --config_file=${CONFIG} \
    --connector_class=${CONNECTOR} \
    --sampler_class=SpatialSampler \
    --make_html_report=${REPORTS}

python ./src/pacasam/main.py --config_file=${CONFIG} \
    --connector_class=${CONNECTOR} \
    --sampler_class=DiversitySampler \
    --make_html_report=${REPORTS}

python ./src/pacasam/main.py --config_file=${CONFIG} \
    --connector_class=${CONNECTOR} \
    --sampler_class=TripleSampler \
    --make_html_report=${REPORTS}
