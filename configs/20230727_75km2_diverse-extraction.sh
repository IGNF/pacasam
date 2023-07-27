conda activate pacasam
export SAMPLING_NAME="20230727_75km2_diverse"
export PARALLEL_EXTRACTION_JOBS="50%"
export DATASET_ROOT_PATH="/mnt/store-lidarhd/projet-LHD/IA/PACASAM-SHARED-WORKSPACE/$USER/${SAMPLING_NAME}/data/"

export SAMPLING_PATH="/mnt/store-lidarhd/projet-LHD/IA/PACASAM-SHARED-WORKSPACE/$USER/${SAMPLING_NAME}/train/LiPaCConnector-TripleSampler-train.gpkg"
export SAMPLING_PARTS_DIR="/tmp/sampling_parts_for_${SAMPLING_NAME}/"
nohup make extract_laz_dataset_parallel >nohup.out.train &

# test
export SAMPLING_PATH="/mnt/store-lidarhd/projet-LHD/IA/PACASAM-SHARED-WORKSPACE/$USER/${SAMPLING_NAME}/test/LiPaCConnector-TripleSampler-test.gpkg"
export SAMPLING_PARTS_DIR="/tmp/sampling_parts_for_${SAMPLING_NAME}-test"
nohup make extract_laz_dataset_parallel >nohup.out.test &
