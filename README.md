# pacasam
Patch-Catalogue-Sampling: methods to sample a catalogue (e.g. PostGIS database) of data patches based on their metadata, for deep learning dataset pruning.


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
    - [ ] (Si nécessaire face à volume de données important) Connecteur données synthétiques pourrait dériver d'un connecteur "GeoDataFrame" avec des opérations de query. Et alors on peut envisager que toute la base Lipac soit mise en mémoire, pour des traitements plus rapides.

- [ ] Prise en main PGADMIN ou BDBeaver pour anticipation des opérations copie+manipulation. Idée de "version de référence" maintenue dont partent des copies / enrichissements, qui se feraient avec des requêtes simples.
- Optimisation : 
    - [X] Config de base avec l'ensemble des indicateurs, pour tests sur 250km² et une npremière viz. 
    - [ ] Créer une brique de Farthest point Sampling, double usage : 
        - [ ] Spatial Sampling par FPS --> pour l'instant semble une optimisation car déjà bonne répartition même avec 4M de tuiles de base.
        - [ ] Spatiale Sampling par itération sur les dalles et sélection d'un patch à chaque fois. On peut envisager une méthode effficae où on attribue un index à chaque patch au sein de chaque dalle, et ensuite on filtre avec un seuil ? Overkill, commencer simple : on devrait sélectionner max 5 patches en conditions réelles. MAIS : les patches ne seront pas optimisés spatialement entre des dalles adjacentes, juste bien répartie par grille. Semble OK.
- Extraction
    - [X] Extract geopackag des métadonnées
    - [ ] Rechercher un format hybride intégrant les données Lidars et permettant affichage dans QGIS. PostGreSQL-3D


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


# Analyses 
- Tets de charge sur données synthétique, pour étudier la répartition d'après différents sampling (aléatoire ou spatiel éventuel).
    --> Passe en mémoire (id et géométrie au moins). Sampling possible. A voir pour l'extract avec tous les attributs, besoin probable de chunker la données requêtée pour sauvegarde. 
    --> Analyse des KNN - 288m attendu de distance moyenne). Problème de projection! A refaire en enregistrant le geopackage avec cf. [QGIS doc](https://docs.qgis.org/3.22/en/docs/user_manual/processing_algs/qgis/vectoranalysis.html#nearest-neighbour-analysis). Largeur des polygones fake n'est pas bonne. peut-être lié à enregistrement / projection... (35m de coté dans qgis).