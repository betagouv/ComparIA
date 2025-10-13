<!--
SPDX-FileCopyrightText: 2025 Pôle d'Expertise de la Régulation Numérique <contact@peren.gouv.fr>

SPDX-License-Identifier: MIT
-->

# Méthode de classement pour les modèles issus du comparateur compar:IA

## Description

Ce projet consiste en un POC permettant de calculer d'une part un classement des modèles de langue utilisés dans le comparateur public d'IA conversationnelle [compar:IA](https://comparia.beta.gouv.fr/), et d'autre part d'estimer le coût écologique de ces modèles.
Un travail sur la représentation de l'évolution des matchs au cours du temps a été effectué. Il permet de construire un graphe dynamique représentant l'évolution des matchs entre modèles dans le comparateur. Il est possible de naviguer dans une fenêtre de temps donnée pour observer quel modèle a été mis en compétition avec quel modèle, combien de fois et la proportion de matchs gagnés pour chaque modèle. Outre le traitement effectué sur les données pour construire le graphique, une interface graphique a été développée.

Ce projet est en développement et sera mis régulièrement à jour.

## Installation


```bash
# Récupération du code avec Git
git clone ${GITLAB_URL}
cd rank-comparia

# Installation des dépendances et du projet via poetry
# (poetry se chargera également de créer un environnement virtuel pour vous,
#  par défaut il sera dans le cache de poetry mais vous pouvez forcer poetry
#  à l'installer à la racine du dossier avec `POETRY_VIRTUALENVS_IN_PROJECT=1`)
poetry install
```

## Données utilisées

Les données utilisées pour ce projet sont trois jeux de données, mis à disposition par le SNUM du Ministère de la culture et disponibles sur HuggingFace :
- [ministere-culture/comparia-conversations](https://huggingface.co/datasets/ministere-culture/comparia-conversations), utilisé pour récupérer les valeurs permettant de calculer la consommation énergétique
- [ministere-culture/comparia-reactions](https://huggingface.co/datasets/ministere-culture/comparia-reactions), utilisé pour établir le classement des modèles basé sur les réactions laissées par les utilisateurs au sein des conversations
- [ministere-culture/comparia-votes](https://huggingface.co/datasets/ministere-culture/comparia-votes), utilisé pour établir le classement des modèles basé sur les votes des utilisateurs à la fin des conversations et pour constuire le graphe dynamique des matchs.


## Utilisation

Voir les notebooks dans le dossier `notebooks/` pour avoir des exemples d'utilisation.

1. Le notebook `rankers.ipynb` permet de calculer les différentes méthodes de classement des modèles. Il inclut également le calcul de score de classement pondéré par le score énergétique avec également une représentation graphique qui permet d'afficher les scores selon le poids qu'on veut donner à la donnée énergétique.
2. Le notebook `frugal.ipynb` permet de calculer en plus la consommation estimée des modèles et de construire une représentation graphique du score de classement en fonction de sa consommation.  
3. Le notebook `pipeline.ipynb` qui illustre l'utilisation de l'interface `RankingPipeline`. Il permet de paramétrer les classements qu'on veut établir, d'exporter des représentations graphiques, comparer les classements établis par les différentes méthodes. On peut également établir des classements selon les mots-clés de la colonne `Categories` du jeu de données. Les données calculées sont enregistrées dans un format `csv` dans le dossier spécifié avec le paramètre `export_path`
4. Le notebook `graph.ipynb` permet de construire les dictionnaires nécessaires à la création du graphe dynamique.

Les notebooks `frugal.ipynb` et `rankers.ipynb` sont davantage pour illustrer les fonctions implémentées. Le notebook `pipeline.ipynb` est le notebook "principal" qui permet de paramétrer les calculs des scores et l'export des graphiques associés.

Les fonctions utilisées dans les notebooks se trouvent dans `src/rank_comparia/` :
- Les méthodes de calcul de classement se trouvent dans les fichiers `elo.py`, `maximum_likelihood.py` dont `ranker.py` est la classe générique.
- Les méthodes de calcul de la consommation énergétique se trouvent dans `frugality.py`  
- Les fonctions associées à la générétation des diffférents graphiques se trouvent dans `plot.py`
- Une pipeline bout en bout est en construction dans `pipeline.py`. Elle inclut les méthodes de classement selon différents paramètres (méthode de classement, quel jeu de données à utiliser, etc.).


Les fonctions nécessaires à la construction du graphe dynamique représentant l'évolution des matchs se trouve dans le dossier `graph-frontend/`. Les fichiers de données nécessaires à la construction de ces graphes se trouvent dans `graph-fronted/files/` ; il est possible de mettre à jour ces données en générant de nouveaux fichiers avec le notebook `graph.ipynb`. Ces données seront sauvegardées dans `/data`. Les fonctions utilisées dans ce notebook se trouve dans `notebooks/utils_graph_d3.py`.



## Tests
```bash
poetry run pytest tests/
```


## Contribution

Avant de contribuer au dépôt, il est nécessaire d'initialiser les _hooks_ de _pre-commit_ :

```bash
poetry run pre-commit install
```

<!--
***** TODO[squelette] ****
Décommenter les lignes suivantes et supprimer ce bloc si vous utilisez la publication
automatique via les jobs `package-publish-project` ou `package-publish-central`
du `.gitlab-ci.yml`.
Le job package-publish-central nécessite que la variable `CENTRAL_REGISTRY_ID`
soit configurée avec l'ID du dépôt central (52).
Cette variable est déjà configurée pour tous les projets au sein du groupe PEReN.
**************************

## Deployment

La bibliothèque est automatiquement publié dans les dépôts de paquets lors de la publication d'un tag de version.
Pour être reconnu le tag doit impérativement commencer par le caractère `v`,
puis être un numéro de version valide, par exemple `v1.2.4`.
Le dépôt doit également comporter un fichier `CHANGELOG.md`,
possédant une section formaté comme suit `## v<version> (<date du commit tagué[YYYY-MM-DD]>)`,
et décrivant les changements associés à la nouvelle version.  
Exemple:
```markdown
## v1.2.4 (2024-08-31)
### Features
- PDFs support
### Bug fixes
- Fix a memory leak
```
-->

## Licence

Ce projet est sous licence MIT. Une copie intégrale du texte
de la licence se trouve dans le fichier [`LICENSES/MIT.txt`](LICENSES/MIT.txt).
