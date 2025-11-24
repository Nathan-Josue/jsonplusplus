import orjson
import zstandard as zstd
import struct
import io
from collections import defaultdict

def detect_type(values):
    """Détecte le type principal d'une colonne"""
    first_val = values[0]
    if isinstance(first_val, int):
        return "int32"
    elif isinstance(first_val, float):
        return "float32"
    elif isinstance(first_val, str):
        return "str"
    elif isinstance(first_val, bool):
        return "bool"
    else:
        return "json"  # fallback pour objets complexes

def pack_column(values, col_type):
    """Transforme une colonne en binaire si numérique, sinon JSON compressé"""
    if col_type == "int32":
        return struct.pack(f"{len(values)}i", *values)
    elif col_type == "float32":
        return struct.pack(f"{len(values)}f", *values)
    elif col_type == "bool":
        return bytes([1 if v else 0 for v in values])
    else:
        return orjson.dumps(values)

def encode_to_bytes(json_data):
    """
    Encode des données JSON en format JONX et retourne les bytes
    
    Args:
        json_data: Liste de dictionnaires JSON à encoder
        
    Returns:
        Bytes du fichier JONX encodé
    """
    if not isinstance(json_data, list):
        raise ValueError("Le JSON doit être une liste d'objets")
    
    if len(json_data) == 0:
        raise ValueError("La liste JSON ne peut pas être vide")
    
    # Détection automatique des colonnes
    fields = list(json_data[0].keys())
    columns = {field: [p.get(field) for p in json_data] for field in fields}
    
    # Détection des types
    types = {field: detect_type(vals) for field, vals in columns.items()}
    
    # Compression des colonnes
    c = zstd.ZstdCompressor(level=3)
    compressed_columns = {}
    for field, vals in columns.items():
        packed = pack_column(vals, types[field])
        compressed_columns[field] = c.compress(packed)
    
    # Création d'index automatique pour colonnes numériques
    indexes = {}
    for field, col_type in types.items():
        if col_type in ["int32", "float32"]:
            # index trié ascendant
            sorted_index = sorted(range(len(columns[field])), key=lambda i: columns[field][i])
            indexes[field] = c.compress(orjson.dumps(sorted_index))
    
    # Créer le fichier JONX en mémoire
    output = io.BytesIO()
    
    # Header
    output.write(b"JONX")
    output.write(struct.pack("I", 1))  # version
    
    # Schema JSON compressé
    schema = {"fields": fields, "types": types}
    schema_compressed = c.compress(orjson.dumps(schema))
    output.write(struct.pack("I", len(schema_compressed)))
    output.write(schema_compressed)
    
    # Colonnes compressées
    for field in fields:
        col_data = compressed_columns[field]
        output.write(struct.pack("I", len(col_data)))
        output.write(col_data)
    
    # Index compressés
    output.write(struct.pack("I", len(indexes)))
    for field, idx in indexes.items():
        output.write(struct.pack("I", len(field)))
        output.write(field.encode("utf-8"))
        output.write(struct.pack("I", len(idx)))
        output.write(idx)
    
    output.seek(0)
    return output.read()

def jonx_encode(json_path, jonx_path):
    """
    Encode un fichier JSON en format JONX et l'écrit dans un fichier
    
    Args:
        json_path: Chemin vers le fichier JSON source
        jonx_path: Chemin vers le fichier JONX de destination
    """
    # Lire le JSON
    with open(json_path, "rb") as f:
        data = orjson.loads(f.read())
    
    # Encoder en bytes
    jonx_bytes = encode_to_bytes(data)
    
    # Écrire dans le fichier
    with open(jonx_path, "wb") as f:
        f.write(jonx_bytes)
    
    fields = list(data[0].keys()) if data else []
    print(f"✅ Fichier JSON++ (JONX) créé avec {len(fields)} colonnes et {len(data)} lignes")