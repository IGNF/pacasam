# pacasam
Patch-Catalogue-Sampling: methods to sample a catalogue (e.g. PostGIS database) of data patches based on their metadata, for deep learning dataset pruning.


# Roadmap

- [ ] mise en place espace de travail
    - [X] repo github, env, connector, structure... attention aux credentials.
    - [ ] Crée un objet similaire au connector, définissant l'interface attendue, qui va créer des données synthétiques (dataframe) et le requêter.
        - [ ] Données synthétique : une liste de prévalences,  pour chaque critère binaire (pour l'instant pas de num points, on voit après car num_points -> binaire facilement avec requête ">0")
        - [ ] Les requêtes ci-après
    - [ ] Fonctionnalités de bases du connector interrogeant la BD:
        - [ ] Requêter si valeur d'un indicateur donné dépasse un seuil (Nota: doit on faire aussi seuil négatif ?)
        - [ ] Requêter si indicateur binaire est vrai (Nota: doit on faire aussi si faux ?)
        - [ ] Requêter sans contraintes d'indicateur ? Trouver astuce avec SQL...
    - Définir en pseudo code le script simple de rencontre des contraintes (cf. mon notebook), sur les données synthétiques d'abord par simplicité, avec noms de colonnes basiques.
    - run.py fait le lien entre un connector, une config, un sampler. 
        - Un sampler peut être le script basique successif, ou une black box. La sortie du sampler c'est une liste d'identifiants, ensuite utilisable pour faire un vrai extract de la base PostGIS.
    
    - Définition de l'architecture du code
        - entrée : config et contraintes sur chaque critère, unique pour le moment
        - tout le système pour requêter la BD, le plus indépendant du schéma possible (connecteur + config mdp).
        - Le système de sauvegarde du sampling = un listing des id à conserver + les géométries pour possibilité d'inspection dans QGIS --> dump direct d'une sous sélection de la base en geopackage est le plus facile à inspecter !! Dans un second temps on pensera à un booléen dans la base...
        - Bien se laisser du temps une fois la mise en place pour explorer différentes options de sampling.
    - Commencer une liste pour revue de Panini
        - Enumerable des noms de classes en français
        - correction de "nb points artefats"
        - Documentation des noms de variables et de leur définition (altitude, dénivelés) dans un xslx (Databook)
        - 

Panini - requests :
    - Passer les booléens en int pour faciliter opérations ">0". (cf. https://stackoverflow.com/a/1465432/8086033)
    