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
export SAMPLING_PARTS_DIR="/tmp/sampling_parts_for_${SAMPLING_NAME}-train"
make extract_laz_dataset_parallel
# nohup make extract_laz_dataset_parallel > "${DATASET_ROOT_PATH}nohup.out.train" &

# test
export SAMPLING_PATH="/mnt/store-lidarhd/projet-LHD/IA/PACASAM-SHARED-WORKSPACE/$USER/${SAMPLING_NAME}/test/LiPaCConnector-TripleSampler-test.gpkg"
export SAMPLING_PARTS_DIR="/tmp/sampling_parts_for_${SAMPLING_NAME}-test"
make extract_laz_dataset_parallel
# nohup make extract_laz_dataset_parallel > "${DATASET_ROOT_PATH}nohup.out.test" &

# Remaining
# (pacasam) CGaydon@DEL2212S027:~/repositories/pacasam$ ls $SAMPLING_PARTS_DIR
# LHD_FMQ_0751_6261_PTS_O_LAMB93_IGN69.gpkg  Semis_2021_0785_6414_LA93_IGN69.gpkg  Semis_2021_1179_6101_LA93_IGN78.gpkg
# LHD_FMQ_0755_6259_PTS_O_LAMB93_IGN69.gpkg  Semis_2021_0888_6377_LA93_IGN69.gpkg  Semis_2021_1180_6101_LA93_IGN78.gpkg
# LHD_FMQ_0756_6259_PTS_O_LAMB93_IGN69.gpkg  Semis_2021_0899_6331_LA93_IGN69.gpkg  Semis_2021_1196_6116_LA93_IGN78.gpkg
# LHD_FMQ_0756_6260_PTS_O_LAMB93_IGN69.gpkg  Semis_2021_0900_6333_LA93_IGN69.gpkg  Semis_2021_1198_6063_LA93_IGN78.gpkg
# LHD_FMQ_0766_6267_PTS_O_LAMB93_IGN69.gpkg  Semis_2021_0907_6288_LA93_IGN69.gpkg  Semis_2021_1221_6056_LA93_IGN78.gpkg
# LHD_FMQ_0768_6265_PTS_O_LAMB93_IGN69.gpkg  Semis_2021_0920_6367_LA93_IGN69.gpkg  Semis_2021_1225_6068_LA93_IGN78.gpkg
# LHD_FMQ_0768_6268_PTS_O_LAMB93_IGN69.gpkg  Semis_2021_0935_6299_LA93_IGN69.gpkg  Semis_2021_1228_6078_LA93_IGN78.gpkg
# Semis_2021_0442_6427_LA93_IGN69.gpkg       Semis_2021_0983_6382_LA93_IGN69.gpkg  Semis_2021_1230_6077_LA93_IGN78.gpkg
# Semis_2021_0443_6427_LA93_IGN69.gpkg       Semis_2021_1166_6105_LA93_IGN78.gpkg  Semis_2022_0920_6294_LA93_IGN69.gpkg
# Semis_2021_0443_6433_LA93_IGN69.gpkg       Semis_2021_1166_6110_LA93_IGN78.gpkg  Semis_2022_0921_6293_LA93_IGN69.gpkg
# Semis_2021_0446_6422_LA93_IGN69.gpkg       Semis_2021_1171_6121_LA93_IGN78.gpkg  Semis_2022_0922_6291_LA93_IGN69.gpkg
# Semis_2021_0457_6390_LA93_IGN69.gpkg       Semis_2021_1173_6090_LA93_IGN78.gpkg  Semis_2022_0923_6293_LA93_IGN69.gpkg
# Semis_2021_0462_6388_LA93_IGN69.gpkg       Semis_2021_1176_6096_LA93_IGN78.gpkg
# (pacasam) CGaydon@DEL2212S027:~/repositories/pacasam$
# Probably due to empty tiles in water areas -> bad calculation of the bbox.
# Example : store-lidarhd/production/sauvegarde_production/MQ/PROTOTYPE_MQ_nuage_classe_optimise_LHDSTV1/NUALHD_1-0_MQ_LAMB93_IGN69_20230126/donnees/LHD_FMQ_0751_6261_PTS_O_LAMB93_IGN69.laz

