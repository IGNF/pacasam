# pacasam
Patch-Catalogue-Sampling: methods to sample a catalogue (e.g. PostGIS database) of data patches based on their metadata, for deep learning dataset pruning.


## Contenu

Classes d'objets:
- Connector: interface de connexion aux données: 
    - LiPaC: connexion et requêtage de la base LiPaC.
    - Synthetic: création d'un GeoDataFrame synthétique, composé de tuiles répartie dans une grille arbitraire, pour effectuer des tests rapidements.
- Sampler: objet de sampling, qui interrogent le connector suivant la configuration pour sélectionne des tuiles (patches) par leur identifiant, et qui définissent à la volée le split train/test.
    - Targetted: atteinte séquentielle des contraintes de prévalence pour chaque descritpteur. Répartition spatiale optimale.
    - Diverse: couverture par Farthest Point Sampling de l'espace des descripteurs (i.e. nombre de points de certaines classes, quantilisés)
    - Completion: complétion aléatoire pour atteindre une taille de jeu de données cible. Répartition spatiale optimale.

Le processus de sampling sauvegarde un geopackage dans `outputs/{ConnectorName}/{SamplingName}-extract.gpkg`, contenant l'échantillon de tuiles avec l'ensemble des champs de la base de données initiales, ainsi qu'une variable `is_test_set` définissant le jeu de test pour un futur apprentissage.


## Usage
Mettre en place l'environnement virtual conda:
```bash
conda install mamba --yes -n base -c conda-forge
mamba env create -f environment.yml
```
Lancer un échantillonnage "tripl" sur des données synthétiques :
```python
conda activate pacasam
python src/pacasam/samplers/triple.py --connector=synthetic
```
Lancer un échantillonnage "tripl" sur des données réelles - base PostGIS LiPaC:
1. Créer fichier `credentials.ini` avec la section `[LIDAR_PATCH_CATALOGUE]` et les champs `DB_LOGIN` et `DB_PASSWORD`. (droits en lecture nécessaires.)
2. Créer sa configuration dans le dossier `configs` (cf. `configs/lipac-optimization-config.yml`). Vérifier notamment les champs liés à la base de données PostGIS à requêter.
3. Lancer le sampling.
```python
conda activate pacasam
python src/pacasam/samplers/triple.py --connector=synthetic
```

# Roadmap

- Structure :
    - [X] mise en place espace de travail
        - [X] repo github, env, connector, structure... attention aux credentials.
    - Objets: connector, une config, un sampler. 
        - entrée : config et contraintes sur chaque critère
        - tout le système pour requêter la BD, le plus indépendant du schéma possible (connecteur + config mdp).
        - Le système de sauvegarde du sampling = un listing des id à conserver + les géométries pour possibilité d'inspection dans QGIS --> dump direct d'une sous sélection de la base en geopackage.
    - [X] Fonctionnalités de bases des connecteurs:
        - [X] Requêter si indicateur binaire est vrai (Nota: doit on faire aussi si faux ?)
        - [X] Compléter aléatoirement avec d'autres ids
        - [X] Faire un extract sur la base des ids.
        - [ ] Requête spatialement distribuée. Si large base (> seuil), travailler par chunk, puis redistribution eventuelle dans la sélection.
    - [X] Connecteur "données synthétique"
    - [X] Connecteur LiPaC
    - [ ] (**Si nécessaire face à volume de données important**) Connecteur données synthétiques pourrait dériver d'un connecteur "GeoDataFrame" avec des opérations de query. Et alors on peut envisager que toute la base Lipac soit mise en mémoire, pour des traitements plus rapides.
    - [X] *random* completion -> spatial sampling for completion.
