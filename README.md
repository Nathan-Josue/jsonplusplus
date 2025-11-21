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
Serveur FastAPI qui expose une API REST complète pour convertir entre JSON et JONX.

**Endpoints disponibles :**
- `GET /` : Redirection vers la documentation Swagger (`/docs`)
- `GET /health` : Vérification de santé de l'API
- `POST /api/encode` : Encoder un fichier JSON → JONX (upload fichier)
- `POST /api/encode/json` : Encoder JSON → JONX (body JSON)
- `POST /api/decode` : Décoder un fichier JONX → JSON
- `POST /api/preview` : Prévisualiser les métadonnées JONX sans générer le fichier

**Fonctionnalités :**
- API REST complète avec documentation interactive (Swagger UI et ReDoc)
- Conversion bidirectionnelle JSON ↔ JONX
- Détection automatique des types de colonnes
- Compression zstd optimisée
- Index automatiques pour colonnes numériques
- Prévisualisation des métadonnées
- Gestion CORS pour les requêtes cross-origin
- Gestion d'erreurs complète avec codes HTTP appropriés

## 📦 Format JONX|JSON++

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
from backend.logical.encoder import jonx_encode

# Convertir un fichier JSON en JONX
jonx_encode("data/json/data.json", "data/json++/data_jonx.json++")
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
from backend.logical.decoder import JONXFile

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

#### Documentation interactive

Accédez à `http://localhost:8000/docs` pour utiliser l'interface Swagger UI qui permet :
- **Tester tous les endpoints** directement depuis le navigateur
- **Voir la documentation complète** de chaque endpoint
- **Exécuter des requêtes** avec des exemples pré-remplis
- **Voir les schémas de requête/réponse** en détail

Accédez à `http://localhost:8000/redoc` pour une documentation alternative en format ReDoc.

## 🔌 API REST

L'API REST expose plusieurs endpoints pour convertir entre JSON et JONX. La documentation interactive est disponible sur `/docs` (Swagger UI) et `/redoc` (ReDoc).

### GET /health

**Vérification de santé de l'API**

Endpoint de santé pour vérifier que l'API est opérationnelle. Utile pour les systèmes de monitoring et les health checks.

**Méthode :** `GET`

**Réponse :**
```json
{
  "status": "healthy",
  "service": "JONX API",
  "version": "1.0.0"
}
```

**Exemple avec curl :**
```bash
curl http://localhost:8000/health
```

**Exemple avec Python :**
```python
import requests
response = requests.get("http://localhost:8000/health")
print(response.json())
```

---

### POST /api/encode

**Encoder JSON → JONX (upload fichier)**

Encode un fichier JSON en format JONX optimisé via upload de fichier.

**Méthode :** `POST`

**Content-Type :** `multipart/form-data`