# 2023-07-31 18:10:14 INFO     COMMAND: ./src/pacasam/run_extraction.py --sampling_path /tmp/sampling_parts_for_20230727_75km2_diverse//LHD_FMQ_0751_6261_PTS_O_LAMB93_IGN69.gpkg --dataset_root_path /mnt/store-lidarhd/projet-LHD/IA/PACASAM-SHARED-WORKSPACE/CGaydon/20230727_75km2_diverse/data/ --samba_filesystem
# 2023-07-31 18:10:14 INFO     SAMPLING GEOPACKAGE: /tmp/sampling_parts_for_20230727_75km2_diverse/LHD_FMQ_0751_6261_PTS_O_LAMB93_IGN69.gpkg
# 2023-07-31 18:10:14 INFO     OUTPUT DATASET DIR: /mnt/store-lidarhd/projet-LHD/IA/PACASAM-SHARED-WORKSPACE/CGaydon/20230727_75km2_diverse/data
# 2023-07-31 18:10:15 INFO     LAZExtractor: Extraction + Colorization from \\store.ign.fr\store-lidarhd\production\sauvegarde_production\MQ\PROTOTYPE_MQ_nuage_classe_optimise_LHDSTV1\NUALHD_1-0_MQ_LAMB93_IGN69_20230126\donnees\LHD_FMQ_0751_6261_PTS_O_LAMB93_IGN69.laz (k=2 patches)
# https://wxs.ign.fr/ortho/geoportail/r/wms?LAYERS=ORTHOIMAGERY.ORTHOPHOTOS&EXCEPTIONS=text/xml&FORMAT=image/geotiff&SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&STYLES=&CRS=EPSG:2154&BBOX=0,0,0,0&WIDTH=0&HEIGHT=0

# Checking Samba file existence.:   0%|          | 0/1 [00:00<?, ?Samba file/s]
# Checking Samba file existence.: 100%|██████████| 1/1 [00:00<00:00, 11.89Samba file/s]
# /var/data/mambaforge-shared/envs/pacasam/lib/python3.9/site-packages/osgeo/osr.py:385: FutureWarning: Neither osr.UseExceptions() nor osr.DontUseExceptions() has been explicitly called. In GDAL 4.0, exceptions will be enabled by default.
#   warnings.warn(
# Traceback (most recent call last):
#   File "/home/CGaydon/repositories/pacasam/./src/pacasam/run_extraction.py", line 56, in <module>
#     run_extraction(args)
#   File "/home/CGaydon/repositories/pacasam/./src/pacasam/run_extraction.py", line 50, in run_extraction
#     extractor.extract()
#   File "/home/CGaydon/repositories/pacasam/src/pacasam/extractors/laz.py", line 75, in extract
#     self._extract_from_single_file(single_file_path, single_file_sampling)
#   File "/home/CGaydon/repositories/pacasam/src/pacasam/extractors/laz.py", line 99, in _extract_from_single_file
#     colorize_single_patch(nocolor_patch=Path(tmp_nocolor_patch.name), colorized_patch=colorized_patch, srid=srid)
#   File "/home/CGaydon/repositories/pacasam/src/pacasam/extractors/laz.py", line 140, in colorize_single_patch
#     color(str(nocolor_patch.resolve()), str(colorized_patch.resolve()), proj=str(srid))
#   File "/var/data/mambaforge-shared/envs/pacasam/lib/python3.9/site-packages/pdaltools/unlock_file.py", line 36, in newfn
#     return func(*args, **kwargs)
#   File "/var/data/mambaforge-shared/envs/pacasam/lib/python3.9/site-packages/pdaltools/color.py", line 144, in color
#     download_image_from_geoportail_retrying(proj, "ORTHOIMAGERY.ORTHOPHOTOS", minx, miny, maxx, maxy, pixel_per_meter, tmp_ortho, timeout_second)
#   File "/var/data/mambaforge-shared/envs/pacasam/lib/python3.9/site-packages/pdaltools/color.py", line 46, in newfn
#     raise err
#   File "/var/data/mambaforge-shared/envs/pacasam/lib/python3.9/site-packages/pdaltools/color.py", line 37, in newfn
#     return func(*args, **kwargs)
#   File "/var/data/mambaforge-shared/envs/pacasam/lib/python3.9/site-packages/pdaltools/color.py", line 83, in download_image_from_geoportail
#     req.raise_for_status()
#   File "/var/data/mambaforge-shared/envs/pacasam/lib/python3.9/site-packages/requests/models.py", line 1021, in raise_for_status
#     raise HTTPError(http_error_msg, response=self)
# requests.exceptions.HTTPError: 400 Client Error: BadRequest for url: https://wxs.ign.fr/ortho/geoportail/r/wms?LAYERS=ORTHOIMAGERY.ORTHOPHOTOS&EXCEPTIONS=text/xml&FORMAT=image/geotiff&SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&STYLES=&CRS=EPSG:2154&BBOX=0,0,0,0&WIDTH=0&HEIGHT=0
# 2023-07-31 18:10:15 INFO     Extraction of a dataset using pacasam (https://github.com/IGNF/pacasam).
# Du a LAZ vide car on n'a pas filtré les patches avec nb_total>1 (on le fera dans la branche de dev et on corrigera...)
# On le fait, et on adapte myria3d au passage pour accepter ces situations :
# https://github.com/IGNF/myria3d/pull/81