- [X] Prise en main PGADMIN ou BDBeaver pour anticipation des opérations copie+manipulation. Idée de "version de référence" maintenue dont partent des copies / enrichissements, qui se feraient avec des requêtes simples.
- [ ] API unique pour les samplers, dans run.py, avec config en argument.
- [ ] Renommer criteria dans config pour préciser qu'il s'agit de targetted sampling. Le nommer par le nom de la classe !
- [ ] Possibilité d'un filtre en amont sur la BD. 
    - [ ] Possibilité de créer une table "vignette_pool" temporaire basée sur ce filtre, et requêter là dessus ?
    - Filtre nb_points > 50. (Mais qu'en est-il de l'eau alors ?...)
    - Filtre sur les chantier, pour exclure ou inclure certains, et créer le **jeu de test de façon exclusive**.
    - (Peut-être mise en mémoire alors de la BD filtrée, avec un connecteur type GeoDataFrame ? (Vérifier que ça scalera). -6> pas très satisfaisant, enlève l'intérêt d'une base "online" facilement inspectable.
    - Préférer l'option "on fait une copie locale de la BD" sur laquelle on a des droits d'écriture 
        - Cf. pour faire une copie : https://stackoverflow.com/a/8815010/8086033 ; sinon en click boutont dans PGAdmin en faisant aussi un backup. Mais pas satisfaisant... Voir si on peut contrôler les rôles suffisamment pour autoriser tables temporaires.
        - https://desertdba.com/what-permissions-are-required-for-temporary-tables/ --> possibilité de créer la base temporaire en amont, et que chaque use puisse la remplir avec "ses" vignettes au moment de la connexion ? Dans ce cas, on doit juste s'assurer que la connexion reste ouverte. A valider avec Marouane ?
        - Now, the point of this exercise is not so much about the 40 MB space as it is this: by default, any user can consume any tempdb space, limited only by either maximum file size or available drive space. See here ; https://learn.microsoft.com/en-us/sql/relational-databases/databases/tempdb-database?view=sql-server-ver16 ; is this applicable ?


- Optimisation :
    - [X] Config de base avec l'ensemble des indicateurs, pour tests sur 250km² et une npremière viz. 
    - [X] Spatiale Sampling par itération sur les dalles et sélection d'un patch à chaque fois.
        On peut envisager une méthode effficae où on attribue un index à chaque patch au sein de chaque dalle, et ensuite on filtre avec un seuil ? Overkill, commencer simple : on devrait sélectionner max 5 patches en conditions réelles. MAIS : les patches ne seront pas optimisés spatialement entre des dalles adjacentes, juste bien répartie par grille. Semble OK.
        - [X] Version "in memory" qui nécessite de charger id et dalle en mémoire.
    - [ ] Seeds to have a reproductible dataset. Works with postgis as well?
    - [X] Diversity sampling : Sampling prenant en compte des clusters 'e.g. les deciles de chaque classe, croisés ensemble), de façon représentative, et spatialisée.
        - [ ] Contrôle et paramétrisation des éléments du diversity sampling. En gros, les différents indicators à définir par des requêter sql (si différent du nom de base, cf. criteria). Être capable de faire une unique requete sql pour remplacer l'usage de sampler.extract qui n'est pas prévue pour ça.
    - [ ] Get rid of unused random sampling / simplify its call and remove the if/else clause.
- Extraction
    - [X] Extract geopackage des métadonnées
    - [ ] Rechercher un format hybride intégrant les données Lidar et permettant affichage dans QGIS. PostGreSQL-3D.


# Panini - évolutions :
- Passer les booléens en int pour faciliter opérations ">0". (cf. https://stackoverflow.com/a/1465432/8086033)
- Enumerable des noms de classes en français --> pas forcément nécessaire, plutôt de la doc.
- correction de "nb points artefats" -> artefaCts
- Documentation des noms de variables et de leur définition (altitude, dénivelés) dans un xslx (Databook)
- Indexation spatiale de la base, et rajoute de colonne directemnet avec une unique requête SQL (+ éventuellement ligne python pour schéma.)
- Revue possible avec Marouane, des quelques fonctionnalités essentielles. Idée d'avoir une base de travail, qui peut être copiée ensuite par des utilisateurs dans un second temps, pour usage et sampling. Test BDBeaver à faire.
- Nombre de points minimum par tuile à imposer ? On peut envisager un filtre en amont sur la BD. On peut aussi compléter la requête à chaque fois. Peut-on créer une table temporaire intermédiaire un premier temps à ensuite requêter ?
- Dans zones d'eau, sans point sol, le dénivelé vaut -18446744073709551616. Passer à NULL ? Quelles conséquences sur les requêtes ensuite ?
- Nom complet des fichiers LAS dans le Store vers la base
- Table Blocs ?
smb://store.ign.fr/store-lidarhd/production/reception/QO/donnees_classees/livraison10p/Livraison_20230116/02_SemisClasse
- Ref sur les ORMS : https://stackoverflow.com/a/56992364/8086033
- Backup de Lipac:  pg_dump dbname > outfile
- Colonnes spécifiant la redondance avec jeux de données pré-existants : 151proto, 201eval, Annecy. Fournir les emprises en format standard.


# Analyses 
- Tets de charge sur données synthétique, pour étudier la répartition d'après différents sampling (aléatoire ou spatiel éventuel).
    --> Passe en mémoire (id et géométrie au moins). Sampling possible. A voir pour l'extract avec tous les attributs, besoin probable de chunker la données requêtée pour sauvegarde. 
    --> Analyse des KNN - 288m attendu de distance moyenne). Problème de projection! A refaire en enregistrant le geopackage avec cf. [QGIS doc](https://docs.qgis.org/3.22/en/docs/user_manual/processing_algs/qgis/vectoranalysis.html#nearest-neighbour-analysis). Largeur des polygones fake n'est pas bonne. peut-être lié à enregistrement / projection... (35m de coté dans qgis).