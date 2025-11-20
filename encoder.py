import orjson
import zstandard as zstd
import struct
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

def jonx_encode(json_path, jonx_path):
    # 1️⃣ Lire le JSON
    with open(json_path, "rb") as f:
        data = orjson.loads(f.read())
    if not isinstance(data, list):
        raise ValueError("Le JSON doit être une liste d'objets")

    # 2️⃣ Détection automatique des colonnes
    fields = list(data[0].keys())
    columns = {field: [p.get(field) for p in data] for field in fields}

    # 3️⃣ Détection des types
    types = {field: detect_type(vals) for field, vals in columns.items()}

    # 4️⃣ Compression des colonnes
    c = zstd.ZstdCompressor(level=3)
    compressed_columns = {}
    for field, vals in columns.items():
        packed = pack_column(vals, types[field])
        compressed_columns[field] = c.compress(packed)

    # 5️⃣ Création d’index automatique pour colonnes numériques
    indexes = {}
    for field, col_type in types.items():
        if col_type in ["int32", "float32"]:
            # index trié ascendant
            sorted_index = sorted(range(len(columns[field])), key=lambda i: columns[field][i])
            indexes[field] = c.compress(orjson.dumps(sorted_index))

    # 6️⃣ Écriture du fichier JONX
    with open(jonx_path, "wb") as f:
        # header
        f.write(b"JONX")
        f.write(struct.pack("I", 1))  # version

        # schema JSON compressé
        schema = {"fields": fields, "types": types}
        schema_compressed = c.compress(orjson.dumps(schema))
        f.write(struct.pack("I", len(schema_compressed)))  # taille du schéma
        f.write(schema_compressed)

        # colonnes compressées
        for field in fields:
            col_data = compressed_columns[field]
            f.write(struct.pack("I", len(col_data)))  # taille de la colonne
            f.write(col_data)

        # index compressés
        f.write(struct.pack("I", len(indexes)))  # nombre d'index
        for field, idx in indexes.items():
            f.write(struct.pack("I", len(field)))  # taille du nom du champ
            f.write(field.encode("utf-8"))
            f.write(struct.pack("I", len(idx)))  # taille de l'index
            f.write(idx)

    print(f"✅ Fichier JSON++ (JONX) créé avec {len(fields)} colonnes et {len(data)} lignes")

