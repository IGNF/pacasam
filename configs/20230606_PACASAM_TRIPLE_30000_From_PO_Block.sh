# git checkout 20230606_PACASAM_TRIPLE_30000_From_PO_Block

# Run training sampling
USER_WORKSPACE="/mnt/store-lidarhd/projet-LHD/IA/PACASAM-SHARED-WORKSPACE/$(echo ${USER})/"
SAMPLING_NAME=20230606_PACASAM_TRIPLE_30000_From_PO_Block

TRAIN_CONFIG_PATH="/home/$(echo ${USER})/repositories/pacasam/configs/${SAMPLING_NAME}-TRAIN.yml"
python ./src/pacasam/run_sampling.py \
  --config_file="${TRAIN_CONFIG_PATH}" \
  --output_path="${USER_WORKSPACE}${SAMPLING_NAME}/train/"

# Run test sampling
TEST_CONFIG_PATH="/home/$(echo ${USER})/repositories/pacasam/configs/${SAMPLING_NAME}-TEST.yml"
python ./src/pacasam/run_sampling.py \
  --config_file="${TEST_CONFIG_PATH}" \
  --output_path="${USER_WORKSPACE}${SAMPLING_NAME}/test/"


# extraction :
SAMPLING_PATH="/mnt/store-lidarhd/projet-LHD/IA/PACASAM-SHARED-WORKSPACE/CGaydon/samplings/20230606_PACASAM_TRIPLE_30000_From_PO_Block/LiPaCConnector-TripleSampler-train.gpkg" \
SAMPLING_PARTS_DIR="/tmp/sampling_parts_20230606_PACASAM_TRIPLE_30000_From_PO_Block/" \
PARALLEL_EXTRACTION_JOBS="50%" \
SAMBA_CREDENTIALS_PATH="credentials.yml" \
DATASET_ROOT_PATH="/mnt/store-lidarhd/projet-LHD/IA/PACASAM-SHARED-WORKSPACE/CGaydon/samplings/20230606_PACASAM_TRIPLE_30000_From_PO_Block/train/" \
nohup make run_extraction_in_parallel &