# Identifiants
export SAMBA_USERNAME=PName@IGN && history -d $((HISTCMD - 1))
export SAMBA_PASSWORD=MonMotDePasseAD && history -d $((HISTCMD - 1))
clear

# sampling train
conda activate pacasam
export SAMPLING_NAME="20230727_75km2_diverse"
export CONFIG_PATH=/home/CGaydon/repositories/pacasam/configs/20230727_75km2_diverse-train.yml
python ./src/pacasam/run_sampling.py \
    --config_file="${CONFIG_PATH}" \
    --output_path="/mnt/store-lidarhd/projet-LHD/IA/PACASAM-SHARED-WORKSPACE/${USER}/${SAMPLING_NAME}/train/"

# sampling test
conda activate pacasam
export CONFIG_PATH=/home/CGaydon/repositories/pacasam/configs/20230727_75km2_diverse-test.yml
export SAMPLING_NAME="20230727_75km2_diverse"
python ./src/pacasam/run_sampling.py \
    --config_file="${CONFIG_PATH}" \
    --output_path="/mnt/store-lidarhd/projet-LHD/IA/PACASAM-SHARED-WORKSPACE/${USER}/${SAMPLING_NAME}/test/"

# Checks :
# Exclusion of some tiles
# Exclusive test/trainval splits
# Right number of patches
# SpatialSampler -> OK
# DiversitySampler -> OK
# TragettedSampler -> OK in train, in test there was no high altitude (>=2000) patches:
# 2023-07-31 17:35:05 WARNING  Could not reach target for points_haute_altitude_heq_2000m. | Found: 0.000 (n=0).
# Logs and configs were saved correctly.
# stats : ok. train ~ val.

conda activate pacasam
export SAMPLING_NAME="20230727_75km2_diverse"
export PARALLEL_EXTRACTION_JOBS="50%"
export DATASET_ROOT_PATH="/mnt/store-lidarhd/projet-LHD/IA/PACASAM-SHARED-WORKSPACE/$USER/${SAMPLING_NAME}/data/"
export USE_SAMBA=Y

export SAMPLING_PATH="/mnt/store-lidarhd/projet-LHD/IA/PACASAM-SHARED-WORKSPACE/$USER/${SAMPLING_NAME}/train/LiPaCConnector-TripleSampler-train.gpkg"
export SAMPLING_PARTS_DIR="/tmp/sampling_parts_for_${SAMPLING_NAME}/"
make extract_laz_dataset_parallel
# nohup make extract_laz_dataset_parallel > "${DATASET_ROOT_PATH}nohup.out.train" &

# test
export SAMPLING_PATH="/mnt/store-lidarhd/projet-LHD/IA/PACASAM-SHARED-WORKSPACE/$USER/${SAMPLING_NAME}/test/LiPaCConnector-TripleSampler-test.gpkg"
export SAMPLING_PARTS_DIR="/tmp/sampling_parts_for_${SAMPLING_NAME}-test"
make extract_laz_dataset_parallel
# nohup make extract_laz_dataset_parallel > "${DATASET_ROOT_PATH}nohup.out.test" &
