# Patch Catalogue Sampling

Méthodes de sous-échantillonnage (*sampling*) de patches de données pour la constitution d'un jeu de données d'apprentissages.
Les données à dispositions auront été décrites au préalable dans un "Catalogue", incluant leur emprise géographique, les histogrammes des classes de chaque patch, et des indicateurs de présences de certains objets d'intérêt (p.ex. éoliennes). Ces métadonnées serviront à échantillonner les données suivant plusieurs heuristiques, avec les cadres conceptuels suivant :

- *Uncertainty Sampling* : on souhaite sélectionner des types de scènes sur lesquelles nos modèles de segmentation sémantique actuels (cf. [myria3d](https://github.com/IGNF/myria3d)) manquent parfois de confiance, voire font des erreurs (p.ex. grands bâtiments).
- *Rééquilibrage* : on souhaite atteindre de bonnes performances sur certaines classes rares (p.ex. eau, sursol pérenne) et objets rares (p.ex. éoliennes, lignes à haute tension, chemin ferroviaires), en augmentant leur prévalence dans le jeu de données.
- *Diversity Sampling* : on souhaite couvrir la grande diversité des scènes possibles. On posera les deux hypothèses suivantes : 
    - (1) Autocorrélation spatiale des scènes : des scènes proches ont tendance à se ressembler plus que des scènes lointaines ; 
    - (2) Les histogrammes des classes de chaque patch sont un proxy (imparfait) de la nature des scènes : sous condition d'une bonne normalisation, on doit pouvoir définir une mesure de distance des scènes à partir des histogrammes de classes, et de là favoriser la diversité des scènes.

## Contenu

Un sampling se lance au moyen d'un fichier de configuration, et via les objets suivants:

- **Connector**: interface de connexion aux données: 
    - `LiPaCConnector`: connexion et requêtage de la base LiPaC (Lidar Patch Catalogue).
    - `SyntheticConnector`: création d'un GeoDataFrame synthétique, composé de tuiles répartie dans une grille arbitraire, pour effectuer des tests rapidements.
- **Sampler**: interrogent les objets `Connector` suivant la configuration pour sélectionne des tuiles (patches) par leur identifiant, et qui définissent à la volée le split train/test.
    - `TargettedSampler`: atteinte séquentielle des contraintes de prévalence pour chaque descritpteur. Répartition spatiale optimale. NB: Si usage de ce sampler en isolation, la taille du jeu de données en sortie n'est pas garantie.
    - `DiversitySampler`: couverture par Farthest Point Sampling de l'espace des descripteurs (i.e. nombre de points de certaines classes, quantilisés).
    - `SpatialSampler`: complétion aléatoire pour atteindre une taille de jeu de données cible. Répartition spatiale optimale.
    - `TripleSampler`: Succession des trois précédents samplers, commençant par `TargettedSampled`, suivi des deux autres à proportion égale.

`TripleSampler` fait un compromis entre les différentes approches. Les autres samplers de base peuvent être utilisés en isolation également.

Le processus de sampling sauvegarde un geopackage dans `outputs/{ConnectorName}/{SamplingName}-extract.gpkg`, contenant l'échantillon de tuiles avec l'ensemble des champs de la base de données initiales, ainsi qu'une variable `split` définissant le jeu de test pour un futur apprentissage.


<details>
<summary><h3>Illustration QGIS - Echantillonnage par TripleSampler</h3></summary>

- A partir de 40 dalles voisines, c'est-à-dire 16000 patches en tout, 893 patches sont échantillonnées, soit environ 6% de la zone.
- Chaque sampler apporte sa contribution (`TargettedSampler`: jaune, `DiversitySampler`: violet, `SpatialSampler`: marron)
- Les zones de bâti et d'eau sont bien représentées, conformément à la configuration de l'échantillonnage.
- Les tuiles du jeu de test sont quadrillées (zoom nécessaire). Elles sont réparties de façon homogène dans le jeu de données, et ce pour chaque sampler :
    - Spatiallement `TargettedSampler`: on couvre un maximum de dalles pour chaque critère.
    - Par les histogrammes de classes pour le `DiversitySampler`, afin que le jeu de test couvre le même espace des histogrammes que le jeu de train, mais simplement de façon moins dense.
    - Spatiallement pour le `SpatialSampler`: on couvre un maximum de dalles.

![](img/TripleSampler-example-by-sampler.png)

- Sur la dalle suivante, le `DiversitySampler` (violet) se concentre sur les panneaux solaires au sud-est. Cet exemple illustre la capacité de ce sampler à identifier des scènes atypiques pour les inclures dans le jeu de données.
- Les zones de bâti sont couverte par trois patches choisis par le `TargettedSampler` (jaune), dont une de test (quadrillage).
- Au sein d'une seule dalle, le choix du `SpatialSampler` se fait de façon aléatoire, ce qui sélectionne des zones plus naturelles et forestières (marron). 

![](img/TripleSampler-example-0954_6338-by-sampler.png)

</details>

<details>
<summary><h2>Usage</h2></summary>

### Mettre en place l'environnement virtual conda:
```bash
conda install mamba --yes -n base -c conda-forge
mamba env create -f environment.yml
```
### Lancer un échantillonnage "triple" sur des données synthétiques :
```python
conda activate pacasam
python ./src/pacasam/main.py --config_file=configs/Synthetic.yml --connector_class=SyntheticConnector --sampler_class=TripleSampler
```
### Lancer un échantillonnage sur des données réelles - base PostGIS LiPaC:

1. Créer sa configuration dans le dossier `configs` (cf. `configs/Lipac.yml`). Vérifier notamment les champs liés à la base de données PostGIS à requêter.

2. Créer un fichier `credentials.ini` avec la section `[LIDAR_PATCH_CATALOGUE]` et les champs `DB_LOGIN` et `DB_PASSWORD`, contenant les éléments de connexion à au catalogue de patch (droits en lecture nécessaires.)

3. (Optionnel) Afficher les options de sampling.
```python
python ./src/pacasam/main.py --help
```
4. Lancer le sampling.
```python
conda activate pacasam
python ./src/pacasam/main.py --config_file=lipac/Synthetic.yml
```
</details>


<details>
<summary><h2>Performances & Tests</h2></summary>

Passage à l'échelle : Tests OK avec 4M de tuiles (et ~20 variables) sur machine locale avec 7.2GB de RAM -> taille totale fait 600MB environ. Le sampling FPS se fait par parties si nécessaires (p.ex. par 100k samples successifs). 
</details>

<details>
<summary><h2> Roadmap post 20230420</h2></summary>

- Tasks:
    - [] Redéfinir frac_test_set et associés vers notion de jeu de validation.
    - [X] Enlever le comportement par défaut "critere > 0". Toujours mettre commande sql pour être explicite.
    - [] Option de télécharger une fois en un geopackage le jeu de données complet. C'est un extract (lourd) de la base, permet analyse descriptive...
    - [] Revoir ce que je veux inclure dans describe.py. Simplifier / rendre scalable ? Export du html vers pdf?
    - [] S'assurer que les logs de chaque échantillonnage s'enregistrent, et incluent en plus de stats desc / quanti sur les éléments. Eventuellement un json avec le nombre de patches concernés pour Targetted ; et pareil pour les autres sampler.

</details>


<details>
<summary><h2> Roadmap - Historique </h2></summary>

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
        - [X] Requête spatialement distribuée. Si large base (> seuil), travailler par chunk, puis redistribution eventuelle dans la sélection.
    - [X] Connecteur "données synthétique"
    - [X] Connecteur LiPaC
    - [X] *random* completion -> spatial sampling for completion.
- [X] Prise en main PGADMIN ou BDBeaver pour anticipation des opérations copie+manipulation. Idée de "version de référence" maintenue dont partent des copies / enrichissements, qui se feraient avec des requêtes simples.
- [X] API unique pour les samplers, dans run.py, avec config en argument.
- [X] Renommer criteria dans config pour préciser qu'il s'agit de targetted sampling. Le nommer par le nom de la classe !
- [X] Possibilité d'un filtre en amont sur la BD. 
    - Filtre nb_points > 50. (Mais qu'en est-il de l'eau alors ?...)
    - Filtre sur les chantier, pour exclure ou inclure certains, et créer le **jeu de test de façon exclusive**.
    - (Peut-être mise en mémoire alors de la BD filtrée, avec un connecteur type GeoDataFrame ? (Vérifier que ça scalera). -6> pas très satisfaisant, enlève l'intérêt d'une base "online" facilement inspectable.
- Optimisation :
    - [X] Config de base avec l'ensemble des indicateurs, pour tests sur 250km² et une npremière viz. 
    - [X] Spatiale Sampling par itération sur les dalles et sélection d'un patch à chaque fois.
        On peut envisager une méthode effficae où on attribue un index à chaque patch au sein de chaque dalle, et ensuite on filtre avec un seuil ? Overkill, commencer simple : on devrait sélectionner max 5 patches en conditions réelles. MAIS : les patches ne seront pas optimisés spatialement entre des dalles adjacentes, juste bien répartie par grille. Semble OK.
        - [X] Version "in memory" qui nécessite de charger id et dalle en mémoire.
    - [X] Seeds to have a reproductible dataset. Works with postgis as well?
    - [X] Diversity sampling : Sampling prenant en compte des clusters 'e.g. les deciles de chaque classe, croisés ensemble), de façon représentative, et spatialisée.
        - [X] Contrôle et paramétrisation des éléments du diversity sampling. En gros, les différents indicators à définir par des requêter sql (si différent du nom de base, cf. targets_for_TargettedSampler). Être capable de faire une unique requete sql pour remplacer l'usage de sampler.extract qui n'est pas prévue pour ça.
    - [X] Separate spatial and random samplers.
- Extraction
    - [X] Extract geopackage des métadonnées

</details>
