# JSON++ (JONX) - Format de fichier optimisé pour JSON

JSON++ (JONX) est un format de fichier binaire optimisé pour stocker des données JSON de manière efficace. Il utilise la compression zstd et le stockage en colonnes pour réduire la taille des fichiers et améliorer les performances de lecture.

## 📋 Table des matières

- [Installation](#installation)
- [Architecture](#architecture)
- [Format JONX](#format-jonx)
- [Utilisation](#utilisation)
  - [encoder.py](#encoderpy)
  - [decoder.py](#decoderpy)
  - [server.py](#serverpy)
- [API REST](#api-rest)
- [Exemples](#exemples)

## 🚀 Installation

### Dépendances

```bash
pip install -r requirements.txt
```

Les dépendances requises sont :
- `fastapi>=0.104.0` - Framework web pour l'API
- `uvicorn[standard]>=0.24.0` - Serveur ASGI
- `orjson>=3.9.0` - Parser JSON rapide
- `zstandard>=0.21.0` - Compression zstd
- `python-multipart>=0.0.6` - Gestion des uploads de fichiers

## 🏗️ Architecture

Le projet est composé de trois modules principaux :

### `encoder.py`
Module d'encodage qui convertit des fichiers JSON en format JONX.

**Fonctions principales :**
- `detect_type(values)` : Détecte automatiquement le type d'une colonne (int32, float32, str, bool, json)
- `pack_column(values, col_type)` : Transforme une colonne en format binaire ou JSON compressé
- `jonx_encode(json_path, jonx_path)` : Fonction principale pour encoder un fichier JSON en JONX

**Caractéristiques :**
- Détection automatique des colonnes et types
- Compression zstd (niveau 3)
- Création automatique d'index pour les colonnes numériques
- Stockage en colonnes pour une meilleure compression

### `decoder.py`
Module de décodage qui lit et décompresse les fichiers JONX.

**Classe principale :**
- `JONXFile` : Classe pour charger et manipuler les fichiers JONX

**Méthodes :**
- `__init__(path)` : Charge un fichier JONX
- `get_column(field_name)` : Récupère une colonne décompressée
- `find_min(field_name, use_index=False)` : Trouve la valeur minimale d'une colonne (avec support d'index)

**Caractéristiques :**
- Chargement paresseux (colonnes compressées stockées en mémoire)
- Décompression à la demande
- Support des index pour recherches rapides

### `server.py`
Serveur FastAPI qui expose une interface web et une API REST pour convertir entre JSON et JONX.

**Routes disponibles :**
- `GET /` : Page d'accueil avec interface de conversion
- `GET /about.html` : Page À propos
- `GET /contact.html` : Page Contact
- `POST /api/decode` : Décoder un fichier JONX → JSON
- `POST /api/encode` : Encoder un fichier JSON → JONX
- `POST /api/preview` : Prévisualiser les métadonnées d'un JSON sans générer le fichier

**Fonctionnalités :**
- Interface web complète avec Monaco Editor
- Conversion bidirectionnelle JSON ↔ JONX
- Prévisualisation en temps réel
- Gestion CORS pour les requêtes cross-origin

## 📦 Format JONX

Le format JONX est structuré comme suit :

```
[Header: 8 bytes]
├── Signature: "JONX" (4 bytes)
└── Version: uint32 (4 bytes)

[Schéma compressé]
├── Taille: uint32 (4 bytes)
└── Données compressées (zstd)

[Colonnes compressées]
├── Pour chaque colonne:
│   ├── Taille: uint32 (4 bytes)
│   └── Données compressées (zstd)

[Index compressés]
├── Nombre d'index: uint32 (4 bytes)
└── Pour chaque index:
    ├── Taille du nom: uint32 (4 bytes)
    ├── Nom du champ (UTF-8)
    ├── Taille de l'index: uint32 (4 bytes)
    └── Index compressé (zstd)
```

### Types de données supportés

- **int32** : Entiers 32 bits (stockés en binaire)
- **float32** : Flottants 32 bits (stockés en binaire)
- **bool** : Booléens (stockés en binaire)
- **str** : Chaînes de caractères (JSON compressé)
- **json** : Objets complexes (JSON compressé)

### Index automatiques

Les colonnes numériques (int32, float32) génèrent automatiquement un index trié pour permettre des recherches rapides (min, max, etc.).

## 💻 Utilisation

### encoder.py

```python
from logical.encoder import jonx_encode

# Convertir un fichier JSON en JONX
jonx_encode("data/json/data.json", "json++/data_jonx.json++")
```

**Exemple de JSON d'entrée :**
```json
[
  {"id": 1, "name": "Produit 1", "price": 100, "category": "Électronique"},
  {"id": 2, "name": "Produit 2", "price": 200, "category": "Vêtements"}
]
```

**Résultat :**
- Fichier `data_jonx.json++` créé avec compression zstd
- Index automatique sur les colonnes `id` et `price`

### decoder.py

```python
from logical.decoder import JONXFile

# Charger un fichier JONX
jonx_file = JONXFile("json++/data_jonx.json++")

# Accéder à une colonne
prices = jonx_file.get_column("price")

# Trouver le prix minimum (avec index pour performance)
min_price = jonx_file.find_min("price", use_index=True)
print(f"Prix minimum: {min_price}")

# Reconstruire le JSON complet
columns = {}
for field in jonx_file.fields:
    columns[field] = jonx_file.get_column(field)

# Reconstruire les objets
num_rows = len(columns[jonx_file.fields[0]])
json_data = []
for i in range(num_rows):
    obj = {field: columns[field][i] for field in jonx_file.fields}
    json_data.append(obj)
```

**Méthodes disponibles :**
- `get_column(field_name)` : Récupère une colonne décompressée
- `find_min(field_name, use_index=False)` : Trouve la valeur minimale
- Propriétés : `fields`, `types`, `indexes`

### server.py

#### Démarrage du serveur

```bash
# Méthode 1 : Directement avec Python
python server.py

# Méthode 2 : Avec uvicorn
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

Le serveur démarre sur `http://localhost:8000`

#### Interface web

Accédez à `http://localhost:8000` pour utiliser l'interface web qui permet :
- **Décoder JONX → JSON** : Upload d'un fichier `.json++` pour voir le JSON reconstruit
- **Encoder JSON → JONX** : Upload d'un fichier `.json` pour générer un fichier `.json++`
- **Créer un format** : Éditeur JSON avec prévisualisation en temps réel des métadonnées JONX

## 🔌 API REST

### POST /api/decode

Décode un fichier JONX et retourne le JSON reconstruit.

**Requête :**
- Type : `multipart/form-data`
- Paramètre : `file` (fichier `.json++` ou `.jonx`)

**Réponse :**
```json
{
  "success": true,
  "file_name": "data_jonx.json++",
  "file_size": 273,
  "version": 1,
  "fields": ["id", "name", "price", "category"],
  "types": {"id": "int32", "name": "str", "price": "int32", "category": "str"},
  "num_rows": 2,
  "json_data": [
    {"id": 1, "name": "Produit 1", "price": 100, "category": "Électronique"},
    {"id": 2, "name": "Produit 2", "price": 200, "category": "Vêtements"}
  ]
}
```

### POST /api/encode

Encode un fichier JSON en format JONX.

**Requête :**
- Type : `multipart/form-data`
- Paramètre : `file` (fichier `.json`)

**Réponse :**
- Type : `application/octet-stream`
- Fichier téléchargeable avec extension `.json++`

### POST /api/preview

Prévisualise les métadonnées d'un JSON sans générer le fichier JONX.

**Requête :**
```json
{
  "data": [
    {"id": 1, "name": "Produit 1", "price": 100},
    {"id": 2, "name": "Produit 2", "price": 200}
  ]
}
```

**Réponse :**
```json
{
  "success": true,
  "version": 1,
  "fields": ["id", "name", "price"],
  "types": {"id": "int32", "name": "str", "price": "int32"},
  "num_rows": 2,
  "estimated_size": 273
}
```

## 📝 Exemples

### Exemple complet : Encoder puis décoder

```python
from logical.encoder import jonx_encode
from logical.decoder import JONXFile

# 1. Encoder un JSON en JONX
jonx_encode("data/json/data.json", "json++/data_jonx.json++")

# 2. Charger le fichier JONX
jonx_file = JONXFile("json++/data_jonx.json++")

# 3. Accéder aux métadonnées
print(f"Colonnes: {jonx_file.fields}")
print(f"Types: {jonx_file.types}")

# 4. Récupérer une colonne spécifique
prices = jonx_file.get_column("price")
print(f"Prix: {prices}")

# 5. Utiliser les index pour des recherches rapides
min_price = jonx_file.find_min("price", use_index=True)
print(f"Prix minimum: {min_price}")
```

### Exemple avec l'API REST

```python
import requests

# Décoder un fichier JONX
with open("json++/data_jonx.json++", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/decode",
        files={"file": f}
    )
    result = response.json()
    print(result["json_data"])

# Prévisualiser un JSON
response = requests.post(
    "http://localhost:8000/api/preview",
    json={
        "data": [
            {"id": 1, "name": "Test", "price": 100}
        ]
    }
)
print(response.json())
```

## 🎯 Avantages du format JONX

1. **Compression efficace** : Utilisation de zstd pour une compression optimale
2. **Stockage en colonnes** : Meilleure compression pour les données tabulaires
3. **Types optimisés** : Stockage binaire pour les types numériques
4. **Index automatiques** : Recherches rapides sur les colonnes numériques
5. **Lecture sélective** : Décompression à la demande des colonnes
6. **Format binaire** : Plus rapide à lire que JSON textuel

## 📄 Licence

Ce projet est fourni tel quel pour usage éducatif et de développement.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