**Paramètres :**
- `file` (requis) : Fichier JSON à encoder (doit être une liste d'objets)

**Format d'entrée :**
- Le fichier JSON doit être une liste d'objets (array)
- Tous les objets doivent avoir les mêmes clés
- Les types sont détectés automatiquement

**Réponse :**
- **Type :** `application/octet-stream`
- **Headers :** `Content-Disposition: attachment; filename="<nom>.json++"`
- **Corps :** Fichier binaire JONX téléchargeable

**Codes d'erreur :**
- `400` : Aucun fichier fourni, JSON invalide, ou liste vide
- `500` : Erreur interne lors de l'encodage

**Exemple avec curl :**
```bash
curl -X POST "http://localhost:8000/api/encode" \
     -F "file=@data.json" \
     --output output.json++
```

**Exemple avec Python :**
```python
import requests

with open("data.json", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/encode",
        files={"file": f}
    )

with open("output.json++", "wb") as out:
    out.write(response.content)
```

**Format JSON d'entrée attendu :**
```json
[
  {"id": 1, "name": "Produit 1", "price": 100.50, "active": true},
  {"id": 2, "name": "Produit 2", "price": 200.75, "active": false}
]
```

---

### POST /api/encode/json

**Encoder JSON → JONX (body JSON)**

Encode des données JSON envoyées dans le body de la requête en format JONX. Alternative à l'upload de fichier pour les données générées dynamiquement.

**Méthode :** `POST`

**Content-Type :** `application/json`

**Body :**
```json
{
  "data": [
    {"id": 1, "name": "Produit 1", "price": 100.50},
    {"id": 2, "name": "Produit 2", "price": 200.75}
  ]
}
```

**Réponse :**
- **Type :** `application/octet-stream`
- **Headers :** `Content-Disposition: attachment; filename="output.json++"`
- **Corps :** Fichier binaire JONX téléchargeable

**Codes d'erreur :**
- `400` : JSON invalide ou liste vide
- `500` : Erreur interne lors de l'encodage

**Exemple avec curl :**
```bash
curl -X POST "http://localhost:8000/api/encode/json" \
     -H "Content-Type: application/json" \
     -d '{
       "data": [
         {"id": 1, "name": "Produit 1", "price": 100.50},
         {"id": 2, "name": "Produit 2", "price": 200.75}
       ]
     }' \
     --output output.json++
```

**Exemple avec Python :**
```python
import requests

data = {
    "data": [
        {"id": 1, "name": "Produit 1", "price": 100.50, "active": True},
        {"id": 2, "name": "Produit 2", "price": 200.75, "active": False}
    ]
}

response = requests.post(
    "http://localhost:8000/api/encode/json",
    json=data
)

with open("output.json++", "wb") as f:
    f.write(response.content)
```

---

### POST /api/decode

**Décoder JONX → JSON**

Décode un fichier JONX et retourne les données JSON reconstruites avec toutes les métadonnées.

**Méthode :** `POST`

**Content-Type :** `multipart/form-data`

**Paramètres :**
- `file` (requis) : Fichier JONX à décoder (extension `.json++` ou `.jonx`)

**Réponse :**
```json
{
  "success": true,
  "file_name": "data.json++",
  "file_size": 273,
  "version": 1,
  "fields": ["id", "name", "price", "active"],
  "types": {
    "id": "int32",
    "name": "str",
    "price": "float32",
    "active": "bool"
  },
  "num_rows": 2,
  "json_data": [
    {"id": 1, "name": "Produit 1", "price": 100.50, "active": true},
    {"id": 2, "name": "Produit 2", "price": 200.75, "active": false}
  ]
}
```

**Champs de la réponse :**
- `success` : Indicateur de succès (bool)
- `file_name` : Nom du fichier uploadé (str)
- `file_size` : Taille du fichier en bytes (int)
- `version` : Version du format JONX (int)
- `fields` : Liste des noms de colonnes (list)
- `types` : Dictionnaire des types par colonne (dict)
- `num_rows` : Nombre de lignes de données (int)
- `json_data` : Données JSON reconstruites (list)

**Codes d'erreur :**
- `400` : Aucun fichier fourni ou fichier JONX invalide
- `500` : Erreur interne lors du décodage

**Exemple avec curl :**
```bash
curl -X POST "http://localhost:8000/api/decode" \
     -F "file=@data.json++"
```

**Exemple avec Python :**
```python
import requests
import json

with open("data.json++", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/decode",
        files={"file": f}
    )

result = response.json()
print(f"Colonnes: {result['fields']}")
print(f"Types: {result['types']}")
print(f"Nombre de lignes: {result['num_rows']}")
print(f"Données: {json.dumps(result['json_data'], indent=2)}")
```

---

### POST /api/preview

**Prévisualiser les métadonnées JONX**

Prévisualise les métadonnées et estime la taille d'un fichier JONX sans le générer. Utile pour valider la structure des données avant l'encodage.

**Méthode :** `POST`

**Content-Type :** `application/json`

**Body :**
```json
{
  "data": [
    {"id": 1, "name": "Produit 1", "price": 100.50, "active": true},
    {"id": 2, "name": "Produit 2", "price": 200.75, "active": false}
  ]
}
```

**Réponse :**
```json
{
  "success": true,
  "version": 1,
  "fields": ["id", "name", "price", "active"],
  "types": {
    "id": "int32",
    "name": "str",
    "price": "float32",
    "active": "bool"
  },
  "num_rows": 2,
  "estimated_size": 273
}
```

**Champs de la réponse :**
- `success` : Indicateur de succès (bool)
- `version` : Version du format JONX qui serait utilisée (int)
- `fields` : Liste des colonnes détectées (list)
- `types` : Types automatiquement détectés pour chaque colonne (dict)
- `num_rows` : Nombre de lignes de données (int)
- `estimated_size` : Taille estimée du fichier JONX en bytes (int)

**Détection automatique des types :**
- `int32` : Entiers
- `float32` : Nombres décimaux
- `str` : Chaînes de caractères
- `bool` : Booléens
- `json` : Objets complexes (fallback)

**Codes d'erreur :**
- `400` : Liste JSON vide
- `500` : Erreur interne lors de l'analyse

**Exemple avec curl :**
```bash
curl -X POST "http://localhost:8000/api/preview" \
     -H "Content-Type: application/json" \
     -d '{
       "data": [
         {"id": 1, "name": "Produit 1", "price": 100.50, "active": true},
         {"id": 2, "name": "Produit 2", "price": 200.75, "active": false}
       ]
     }'
```

**Exemple avec Python :**
```python
import requests

data = {
    "data": [
        {"id": 1, "name": "Produit 1", "price": 100.50, "active": True},
        {"id": 2, "name": "Produit 2", "price": 200.75, "active": False}
    ]
}

response = requests.post(
    "http://localhost:8000/api/preview",
    json=data
)

result = response.json()
print(f"Colonnes détectées: {result['fields']}")
print(f"Types: {result['types']}")
print(f"Taille estimée: {result['estimated_size']} bytes")
```

## 📝 Exemples

### Exemple complet : Encoder puis décoder

```python
from backend.logical.encoder import jonx_encode
from backend.logical.decoder import JONXFile

# 1. Encoder un JSON en JONX
jonx_encode("data/json/data.json", "data/json++/data_jonx.json++")

# 2. Charger le fichier JONX
jonx_file = JONXFile("data/json++/data_jonx.json++")

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

### Exemple complet avec l'API REST

```python
import requests
import json

# 1. Prévisualiser les métadonnées
preview_data = {
    "data": [
        {"id": 1, "name": "Produit 1", "price": 100.50, "active": True},
        {"id": 2, "name": "Produit 2", "price": 200.75, "active": False}
    ]
}

response = requests.post(
    "http://localhost:8000/api/preview",
    json=preview_data
)
preview_result = response.json()
print(f"Métadonnées: {json.dumps(preview_result, indent=2)}")

# 2. Encoder JSON → JONX (via body JSON)
response = requests.post(
    "http://localhost:8000/api/encode/json",
    json=preview_data
)

with open("output.json++", "wb") as f:
    f.write(response.content)
print("Fichier JONX créé: output.json++")

# 3. Décoder JONX → JSON
with open("output.json++", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/decode",
        files={"file": f}
    )
    decode_result = response.json()
    print(f"Données décodées: {json.dumps(decode_result['json_data'], indent=2)}")

# 4. Encoder depuis un fichier JSON
with open("data.json", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/encode",
        files={"file": f}
    )
    with open("data.json++", "wb") as out:
        out.write(response.content)
    print("Fichier JONX créé depuis upload: data.json++")

# 5. Vérifier la santé de l'API
response = requests.get("http://localhost:8000/health")
print(f"Statut API: {response.json()}")
```

## 🎯 Avantages du format JONX

1. **Compression efficace** : Utilisation de zstd pour une compression optimale
2. **Stockage en colonnes** : Meilleure compression pour les données tabulaires
3. **Types optimisés** : Stockage binaire pour les types numériques
4. **Index automatiques** : Recherches rapides sur les colonnes numériques
5. **Lecture sélective** : Décompression à la demande des colonnes
6. **Format binaire** : Plus rapide à lire que JSON textuel

## Licence

Ce projet est fourni tel quel pour usage éducatif et de développement.

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

