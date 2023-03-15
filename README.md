# pacasam
Patch-Catalogue-Sampling: methods to sample a catalogue (e.g. PostGIS database) of data patches based on their metadata, for deep learning dataset pruning.


# Roadmap

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
- [ ] Prise en main PGADMIN ou BDBeaver pour anticipation des opérations copie+manipulation. Idée de "version de référence" maintenue dont partent des copies / enrichissements, qui se feraient avec des requêtes simples.
- Optimisation : 
    - [ ] Config de base avec l'ensemble des indicateurs, pour tests sur 250km² et une npremière viz. 
        Réfléxion sur le format pour faciliter l'ajout ; garder possibilité d'afficher dans excel MAIS en protégeant les strings. Attention aux conversions automatiques... Fichier excel directement ? Moins risqué ? Mais moins standard... Et si format tabulaire pas possible d'ajouter des autres paramètres efficacement ! Sinon : proposer une conversion simple de yaml vers excel pour analyse, juste sur les objectifs de l'opti...

+ cf. les todo dans le code

Panini - requests :
    - Passer les booléens en int pour faciliter opérations ">0". (cf. https://stackoverflow.com/a/1465432/8086033)
    - Enumerable des noms de classes en français
    - correction de "nb points artefats"
    - Documentation des noms de variables et de leur définition (altitude, dénivelés) dans un xslx (Databook)
    - Indexation spatiale de la base, et rajoute de colonne directemnet avec une unique requête SQL (+ éventuellement ligne python pour schéma.)
    - Revue possible avec Marouane, des quelques fonctionnalités essentielles. 
    - Idée d'avoir une base de travail, qui peut être copiée ensuite par des utilisateurs dans un second temps, pour usage et sampling.
