![](/assets/logo.svg)

# jsonplusplus

[![PyPI version](https://badge.fury.io/py/jsonplusplus.svg)](https://badge.fury.io/py/jsonplusplus)
[![Python versions](https://img.shields.io/pypi/pyversions/jsonplusplus.svg)](https://pypi.org/project/jsonplusplus/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://img.shields.io/github/actions/workflow/status/Nathan-Josue/jsonplusplus/workflow.yml)](https://github.com/Nathan-Josue/jsonplusplus/actions)

**Un format de données JSON colonné, compressé et optimisé pour la vitesse et le stockage.**

`jsonplusplus` est une bibliothèque Python qui introduit le format **JONX (JSON++)**, un format binaire optimisé conçu pour stocker et manipuler efficacement de grandes quantités de données JSON. Parfait pour l'analytique, le machine learning et les datasets volumineux.

---

## 🎉 Nouveautés Version 2.0.0

### Extension massive du système de types

La version 2.0.0 apporte une **refonte complète de la détection de types** avec **21 types supportés** (contre 7 dans la v1.0), permettant une optimisation encore plus fine de la compression et du stockage :

#### 📊 Nouveaux types numériques
- **Entiers étendus** : int8, int64, uint8, uint16, uint32, uint64 (en plus de int16, int32)
- **Flottants étendus** : float64 (en plus de float16, float32)
- **Optimisation automatique** : Détection de la plage optimale (ex: [0-255] → uint8 au lieu de int32)
- **Réduction de taille** : Jusqu'à 75% d'économie pour les petites valeurs (uint8 vs int32)

#### 🕐 Support des types temporels
- **date** : Format ISO 8601 (YYYY-MM-DD)
- **datetime** : Format ISO 8601 avec heure
- **timestamp_ms** : Timestamp Unix en millisecondes
- **Index automatiques** : Recherches min/max O(1) sur les dates

#### 🔧 Types spécialisés intelligents
- **uuid** : Détection automatique des UUID
- **enum** : Optimisation par dictionnaire pour ≤256 valeurs uniques
- **string_dict** : Compression par dictionnaire pour ≤30% de valeurs uniques
- **binary** : Support natif des données binaires (bytes, bytearray)

#### ✨ Support nullable
- **nullable<T>** : Tous les types supportent maintenant les valeurs `null`
- **Détection automatique** : `[None, 1, 2]` → `nullable<uint8>`

### Améliorations techniques

- **Refactorisation du code** : Séparation de la logique métier en modules utils
- **Meilleure maintenabilité** : Code modulaire et testé
- **Performance** : Détection de types optimisée avec analyse intelligente
- **CLI étendu** : Toutes les commandes supportent les nouveaux types

### Migration depuis v1.x

✅ **100% rétrocompatible** : Aucune modification de code nécessaire !
Les fichiers JONX v1.x restent lisibles, et l'encodage utilise automatiquement les nouveaux types.

### Exemple comparatif v1.0 vs v2.0

```python
# Même code, résultats différents selon la version
data = [
    {"id": 100, "uuid": "550e8400-e29b-41d4-a716-446655440000", "created": "2024-12-30"},
    {"id": 200, "uuid": "6ba7b810-9dad-11d1-80b4-00c04fd430c8", "created": "2024-12-31"}
]

# Version 1.0 détectait :
# - id: int16 (optimisé)
# - uuid: str (texte compressé)
# - created: str (texte compressé)

# Version 2.0 détecte :
# - id: uint8 (75% plus compact que int16!)
# - uuid: uuid (détection automatique)
# - created: date (avec index automatique pour recherches rapides)
```

**Résultat** : Fichiers **plus petits** et **recherches plus rapides** sans changer une ligne de code !

---

## Présentation du format

### Qu'est-ce que JSON++ / JONX ?

**JONX (JSON++)** est un format de fichier binaire qui transforme des données JSON en un format **colonné** (columnar storage) avec compression **Zstandard** et auto-détection des types. Contrairement au JSON traditionnel qui stocke les données ligne par ligne, JONX organise les données en colonnes contiguës, permettant une compression supérieure et des accès sélectifs ultra-rapides.

### Comparaison avec JSON traditionnel

| Caractéristique | JSON traditionnel | JONX (JSON++) |
|----------------|------------------|---------------|
| **Format** | Texte (UTF-8) | Binaire optimisé |
| **Compression** | Aucune (ou gzip) | Zstandard (niveau 7) |
| **Stockage** | Ligne par ligne | Colonnes contiguës |
| **Types** | Tous en texte | Auto-détection (13 types numériques + 8 types spécialisés + nullable) |
| **Index** | Aucun | Index triés automatiques pour types numériques et temporels |
| **Lecture sélective** | Non | Oui (décompression à la demande) |
| **Performance** | Lente (parsing) | Ultra-rapide (orjson + binaire) |

### Points forts

- **Compression Zstandard** : Réduction de taille jusqu'à 80% selon les données
- **Stockage en colonnes** : Meilleure compression pour données tabulaires
- **Auto-détection avancée des types** : 21 types supportés
  - **Numériques** : int8, int16, int32, int64, uint8, uint16, uint32, uint64, float16, float32, float64
  - **Temporels** : date, datetime, timestamp_ms
  - **Spécialisés** : uuid, enum, string_dict, binary
  - **Autres** : bool, str, json
  - **Support nullable** : nullable<T> pour tous les types
- **Index optimisés** : Recherches min/max ultra-rapides sur colonnes numériques et temporelles
- **Encodage/décodage rapide** : Utilise `orjson` pour des performances maximales
- **Chargement sélectif** : Décompression à la demande = moins de RAM
- **Compatible Python natif** : Aucune dépendance externe lourde

---

## 📦 Installation

```bash
pip install jsonplusplus
```

**Dépendances requises :**
- Python >= 3.8
- `orjson>=3.9.0` - Parser JSON ultra-rapide
- `zstandard>=0.21.0` - Compression Zstandard
- `numpy>=1.20.0` - Support float16

---

## 💻 Fonctionnalités principales

### Fonctions d'encodage

- **`jonx_encode(json_path, jonx_path)`** : Convertit un fichier JSON en fichier JONX
- **`encode_to_bytes(json_data)`** : Encode des données JSON (liste d'objets) en bytes JONX

### Fonctions de décodage

- **`decode_from_bytes(byte_data)`** : Décode des bytes JONX et retourne un dictionnaire avec les données JSON reconstruites

### Classe JONXFile

- **`JONXFile(path)`** : Charge un fichier JONX pour accès colonne par colonne
  - **`get_column(field_name)`** : Récupère une colonne décompressée
  - **`find_min(field_name, use_index=False)`** : Trouve la valeur minimale (avec support d'index)
  - Propriétés : `fields`, `types`, `indexes`

---

## 📚 Référence complète des opérations

### 🔧 Opérations d'encodage (JSON → JONX)

#### `jonx_encode(json_path, jonx_path)`

Convertit un fichier JSON en fichier JONX.

**Paramètres :**
- `json_path` (str) : Chemin vers le fichier JSON source
- `jonx_path` (str) : Chemin vers le fichier JONX de destination

**Exemple :**
```python
from jsonplusplus import jonx_encode

jonx_encode("data.json", "data.jonx")
```

#### `encode_to_bytes(json_data)`

Encode des données JSON en mémoire en bytes JONX.

**Paramètres :**
- `json_data` (list) : Liste d'objets JSON (tous les objets doivent avoir les mêmes clés)

**Retourne :**
- `bytes` : Données JONX encodées

**Exemple :**
```python
from jsonplusplus import encode_to_bytes

data = [
        {"id": 1, "name": "Alice"}, 
        {"id": 2, "name": "Bob"}
       ]
jonx_bytes = encode_to_bytes(data)
```

---

### 🔍 Opérations de décodage (JONX → JSON)

#### `decode_from_bytes(data: bytes) -> dict`

Décode des bytes JONX et retourne un dictionnaire avec les données reconstruites.

**Paramètres :**
- `data` (bytes) : Données JONX à décoder

**Retourne :**
- `dict` avec les clés suivantes :
  - `version` (int) : Version du format JONX
  - `fields` (list) : Liste des noms de colonnes
  - `types` (dict) : Dictionnaire des types par colonne
  - `num_rows` (int) : Nombre de lignes
  - `json_data` (list) : Données JSON reconstruites (liste d'objets)

**Exemple :**
```python
from jsonplusplus import decode_from_bytes

with open("data.jonx", "rb") as f:
    result = decode_from_bytes(f.read())

print(result["json_data"])  # Liste d'objets JSON
print(result["fields"])     # ["id", "name", ...]
print(result["types"])      # {"id": "int32", "name": "str", ...}
```

---

### 📂 Classe JONXFile

La classe `JONXFile` permet un accès optimisé aux fichiers JONX avec chargement paresseux des colonnes.

#### Constructeur

```python
JONXFile(path: str)
```

**Paramètres :**
- `path` (str) : Chemin vers le fichier JONX

**Propriétés disponibles :**
- `fields` (list) : Liste des noms de colonnes disponibles
- `types` (dict) : Dictionnaire des types par colonne
- `indexes` (dict) : Dictionnaire des index disponibles (clés = noms de colonnes numériques)

#### Méthodes d'accès aux données

##### `get_column(field_name: str) -> list`

Récupère une colonne décompressée. La décompression se fait à la demande (lazy loading).

**Paramètres :**
- `field_name` (str) : Nom de la colonne à récupérer

**Retourne :**
- `list` : Liste des valeurs de la colonne

**Exemple :**
```python
file = JONXFile("data.jonx")
prices = file.get_column("price")  # Décompression à la demande
```

##### `get_columns(field_names: list) -> dict`

Récupère plusieurs colonnes en une seule opération.

**Paramètres :**
- `field_names` (list) : Liste des noms de colonnes à récupérer

**Retourne :**
- `dict` : Dictionnaire {nom_colonne: [valeurs]}

**Exemple :**
```python
file = JONXFile("data.jonx")
columns = file.get_columns(["id", "name", "price"])
# Retourne: {"id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"], "price": [100, 200, 300]}
```

#### Méthodes de recherche

##### `find_min(field: str, column=None, use_index=False) -> any`

Trouve la valeur minimale d'une colonne.

**Paramètres :**
- `field` (str) : Nom de la colonne
- `column` (list, optionnel) : Colonne pré-chargée (récupérée automatiquement si None)
- `use_index` (bool) : Utiliser l'index pour une recherche O(1) (recommandé pour colonnes numériques)

**Retourne :**
- Valeur minimale de la colonne

**Exemple :**
```python
file = JONXFile("data.jonx")
min_price = file.find_min("price", use_index=True)  # Ultra-rapide avec index
```

##### `find_max(field: str, column=None, use_index=False) -> any`

Trouve la valeur maximale d'une colonne.

**Paramètres :**
- `field` (str) : Nom de la colonne
- `column` (list, optionnel) : Colonne pré-chargée (récupérée automatiquement si None)
- `use_index` (bool) : Utiliser l'index pour une recherche O(1) (recommandé pour colonnes numériques)

**Retourne :**
- Valeur maximale de la colonne

**Exemple :**
```python
file = JONXFile("data.jonx")
max_price = file.find_max("price", use_index=True)  # Ultra-rapide avec index
```

#### Méthodes d'agrégation

##### `sum(field: str, column=None) -> number`

Calcule la somme d'une colonne numérique.

**Paramètres :**
- `field` (str) : Nom de la colonne
- `column` (list, optionnel) : Colonne pré-chargée (récupérée automatiquement si None)

**Retourne :**
- Somme des valeurs de la colonne

**Lève :**
- `TypeError` : Si la colonne n'est pas numérique

**Exemple :**
```python
file = JONXFile("data.jonx")
total_sales = file.sum("sales")
```

##### `avg(field: str, column=None) -> float`

Calcule la moyenne d'une colonne numérique.

**Paramètres :**
- `field` (str) : Nom de la colonne
- `column` (list, optionnel) : Colonne pré-chargée (récupérée automatiquement si None)

**Retourne :**
- Moyenne des valeurs de la colonne

**Lève :**
- `TypeError` : Si la colonne n'est pas numérique
- `ValueError` : Si la colonne est vide

**Exemple :**
```python
file = JONXFile("data.jonx")
avg_price = file.avg("price")
```

##### `count(field: str = None) -> int`

Compte le nombre d'éléments dans une colonne ou le nombre total de lignes.

**Paramètres :**
- `field` (str, optionnel) : Nom de la colonne (si None, retourne le nombre total de lignes)

**Retourne :**
- Nombre d'éléments dans la colonne ou nombre total de lignes

**Exemple :**
```python
file = JONXFile("data.jonx")
total_rows = file.count()        # Nombre total de lignes
price_count = file.count("price")  # Nombre d'éléments dans la colonne price
```

#### Méthodes utilitaires

##### `info() -> dict`

Retourne un dictionnaire avec toutes les métadonnées du fichier JONX.

**Retourne :**
- `dict` avec les clés suivantes :
  - `path` (str) : Chemin du fichier
  - `version` (int) : Version du format JONX
  - `num_rows` (int) : Nombre de lignes
  - `num_columns` (int) : Nombre de colonnes
  - `fields` (list) : Liste des noms de colonnes
  - `types` (dict) : Dictionnaire des types par colonne
  - `indexes` (list) : Liste des colonnes avec index
  - `file_size` (int) : Taille du fichier en bytes

**Exemple :**
```python
file = JONXFile("data.jonx")
metadata = file.info()
print(f"Fichier: {metadata['path']}")
print(f"Lignes: {metadata['num_rows']}")
print(f"Colonnes: {metadata['num_columns']}")
print(f"Taille: {metadata['file_size']} bytes")
```

##### `has_index(field: str) -> bool`

Vérifie si une colonne a un index disponible.

**Paramètres :**
- `field` (str) : Nom de la colonne à vérifier

**Retourne :**
- `bool` : True si la colonne a un index, False sinon

**Raises :**
- `JONXValidationError` : Si la colonne n'existe pas

**Exemple :**
```python
file = JONXFile("data.jonx")
if file.has_index("price"):
    print("La colonne 'price' a un index")
```

##### `is_numeric(field: str) -> bool`

Vérifie si une colonne est de type numérique.

**Paramètres :**
- `field` (str) : Nom de la colonne à vérifier

**Retourne :**
- `bool` : True si la colonne est numérique, False sinon

**Raises :**
- `JONXValidationError` : Si la colonne n'existe pas

**Exemple :**
```python
file = JONXFile("data.jonx")
if file.is_numeric("price"):
    total = file.sum("price")
```

##### `check_schema() -> dict`

Vérifie la cohérence du schéma du fichier JONX.

**Retourne :**
- `dict` avec les clés suivantes :
  - `valid` (bool) : True si le schéma est valide
  - `errors` (list) : Liste des erreurs trouvées
  - `warnings` (list) : Liste des avertissements

**Exemple :**
```python
file = JONXFile("data.jonx")
schema_check = file.check_schema()
if not schema_check["valid"]:
    print("Erreurs de schéma:", schema_check["errors"])
```

##### `validate() -> dict`

Valide l'intégrité complète du fichier JONX. Effectue une validation approfondie en vérifiant le schéma, l'intégrité des données, et en tentant de décompresser toutes les colonnes.

**Retourne :**
- `dict` avec les clés suivantes :
  - `valid` (bool) : True si le fichier est valide
  - `errors` (list) : Liste des erreurs trouvées
  - `warnings` (list) : Liste des avertissements

**Raises :**
- `JONXFileError` : Si le fichier ne peut pas être lu
- `JONXDecodeError` : Si le fichier est corrompu

**Exemple :**
```python
file = JONXFile("data.jonx")
validation = file.validate()
if validation["valid"]:
    print("✅ Fichier valide")
else:
    print("❌ Erreurs:", validation["errors"])
if validation["warnings"]:
    print("⚠️  Avertissements:", validation["warnings"])
```

---

### 📊 Tableau récapitulatif des opérations

| Opération | Type | Description | Performance |
|-----------|------|-------------|-------------|
| `jonx_encode()` | Encodage | Convertit fichier JSON → JONX | O(n) |
| `encode_to_bytes()` | Encodage | Encode données JSON → bytes JONX | O(n) |
| `decode_from_bytes()` | Décodage | Décode bytes JONX → JSON complet | O(n) |
| `JONXFile()` | Chargement | Charge fichier JONX (lazy) | O(1) |
| `get_column()` | Accès | Récupère une colonne (décompression à la demande) | O(n) |
| `get_columns()` | Accès | Récupère plusieurs colonnes | O(n×m) |
| `find_min()` | Recherche | Valeur minimale (avec index = O(1)) | O(1) avec index, O(n) sans |
| `find_max()` | Recherche | Valeur maximale (avec index = O(1)) | O(1) avec index, O(n) sans |
| `sum()` | Agrégation | Somme d'une colonne numérique | O(n) |
| `avg()` | Agrégation | Moyenne d'une colonne numérique | O(n) |
| `count()` | Agrégation | Nombre d'éléments | O(1) |
| `info()` | Utilitaire | Métadonnées complètes du fichier | O(1) |
| `has_index()` | Utilitaire | Vérifie si une colonne a un index | O(1) |
| `is_numeric()` | Utilitaire | Vérifie si une colonne est numérique | O(1) |
| `check_schema()` | Utilitaire | Vérifie la cohérence du schéma | O(n) |
| `validate()` | Utilitaire | Valide l'intégrité complète | O(n) |

**Légende :**
- `n` = nombre de lignes
- `m` = nombre de colonnes à récupérer

---

## 🖥️ Interface en ligne de commande (CLI)

`jsonplusplus` inclut une interface en ligne de commande complète pour convertir, inspecter et interroger les fichiers JONX.

### Installation

Après installation avec `pip install jsonplusplus`, la commande `jsonplusplus` (ou `jonx`) est disponible dans votre terminal.

### Commandes disponibles

#### `encode` - Encoder JSON → JONX

```bash
# Encoder un fichier JSON
jsonplusplus encode data.json -o data.jonx

# Ou sans spécifier la sortie (génère automatiquement data.jonx)
jsonplusplus encode data.json
```

**Options :**
- `input` : Fichier JSON d'entrée (requis)
- `-o, --output` : Fichier JONX de sortie (optionnel, généré automatiquement si omis)

**Exemple de sortie :**
```
📦 Encodage de 'data.json' vers 'data.jonx'...
✅ JONX créé : 1000 lignes, 5 colonnes
✅ Encodage réussi!
   Taille originale: 125,340 bytes
   Taille JONX: 45,230 bytes
   Compression: 63.9%
```

#### `decode` - Décoder JONX → JSON

```bash
# Décoder un fichier JONX
jsonplusplus decode data.jonx -o data.json

# Ou sans spécifier la sortie (génère automatiquement data.json)
jsonplusplus decode data.jonx
```

**Options :**
- `input` : Fichier JONX d'entrée (requis)
- `-o, --output` : Fichier JSON de sortie (optionnel, généré automatiquement si omis)

**Exemple de sortie :**
```
📦 Décodage de 'data.jonx' vers 'data.json'...
✅ Décodage réussi!
   Version: 1
   Lignes: 1000
   Colonnes: 5
   Fichier créé: data.json
```

#### `info` - Afficher les informations

```bash
jsonplusplus info data.jonx
```

Affiche toutes les métadonnées du fichier JONX.

**Exemple de sortie :**
```
📊 Informations sur 'data.jonx':
============================================================
Chemin:           data.jonx
Version:          1
Nombre de lignes: 1,000
Nombre de colonnes: 5
Taille du fichier: 45,230 bytes

Colonnes (5):
  [✓] id                   (int16)
  [ ] name                 (str)
  [✓] age                  (int16)
  [✓] salary               (float16)
  [ ] active               (bool)

Index disponibles (3):
  - id
  - age
  - salary
```

#### `validate` - Valider un fichier JONX

```bash
jsonplusplus validate data.jonx
```

Valide l'intégrité complète du fichier JONX.

**Exemple de sortie :**
```
🔍 Validation de 'data.jonx'...
✅ Fichier valide!
```

#### `query` - Interroger un fichier JONX

```bash
# Trouver la valeur minimale
jsonplusplus query data.jonx price --min

# Trouver la valeur maximale
jsonplusplus query data.jonx age --max --use-index

# Calculer la somme
jsonplusplus query data.jonx salary --sum

# Calculer la moyenne
jsonplusplus query data.jonx salary --avg

# Compter les éléments
jsonplusplus query data.jonx id --count
```

**Options :**
- `file` : Fichier JONX (requis)
- `column` : Nom de la colonne (requis)
- `--min` : Trouver la valeur minimale
- `--max` : Trouver la valeur maximale
- `--sum` : Calculer la somme (colonne numérique uniquement)
- `--avg` : Calculer la moyenne (colonne numérique uniquement)
- `--count` : Compter les éléments
- `--use-index` : Utiliser l'index pour les opérations min/max (plus rapide)

**Exemples de sortie :**
```
Minimum de 'price': 10.5
Maximum de 'age': 65
Somme de 'salary': 262016.0
Moyenne de 'salary': 52403.2
Nombre d'éléments dans 'id': 1000
```

### Aide

Pour voir toutes les commandes disponibles :

```bash
jsonplusplus --help
```

Pour voir l'aide d'une commande spécifique :

```bash
jsonplusplus encode --help
jsonplusplus query --help
```

### Utilisation en tant que module Python

Vous pouvez aussi utiliser le CLI via Python :

```bash
python -m jsonplusplus encode data.json
python -m jsonplusplus info data.jonx
```

#### `view` - Visualiseur GUI

Ouvre une application desktop moderne pour visualiser les fichiers JONX.

```bash
# Ouvrir le visualiseur
jsonplusplus view

# Ouvrir directement un fichier
jsonplusplus view data.jonx

# Ou utiliser la commande dédiée
jonx-viewer data.jonx
```

**Fonctionnalités du visualiseur :**
- Interface moderne avec mode sombre/clair
- Tableau interactif avec pagination
- Recherche en temps réel
- Métadonnées et statistiques
- Export CSV/JSON
- Statistiques automatiques (min, max, avg)

**Installation du support GUI :**
```bash
pip install jsonplusplus[gui]
# Ou
pip install customtkinter
```

Voir [VIEWER_GUI.md](VIEWER_GUI.md) pour la documentation complète du visualiseur.

---

## 📖 Exemples

### Exemple rapide

```python
from jsonplusplus import jonx_encode, decode_from_bytes

# Encoder un fichier JSON en JONX
jonx_encode("data.json", "data.jonx")

# Décoder depuis bytes
with open("data.jonx", "rb") as f:
    result = decode_from_bytes(f.read())

print(result["json_data"][0])
print(f"Colonnes: {result['fields']}")
print(f"Types: {result['types']}")
```

### Exemple avancé avec JONXFile

```python
from jsonplusplus import JONXFile

# Charger un fichier JONX
file = JONXFile("data.jonx")

# Accéder aux métadonnées
print(f"Colonnes disponibles: {file.fields}")
print(f"Types détectés: {file.types}")
print(f"Index disponibles: {list(file.indexes.keys())}")

# Récupérer une colonne spécifique (décompression à la demande)
ages = file.get_column("age")
prices = file.get_column("price")

# Récupérer plusieurs colonnes en une fois
columns = file.get_columns(["id", "name", "price"])

# Utiliser les index pour des recherches ultra-rapides
min_age = file.find_min("age", use_index=True)
max_price = file.find_max("price", use_index=True)

# Opérations d'agrégation
total_sales = file.sum("sales")
avg_price = file.avg("price")
num_rows = file.count()

print(f"Âge minimum: {min_age}")
print(f"Prix maximum: {max_price}")
print(f"Total ventes: {total_sales}")
print(f"Prix moyen: {avg_price}")
print(f"Nombre de lignes: {num_rows}")

# Reconstruire le JSON complet si nécessaire
json_data = []
num_rows = len(ages)
for i in range(num_rows):
    obj = {field: file.get_column(field)[i] for field in file.fields}
    json_data.append(obj)
```

### Exemple avec encode_to_bytes

```python
from jsonplusplus import encode_to_bytes, decode_from_bytes

# Données JSON en mémoire
data = [
    {"id": 1, "name": "Alice", "age": 30, "salary": 50000.5, "active": True},
    {"id": 2, "name": "Bob", "age": 25, "salary": 45000.0, "active": False},
    {"id": 3, "name": "Charlie", "age": 35, "salary": 60000.75, "active": True}
]

# Encoder en bytes JONX
jonx_bytes = encode_to_bytes(data)

# Sauvegarder ou transmettre
with open("output.jonx", "wb") as f:
    f.write(jonx_bytes)

# Décoder plus tard
result = decode_from_bytes(jonx_bytes)
print(f"Encodé {result['num_rows']} lignes avec {len(result['fields'])} colonnes")
```

---

## 🏗️ Structure interne du format JONX

Le format JONX est structuré de manière séquentielle pour permettre une lecture efficace :

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER (8 bytes)                                             │
├─────────────────────────────────────────────────────────────┤
│ Signature: "JONX" (4 bytes)                                 │
│ Version: uint32 (4 bytes)                                    │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ SCHÉMA COMPRESSÉ                                             │
├─────────────────────────────────────────────────────────────┤
│ Taille: uint32 (4 bytes)                                     │
│ Données compressées (zstd): {fields: [...], types: {...}}   │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ COLONNES COMPRESSÉES (pour chaque colonne)                   │
├─────────────────────────────────────────────────────────────┤
│ Taille: uint32 (4 bytes)                                     │
│ Données compressées (zstd): colonne binaire ou JSON          │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ INDEX COMPRESSÉS (optionnels)                                │
├─────────────────────────────────────────────────────────────┤
│ Nombre d'index: uint32 (4 bytes)                             │
│ Pour chaque index:                                           │
│   ├── Taille du nom: uint32 (4 bytes)                        │
│   ├── Nom du champ (UTF-8)                                   │
│   ├── Taille de l'index: uint32 (4 bytes)                    │
│   └── Index compressé (zstd): indices triés                  │
└─────────────────────────────────────────────────────────────┘
```

### Types de données supportés

#### Types numériques entiers

| Type | Description | Plage | Stockage |
|------|-------------|-------|----------|
| `int8` | Entiers signés 8 bits | -128 à 127 | Binaire (1 byte/valeur) |
| `int16` | Entiers signés 16 bits | -32768 à 32767 | Binaire (2 bytes/valeur) |
| `int32` | Entiers signés 32 bits | -2³¹ à 2³¹-1 | Binaire (4 bytes/valeur) |
| `int64` | Entiers signés 64 bits | -2⁶³ à 2⁶³-1 | Binaire (8 bytes/valeur) |
| `uint8` | Entiers non signés 8 bits | 0 à 255 | Binaire (1 byte/valeur) |
| `uint16` | Entiers non signés 16 bits | 0 à 65535 | Binaire (2 bytes/valeur) |
| `uint32` | Entiers non signés 32 bits | 0 à 2³²-1 | Binaire (4 bytes/valeur) |
| `uint64` | Entiers non signés 64 bits | 0 à 2⁶⁴-1 | Binaire (8 bytes/valeur) |

#### Types numériques flottants

| Type | Description | Précision | Stockage |
|------|-------------|-----------|----------|
| `float16` | Flottants demi-précision (IEEE 754) | ~3 décimales | Binaire (2 bytes/valeur) |
| `float32` | Flottants simple précision (IEEE 754) | ~7 décimales | Binaire (4 bytes/valeur) |
| `float64` | Flottants double précision (IEEE 754) | ~15 décimales | Binaire (8 bytes/valeur) |

#### Types temporels

| Type | Description | Format | Stockage |
|------|-------------|--------|----------|
| `date` | Date (YYYY-MM-DD) | ISO 8601 | JSON compressé (zstd) |
| `datetime` | Date et heure | ISO 8601 | JSON compressé (zstd) |
| `timestamp_ms` | Timestamp en millisecondes | Entier (epoch) | Binaire (8 bytes/valeur) |

#### Types spécialisés

| Type | Description | Stockage |
|------|-------------|----------|
| `uuid` | UUID (Universally Unique Identifier) | JSON compressé (zstd) |
| `enum` | Énumération (≤256 valeurs uniques) | JSON compressé (zstd) avec dictionnaire |
| `string_dict` | Chaînes avec forte répétition (≤30% uniques) | JSON compressé (zstd) avec dictionnaire |
| `binary` | Données binaires (bytes, bytearray) | JSON compressé (zstd) |

#### Autres types

| Type | Description | Stockage |
|------|-------------|----------|
| `bool` | Booléens | Binaire (1 byte/valeur) |
| `str` | Chaînes de caractères | JSON compressé (zstd) |
| `json` | Objets complexes (fallback) | JSON compressé (zstd) |

#### Support nullable

Tous les types peuvent être encapsulés dans `nullable<T>` pour supporter les valeurs `null` :
- `nullable<int32>` : Entiers 32 bits avec support null
- `nullable<float64>` : Flottants 64 bits avec support null
- `nullable<uuid>` : UUID avec support null
- etc.

### Auto-détection des types

La bibliothèque détecte automatiquement le type optimal pour chaque colonne en utilisant un algorithme intelligent :

#### Détection des types numériques entiers

L'algorithme détecte la plage de valeurs et choisit le type le plus compact :
- **Valeurs positives uniquement** : uint8 → uint16 → uint32 → uint64 (selon la valeur max)
- **Valeurs signées** : int8 → int16 → int32 → int64 (selon min/max)

Exemples :
- `[1, 2, 255]` → `uint8` (toutes les valeurs entre 0 et 255)
- `[-1, 10, 100]` → `int8` (toutes les valeurs entre -128 et 127)
- `[1000, 2000, 60000]` → `uint16` (toutes les valeurs entre 0 et 65535)
- `[5000000000]` → `uint64` (valeur > 2³²-1)

#### Détection des types numériques flottants

- **float16** : Valeurs dans [-65504, 65504] avec précision ≤ 3 décimales
- **float32** : Valeurs dans [-3.4e38, 3.4e38]
- **float64** : Autres valeurs flottantes

#### Détection des types spécialisés (chaînes)

Pour les colonnes de type string, l'algorithme effectue une analyse avancée :

1. **UUID** : Toutes les valeurs sont des UUID valides → `uuid`
2. **Date** : Toutes les valeurs respectent le format YYYY-MM-DD → `date`
3. **Datetime** : Toutes les valeurs sont des ISO 8601 datetime → `datetime`
4. **Enum** : ≤256 valeurs uniques → `enum` (optimisation par dictionnaire)
5. **String_dict** : ≤30% de valeurs uniques → `string_dict` (compression par dictionnaire)
6. **String** : Autres chaînes → `str` (JSON compressé)

#### Détection des autres types

- **Booléens** : Détection automatique (True/False)
- **Binary** : Détection automatique (bytes, bytearray)
- **JSON** : Fallback pour objets complexes, listes, etc.
- **Nullable** : Détection automatique si la colonne contient au moins une valeur `null`

#### Exemples d'auto-détection

```python
# Exemples de détection automatique
[1, 2, 3]                           → uint8
[-1, 10]                            → int8
[1.23, 2.1]                         → float16
[5000000000, 6000000000]            → uint64
[True, False]                       → bool
["A", "B", "A"]                     → enum (3 valeurs, dont 2 uniques)
["2024-12-30"]                      → date
["2024-12-30T12:34:56"]             → datetime
[str(uuid.uuid4()), ...]            → uuid
[None, 1, 2]                        → nullable<uint8>
[b"\x00\xFF"]                       → binary
["apple", "banana", "apple", ...]   → string_dict (si ≤30% uniques)
[{"a": 1}, {"b": 2}]                → json
```

### Index automatiques

Les colonnes **numériques et temporelles** génèrent automatiquement un **index trié** compressé, permettant des recherches min/max en O(1) après décompression de l'index.

**Types indexables :**
- **Numériques** : int8, int16, int32, int64, uint8, uint16, uint32, uint64, float16, float32, float64
- **Temporels** : date, datetime, timestamp_ms

L'index stocke les indices des valeurs triées, ce qui permet de trouver instantanément les valeurs min/max sans parcourir toute la colonne.

### Reconstruction ligne par ligne

Les données sont reconstruites ligne par ligne en combinant les colonnes décompressées selon l'ordre des champs dans le schéma.

---

##  Avantages techniques

### Compression élevée

Grâce à la combinaison du stockage en colonnes et de la compression Zstandard, JONX peut réduire la taille des fichiers de **50% à 80%** par rapport au JSON brut, selon la structure des données.

### Chargement sélectif de colonnes

Contrairement au JSON qui doit charger toutes les données, JONX permet de décompresser uniquement les colonnes nécessaires, réduisant significativement l'utilisation de la RAM pour les datasets volumineux.

### Parfait pour l'analytique et le ML

- **Analytics** : Accès rapide aux colonnes numériques avec index
- **Machine Learning** : Chargement sélectif des features nécessaires
- **Datasets volumineux** : Compression efficace et lecture paresseuse

### Compatible Python natif

Aucune dépendance externe lourde. Utilise uniquement des bibliothèques Python standard et des bindings optimisés (`orjson`, `zstandard`, `numpy`).

---

## 🗺️ Roadmap

### Version 2.0 (Actuelle) ✅

**🎉 Nouvelle version majeure avec extension massive du système de types !**

- [x] Encodage/décodage JSON ↔ JONX
- [x] **Auto-détection avancée des types** : 21 types supportés
  - [x] Types numériques entiers : int8, int16, int32, int64, uint8, uint16, uint32, uint64
  - [x] Types numériques flottants : float16, float32, float64
  - [x] Types temporels : date, datetime, timestamp_ms
  - [x] Types spécialisés : uuid, enum, string_dict, binary
  - [x] Support nullable : nullable<T> pour tous les types
- [x] Compression Zstandard (niveau 7)
- [x] Index automatiques pour colonnes numériques **et temporelles**
- [x] Classe `JONXFile` avec accès colonne par colonne (lazy loading)
- [x] Support des recherches min/max avec index O(1)
- [x] Opérations d'agrégation (sum, avg, count)
- [x] Récupération multiple de colonnes (get_columns)
- [x] Gestion d'erreurs robuste avec exceptions personnalisées
- [x] Validation complète des données (validate, check_schema)
- [x] CLI complet (encode, decode, info, query, validate, view)
- [x] Visualiseur GUI moderne (jonx-viewer)

### Version 1.0 (Précédente) 🕐

- [x] Version initiale avec support des types de base (int16, int32, float16, float32, bool, str, json)
- [x] Compression Zstandard et index automatiques
- [x] API de base pour encodage/décodage

### Version 3.0 (Planifiée) 🚧

**Fonctionnalités avancées pour les datasets volumineux :**

- [ ] Index personnalisés (multi-colonnes)
- [ ] Filtrage et projection de colonnes optimisés
- [ ] Streaming pour fichiers volumineux (lecture partielle)
- [ ] API de requête avancée (filtres, where, groupby, joins)
- [ ] Opérations d'agrégation avancées (std, median, quantiles, mode)
- [ ] Benchmarks de performance complets
- [ ] Support multi-fichiers (partitionnement)
- [ ] Compression adaptative (choix du niveau zstd par colonne)
- [ ] Métadonnées étendues (statistiques, cardinalité, histogrammes)
- [ ] Intégration native avec pandas/Polars
- [ ] Compression différentielle pour séries temporelles
- [ ] Support des transactions (ACID)

### Version 4.0 (Future) 🔮

**Vision long terme - Base de données analytique :**

- [ ] Moteur de requête SQL-like
- [ ] Partitionnement intelligent par plage de valeurs
- [ ] Index bitmap pour colonnes catégorielles
- [ ] Support des vues matérialisées
- [ ] Réplication et sharding
- [ ] API REST pour accès distant
- [ ] Connecteur JDBC/ODBC
- [ ] Support des fonctions window (ROW_NUMBER, RANK, etc.)
- [ ] Optimiseur de requêtes avec statistiques
- [ ] Support du streaming en temps réel

---

## 📄 Licence

Ce projet est sous licence **MIT**. Voir le fichier `LICENSE` pour plus de détails.

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Voici comment contribuer :

### Processus de contribution

1. **Fork** le projet
2. Créez une **branche** pour votre feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** vos changements (`git commit -m 'Add some AmazingFeature'`)
4. **Push** vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une **Pull Request**

### Règles et style

- **Formatage** : Utilisez `black` pour le formatage du code
- **Linting** : Respectez `ruff` ou `flake8` pour le linting
- **Tests** : Ajoutez des tests pour toute nouvelle fonctionnalité
- **Documentation** : Mettez à jour la documentation si nécessaire
- **Type hints** : Utilisez les annotations de type Python 3.8+

### Structure du projet

```
jsonplusplus/
├── src/
│   └── jsonplusplus/
│       ├── __init__.py
│       ├── encoder.py      # Encodage JSON → JONX
│       └── decoder.py      # Décodage JONX → JSON
├── tests/                  # Tests unitaires
├── README.md
├── pyproject.toml
└── LICENSE
```

### Signaler un bug

Ouvrez une [issue](https://github.com/Nathan-Josue/jsonplusplus/issues) avec :
- Description du bug
- Étapes pour reproduire
- Comportement attendu vs comportement actuel
- Version de Python et de la bibliothèque

---

## 👤 Auteur

**Nathan Josué**

- GitHub: [@Nathan-Josue](https://github.com/Nathan-Josue)
- Projet: [jsonplusplus](https://github.com/Nathan-Josue/jsonplusplus)

---

## 🙏 Remerciements

- `orjson` pour le parsing JSON ultra-rapide
- `zstandard` pour la compression efficace
- Inspiré par les formats colonnaires modernes (Apache Parquet, Apache Arrow)

---

## 📚 Ressources

- [Documentation complète](https://github.com/Nathan-Josue/jsonplusplus/wiki)
- [Exemples avancés](https://github.com/Nathan-Josue/jsonplusplus/examples)
- [Changelog](https://github.com/Nathan-Josue/jsonplusplus/blob/master/CHANGELOG.md)

---

**⭐ Si ce projet vous est utile, n'hésitez pas à lui donner une étoile sur GitHub !**
