# Extraction de rapport budgétaire
Convertit les tableaux d'un rapport budgétaire de collectivité depuis le format PDF vers le format CSV.
Le logiciel est écrit en python.

# Installation
Liste des dépendances:
- pandas et numpy
- jpype1
- tabula-py

1. Installer jpype1 et tabula-py
```
${HOME}/venv/bin/pip install jpype1
${HOME}/venv/bin/pip install tabula-py
```

2. Cloner les fichiers dans un répertoire
```
git clone https://github.com/agardelein/budrepconvert
```

# Utilisation
La conversion du fichier source s'effectue principalement en deux étapes:
1. Préparer le fichier de configuration
2. Exécution du programme

## Préparation du fichier de configuration
La section `[general]` doit indiquer le nom du fichier source et la liste des tables à convertir.

Pour chaque table il faut procéder de manière itérative:
1. Définir les paramètres de base: le numéro de page `pages` et le numéro de la table à convertir `table_number`. En cas de tableau réparti sur plusieurs pages, indiquer sur quel axe effectuer la concaténation avec `axis`.
2. Estimer le nombre de lignes de l'en-tête `header_lines`
3. Spécifier `verbose = true`
4. Exécuter le programme (voir ci-dessous), avec `-r` la première fois.
5. Analyser le résultat de lecture (`after read_data`) et ajuster les paramètres de conversion (`labels`, `move_labels`, `rebuild_data`, etc.)
6. Retourner au point 5 jusqu'à obtenir un résultat acceptable, sans l'option `-r`

## Exécution du programme
La ligne de commande est:
```
${HOME}/venv/bin/python3 br.py
```

# Processus d'analyse
## Analyse pour une page unique
Les étapes sont:
1. Lecture de la table et 
2. Conversion de l'entête
   a. Masquage des cellules indiquées
   b. Fusion des cellules d'entête et suppression des notes (ex. `(4) (5)`)
   c. Déplacement des labels indiqués
   d. Rectification des labels indiqués
   e. Ajout des colonnes supplémentaires si besoin
   f. Séparation des données incluses dans la première colonne si besoin
   g. Suppression des colonnes inutiles
3. Fusion des lignes multiples
4. Extraction des numéros de chapitre s'ils sont fusionnés dans la première colonne avec leur nom
5. Suppression des notes (ex. `(4) (5)`) des noms de chapitre
6. Rectification des données
7. Conversion de la première colonne en index
8. Conversion des données du format texte au format flottant.

## Analyse pour une page multiple
Pour chacune des pages:
1. Lire la page comme une page unique (voir ci-dessus)
2. Concaténer le résultat aux autres pages
