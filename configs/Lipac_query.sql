WITH FICHIER_LIDAR_REFERENCE AS
  (SELECT FICHIER_LIDAR.ID,
          VERSION_DE_REFERENCE,
          CHEMIN_DALLES AS FILE_PATH
   FROM FICHIER_LIDAR
   WHERE VERSION_DE_REFERENCE),
     STAT_LIDAR_REFERENCE AS
  (SELECT FICHIER_LIDAR_REFERENCE.FILE_PATH,
          VIGNETTE_ID,
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
          NB_ARTEFACT,
          DENIVELE,
          ALTITUDE
   FROM STAT_VIGNETTE_LIDAR
   JOIN FICHIER_LIDAR_REFERENCE ON STAT_VIGNETTE_LIDAR.FICHIER_LIDAR_ID = FICHIER_LIDAR_REFERENCE.ID
   WHERE NB_TOTAL > 0 ),
     VIGNETTE_COLS AS
  (SELECT VIGNETTE.ID AS PATCH_ID,
          VIGNETTE.DALLE_ID,
          VIGNETTE.GEOMETRIE AS GEOMETRY
   FROM VIGNETTE),
     VIGNETTES_AVEC_STATS_ET_CROISEMENT AS
  (SELECT VIGNETTE_COLS.PATCH_ID,
          VIGNETTE_COLS.DALLE_ID,
          VIGNETTE_COLS.GEOMETRY AS GEOMETRY,
          STAT_LIDAR_REFERENCE.*,
          (NB_BATI >= 500) AS NB_POINTS_BATI_HEQ_500,
          ((NB_BATI / (NB_TOTAL + 0.000001)) >= 0.25) AS NB_POINTS_BATI_HEQ_QUARTER_OF_ALL_POINTS,
          NB_EAU >= 50 AS NB_POINTS_EAU_HEQ_50,
          NB_PONT >= 50 AS NB_POINTS_PONT_HEQ_50,
          NB_SURSOL_PERENNE >= 50 AS NB_POINTS_SURSOL_PERENNE_HEQ_50,
          ((DENIVELE >= 30)
           AND (DENIVELE < 45)) AS FORT_DEVERS_DENIVELE_ENTRE_30_45,
          (DENIVELE >= 45) AS FORT_DEVERS_DENIVELE_HEQ_45,
          ((1000 <= ALTITUDE)
           AND (ALTITUDE < 2000)) AS POINTS_HAUTE_ALTITUDE_ENTRE_1000M_2000M,
          2000 <= ALTITUDE AS POINTS_HAUTE_ALTITUDE_HEQ_2000M,
          CROISEMENT_VIGNETTE.PRESENCE_DE_SURFACES_D_EAU,
          CROISEMENT_VIGNETTE.PRESENCE_DE_PYLONES,
          CROISEMENT_VIGNETTE.PRESENCE_D_AUTOROUTES
   FROM STAT_LIDAR_REFERENCE
   JOIN VIGNETTE_COLS ON STAT_LIDAR_REFERENCE.VIGNETTE_ID = VIGNETTE_COLS.PATCH_ID
   LEFT JOIN CROISEMENT_VIGNETTE ON CROISEMENT_VIGNETTE.VIGNETTE_ID = VIGNETTE_COLS.PATCH_ID)
SELECT TEST_ET_EXCLUSION.TEST,
       DALLE.RACINE_DU_NOM AS FILE_ID,
       VIGNETTES_AVEC_STATS_ET_CROISEMENT.*,
       BLOC.SRID
FROM VIGNETTES_AVEC_STATS_ET_CROISEMENT
JOIN DALLE ON VIGNETTES_AVEC_STATS_ET_CROISEMENT.DALLE_ID = DALLE.ID
JOIN BLOC ON DALLE.BLOC_ID = BLOC.ID
LEFT JOIN
  (SELECT BOOL_OR(JEU_DE_DALLES.TEST) AS TEST,
          BOOL_OR(JEU_DE_DALLES.A_EXCLURE) AS A_EXCLURE,
          RELATION_DALLES_JEUX.DALLE_ID
   FROM RELATION_DALLES_JEUX
   JOIN JEU_DE_DALLES ON RELATION_DALLES_JEUX.JEU_DE_DALLES_ID = JEU_DE_DALLES.ID
   GROUP BY RELATION_DALLES_JEUX.DALLE_ID) AS TEST_ET_EXCLUSION ON TEST_ET_EXCLUSION.DALLE_ID = VIGNETTES_AVEC_STATS_ET_CROISEMENT.DALLE_ID
WHERE (NOT TEST_ET_EXCLUSION.A_EXCLURE
       OR TEST_ET_EXCLUSION.A_EXCLURE IS NULL);