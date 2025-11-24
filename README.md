# jsonplusplus

[![PyPI version](https://badge.fury.io/py/jsonplusplus.svg)](https://badge.fury.io/py/jsonplusplus)
[![Python versions](https://img.shields.io/pypi/pyversions/jsonplusplus.svg)](https://pypi.org/project/jsonplusplus/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://img.shields.io/github/actions/workflow/status/Nathan-Josue/jsonplusplus/ci.yml?branch=master)](https://github.com/Nathan-Josue/jsonplusplus/actions)

**Un format de données JSON colonné, compressé et optimisé pour la vitesse et le stockage.**

`jsonplusplus` est une bibliothèque Python qui introduit le format **JONX (JSON++)**, un format binaire optimisé conçu pour stocker et manipuler efficacement de grandes quantités de données JSON. Parfait pour l'analytique, le machine learning et les datasets volumineux.

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
| **Types** | Tous en texte | Auto-détection (int16, int32, float16, float32, bool, str, json) |
| **Index** | Aucun | Index triés automatiques |
| **Lecture sélective** | Non | Oui (décompression à la demande) |
| **Performance** | Lente (parsing) | Ultra-rapide (orjson + binaire) |

### Points forts

- **Compression Zstandard** : Réduction de taille jusqu'à 80% selon les données
-  **Stockage en colonnes** : Meilleure compression pour données tabulaires
-  **Auto-détection des types** : int16, int32, float16, float32, bool, string, json
-  **Index optimisés** : Recherches min/max ultra-rapides sur colonnes numériques
-  **Encodage/décodage rapide** : Utilise `orjson` pour des performances maximales
-  **Chargement sélectif** : Décompression à la demande = moins de RAM
-  **Compatible Python natif** : Aucune dépendance externe lourde

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

data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
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

**Légende :**
- `n` = nombre de lignes
- `m` = nombre de colonnes à récupérer

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

| Type | Description | Stockage |
|------|-------------|----------|
| `int16` | Entiers 16 bits (-32768 à 32767) | Binaire (2 bytes/valeur) |
| `int32` | Entiers 32 bits | Binaire (4 bytes/valeur) |
| `float16` | Flottants 16 bits (IEEE 754) | Binaire (2 bytes/valeur) |
| `float32` | Flottants 32 bits (IEEE 754) | Binaire (4 bytes/valeur) |
| `bool` | Booléens | Binaire (1 byte/valeur) |
| `str` | Chaînes de caractères | JSON compressé (zstd) |
| `json` | Objets complexes | JSON compressé (zstd) |

### Auto-détection des types

La bibliothèque détecte automatiquement le type optimal pour chaque colonne :

- **Entiers** : `int16` si toutes les valeurs sont dans [-32768, 32767], sinon `int32`
- **Flottants** : `float16` si précision ≤ 3 décimales et dans la plage IEEE 754, sinon `float32`
- **Booléens** : Détectés automatiquement
- **Chaînes** : Stockées comme `str` (JSON compressé)
- **Objets complexes** : Stockés comme `json` (JSON compressé)

### Index automatiques

Les colonnes numériques (`int16`, `int32`, `float16`, `float32`) génèrent automatiquement un **index trié** compressé, permettant des recherches min/max en O(1) après décompression de l'index.

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

### Version 1.0 (Actuelle) ✅

- [x] Encodage/décodage JSON ↔ JONX
- [x] Auto-détection des types (int16, int32, float16, float32, bool, str, json)
- [x] Compression Zstandard
- [x] Index automatiques pour colonnes numériques
- [x] Classe `JONXFile` avec accès colonne par colonne
- [x] Support des recherches min/max avec index
- [x] Opérations d'agrégation (sum, avg, count)
- [x] Récupération multiple de colonnes (get_columns)

### Version 2.0 (Planifiée) 🚧

- [ ] Support des types additionnels (int8, int64, float64)
- [ ] Index personnalisés (multi-colonnes)
- [ ] Filtrage et projection de colonnes optimisés
- [ ] Support des données nulles (NULL handling)
- [ ] Streaming pour fichiers volumineux
- [ ] API de requête simple (filtres, groupby, joins)
- [ ] Opérations d'agrégation avancées (std, median, quantiles)
- [ ] Benchmarks de performance complets

### Version 3.0 (Future) 🔮

- [ ] Support multi-fichiers (partitionnement)
- [ ] Compression adaptative (choix du niveau zstd par colonne)
- [ ] Métadonnées étendues (statistiques, cardinalité)
- [ ] Intégration avec pandas/Polars
- [ ] Support des types temporels (date, datetime, timestamp)
- [ ] Compression différentielle pour séries temporelles
- [ ] API de requête avancée (base de donnée)

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
