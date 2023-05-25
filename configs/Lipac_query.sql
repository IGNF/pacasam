/*
Colonnes nécessaires pour l'échantillonnage :

- geometry : géométrie du patch
- patch_id : identifiant unique de chaque patch dans le résultat de la requête
- file_id : identifiant unique de chaque fichier dans le résultat de la requête
- file_path : chemin d'accès pour l'extraction des données, utilisé après l'échantillonnage. 
Pour Lipac, il est attendu qu'il s'agisse d'un fichier stocké dans un système de stockage de données Samba, commençant par \store.ign.fr\store-lidarhd.

Nota : un LEFT JOIN est appliqué pour croisement_vignette pour l'instant car la table est vide.
*/
SELECT VIGNETTE_ET_CHEMIN.*,
	DALLE.RACINE_DU_NOM AS FILE_ID
FROM
	(SELECT PATCHES_WITH_STATS_AND_CROISEMENT.*,
			FICHIER_LIDAR.CHEMIN_DALLES AS FILE_PATH
		FROM
			(SELECT PATCHES_WITH_STATS.*,
					PRESENCE_DE_SURFACES_D_EAU,
					PRESENCE_DE_PYLONES,
					PRESENCE_D_AUTOROUTES
				FROM
					(SELECT PATCHES.*,
							NB_TOTAL,
							NB_SOL,
							NB_BATI,
							NB_VEGETATION_BASSE,
							NB_VEGETATION_MOYENNE,
							NB_VEGETATION_HAUTE,
							NB_PONT,
							NB_EAU,
							NB_SURSOL_PERENNE,
							NB_NON_CLASSES,
							NB_ARTEFACTS,
							DENIVELE,
							ALTITUDE,
							(NB_BATI >= 500) AS NB_POINTS_BATI_HEQ_500,
							((NB_BATI / (NB_TOTAL + 0.000001)) >= 0.25) AS NB_POINTS_BATI_HEQ_QUARTER_OF_ALL_POINTS,
							NB_EAU >= 50 AS NB_POINTS_EAU_HEQ_50,
							NB_PONT >= 50 AS NB_POINTS_PONT_HEQ_50,
							NB_SURSOL_PERENNE >= 50 AS NB_POINTS_SURSOL_PERENNE_HEQ_500,
							((DENIVELE >= 30)
								AND (DENIVELE < 45)) AS FORT_DEVERS_DENIVELE_ENTRE_30_45,
							(DENIVELE >= 45) AS FORT_DEVERS_DENIVELE_HEQ_45,
							((1000 <= ALTITUDE)
								AND (ALTITUDE < 2000)) AS POINTS_HAUTE_ALTITUDE_ENTRE_1000M_2000M,
							2000 <= ALTITUDE AS POINTS_HAUTE_ALTITUDE_HEQ_2000M
						FROM
							(SELECT VIGNETTE.ID AS PATCH_ID,
									VIGNETTE.DALLE_ID,
									VIGNETTE.GEOMETRIE AS GEOMETRY
								FROM VIGNETTE) AS PATCHES
						JOIN STAT_VIGNETTE_LIDAR ON PATCHES.PATCH_ID = STAT_VIGNETTE_LIDAR.VIGNETTE_ID) AS PATCHES_WITH_STATS
				LEFT JOIN CROISEMENT_VIGNETTE ON CROISEMENT_VIGNETTE.VIGNETTE_ID = PATCHES_WITH_STATS.PATCH_ID) AS PATCHES_WITH_STATS_AND_CROISEMENT
		JOIN FICHIER_LIDAR ON PATCHES_WITH_STATS_AND_CROISEMENT.DALLE_ID = FICHIER_LIDAR.DALLE_ID
		WHERE FICHIER_LIDAR.VERSION_DE_REFERENCE) AS VIGNETTE_ET_CHEMIN
JOIN DALLE ON VIGNETTE_ET_CHEMIN.DALLE_ID = DALLE.ID;