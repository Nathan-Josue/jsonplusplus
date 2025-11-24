import orjson
import zstandard as zstd
import struct
import io
import math
import os
from .exceptions import (
    JONXValidationError,
    JONXEncodeError,
    JONXFileError,
    JONXSchemaError
)

ZSTD = zstd.ZstdCompressor(level=7)


# -----------------------------------------------------
#   TYPE DETECTION
# -----------------------------------------------------

def detect_numeric_type_int(values):
    """
    Détermine si une colonne d'entiers peut être stockée en int16 ou int32.
    """
    min_v = min(values)
    max_v = max(values)

    if -32768 <= min_v <= 32767 and -32768 <= max_v <= 32767:
        return "int16"
    return "int32"


def detect_numeric_type_float(values):
    """
    Détermine float16 si :
    - précision <= 3 décimales
    - valeur dans la plage float16
    Sinon float32.
    """
    # plage float16 IEEE754
    MIN_F16 = -65504
    MAX_F16 = 65504

    for v in values:
        if not (MIN_F16 <= v <= MAX_F16):
            return "float32"
        # précision <= 3 décimales
        if round(v, 3) != v:
            return "float32"

    return "float16"


def detect_type(values):
    """Détection du type avec support int16 / float16."""
    first = values[0]

    if isinstance(first, bool):
        return "bool"

    if isinstance(first, int):
        return detect_numeric_type_int(values)

    if isinstance(first, float):
        return detect_numeric_type_float(values)

    if isinstance(first, str):
        return "str"

    return "json"


# -----------------------------------------------------
#   PACKING
# -----------------------------------------------------

def pack_column(values, col_type):
    """Encode binaire en fonction du type."""
    if col_type == "int16":
        return struct.pack(f"{len(values)}h", *values)

    if col_type == "int32":
        return struct.pack(f"{len(values)}i", *values)

    if col_type == "float16":
        # conversion manuelle float32 -> float16 (IEEE754 half)
        import numpy as np
        arr = np.array(values, dtype=np.float16)
        return arr.tobytes()

    if col_type == "float32":
        return struct.pack(f"{len(values)}f", *values)

    if col_type == "bool":
        return bytes((1 if v else 0) for v in values)

    return orjson.dumps(values)


# -----------------------------------------------------
#   ENCODER PRINCIPAL
# -----------------------------------------------------

def _validate_json_data(json_data):
    """
    Valide les données JSON avant encodage.
    
    Args:
        json_data: Données JSON à valider
        
    Raises:
        JONXValidationError: Si les données sont invalides
    """
    if not isinstance(json_data, list):
        raise JONXValidationError(
            "Les données JSON doivent être une liste d'objets",
            {"type": type(json_data).__name__}
        )
    
    if len(json_data) == 0:
        raise JONXValidationError(
            "La liste JSON ne peut pas être vide",
            {"num_rows": 0}
        )
    
    # Vérifier que tous les éléments sont des dictionnaires
    for i, item in enumerate(json_data):
        if not isinstance(item, dict):
            raise JONXValidationError(
                f"L'élément à l'index {i} n'est pas un dictionnaire",
                {"index": i, "type": type(item).__name__}
            )
    
    # Vérifier que tous les objets ont les mêmes clés
    first_keys = set(json_data[0].keys())
    if len(first_keys) == 0:
        raise JONXValidationError(
            "Les objets JSON doivent avoir au moins une clé",
            {"num_rows": len(json_data)}
        )
    
    for i, item in enumerate(json_data[1:], start=1):
        item_keys = set(item.keys())
        if item_keys != first_keys:
            missing = first_keys - item_keys
            extra = item_keys - first_keys
            raise JONXSchemaError(
                f"L'objet à l'index {i} a un schéma différent",
                {
                    "index": i,
                    "expected_keys": sorted(first_keys),
                    "actual_keys": sorted(item_keys),
                    "missing_keys": sorted(missing) if missing else None,
                    "extra_keys": sorted(extra) if extra else None
                }
            )


def encode_to_bytes(json_data):
    """
    Encode des données JSON en bytes JONX avec validation complète.
    
    Args:
        json_data: Liste d'objets JSON à encoder
        
    Returns:
        bytes: Données JONX encodées
        
    Raises:
        JONXValidationError: Si les données sont invalides
        JONXEncodeError: Si l'encodage échoue
    """
    try:
        # Validation des données
        _validate_json_data(json_data)
        
        fields = list(json_data[0].keys())
        columns = {f: [row[f] for row in json_data] for f in fields}
        
        # Vérifier que toutes les colonnes ont la même longueur
        expected_length = len(json_data)
        for field, values in columns.items():
            if len(values) != expected_length:
                raise JONXSchemaError(
                    f"La colonne '{field}' a une longueur incohérente",
                    {
                        "field": field,
                        "expected_length": expected_length,
                        "actual_length": len(values)
                    }
                )
        
        # Détection complète des types
        types = {}
        for f, col in columns.items():
            if len(col) == 0:
                raise JONXValidationError(
                    f"La colonne '{f}' est vide",
                    {"field": f}
                )
            try:
                types[f] = detect_type(col)
            except Exception as e:
                raise JONXEncodeError(
                    f"Erreur lors de la détection du type pour la colonne '{f}'",
                    {"field": f, "error": str(e)}
                ) from e
        
        # Compression colonnes
        compressed_columns = {}
        for f in fields:
            try:
                blob = pack_column(columns[f], types[f])
                compressed_columns[f] = ZSTD.compress(blob)
            except Exception as e:
                raise JONXEncodeError(
                    f"Erreur lors de l'encodage de la colonne '{f}'",
                    {"field": f, "type": types[f], "error": str(e)}
                ) from e
        
        # Index auto (numériques uniquement)
        indexes = {}
        for f, t in types.items():
            if t in ("int16", "int32", "float16", "float32"):
                try:
                    sorted_idx = sorted(range(len(columns[f])),
                                        key=lambda i: columns[f][i])
                    indexes[f] = ZSTD.compress(orjson.dumps(sorted_idx))
                except Exception as e:
                    raise JONXEncodeError(
                        f"Erreur lors de la création de l'index pour '{f}'",
                        {"field": f, "error": str(e)}
                    ) from e
        
        out = io.BytesIO()
        
        # Header
        out.write(b"JONX")
        out.write(struct.pack("I", 1))
        
        # Schema
        schema = {"fields": fields, "types": types}
        try:
            schema_bytes = ZSTD.compress(orjson.dumps(schema))
            out.write(struct.pack("I", len(schema_bytes)))
            out.write(schema_bytes)
        except Exception as e:
            raise JONXEncodeError(
                "Erreur lors de l'encodage du schéma",
                {"error": str(e)}
            ) from e
        
        # Colonnes
        for f in fields:
            col = compressed_columns[f]
            out.write(struct.pack("I", len(col)))
            out.write(col)
        
        # Index
        out.write(struct.pack("I", len(indexes)))
        for f, idx in indexes.items():
            out.write(struct.pack("I", len(f)))
            out.write(f.encode("utf-8"))
            out.write(struct.pack("I", len(idx)))
            out.write(idx)
        
        return out.getvalue()
        
    except (JONXValidationError, JONXSchemaError, JONXEncodeError):
        # Re-raise les exceptions personnalisées
        raise
    except Exception as e:
        # Capturer toute autre exception et la convertir
        raise JONXEncodeError(
            "Erreur inattendue lors de l'encodage",
            {"error": str(e), "error_type": type(e).__name__}
        ) from e

    # Compression colonnes
    compressed_columns = {}
    for f in fields:
        blob = pack_column(columns[f], types[f])
        compressed_columns[f] = ZSTD.compress(blob)

    # Index auto (numériques uniquement)
    indexes = {}
    for f, t in types.items():
        if t in ("int16", "int32", "float16", "float32"):
            sorted_idx = sorted(range(len(columns[f])),
                                key=lambda i: columns[f][i])
            indexes[f] = ZSTD.compress(orjson.dumps(sorted_idx))

    out = io.BytesIO()

    # Header
    out.write(b"JONX")
    out.write(struct.pack("I", 1))

    # Schema
    schema = {"fields": fields, "types": types}
    schema_bytes = ZSTD.compress(orjson.dumps(schema))
    out.write(struct.pack("I", len(schema_bytes)))
    out.write(schema_bytes)

    # Colonnes
    for f in fields:
        col = compressed_columns[f]
        out.write(struct.pack("I", len(col)))
        out.write(col)

    # Index
    out.write(struct.pack("I", len(indexes)))
    for f, idx in indexes.items():
        out.write(struct.pack("I", len(f)))
        out.write(f.encode("utf-8"))
        out.write(struct.pack("I", len(idx)))
        out.write(idx)

    return out.getvalue()


# -----------------------------------------------------
#   WRAPPER FICHIER
# -----------------------------------------------------

def jonx_encode(json_path, jonx_path):
    """
    Encode un fichier JSON en fichier JONX avec validation.
    
    Args:
        json_path: Chemin vers le fichier JSON source
        jonx_path: Chemin vers le fichier JONX de destination
        
    Raises:
        JONXFileError: Si les fichiers ne peuvent pas être lus/écrits
        JONXValidationError: Si les données JSON sont invalides
        JONXEncodeError: Si l'encodage échoue
    """
    # Vérifier que le fichier source existe
    if not os.path.exists(json_path):
        raise JONXFileError(
            f"Le fichier source n'existe pas: {json_path}",
            {"path": json_path}
        )
    
    if not os.path.isfile(json_path):
        raise JONXFileError(
            f"Le chemin n'est pas un fichier: {json_path}",
            {"path": json_path}
        )
    
    # Vérifier les permissions de lecture
    if not os.access(json_path, os.R_OK):
        raise JONXFileError(
            f"Permission de lecture refusée: {json_path}",
            {"path": json_path}
        )
    
    # Lire et parser le fichier JSON
    try:
        with open(json_path, "rb") as f:
            file_content = f.read()
    except IOError as e:
        raise JONXFileError(
            f"Impossible de lire le fichier: {json_path}",
            {"path": json_path, "error": str(e)}
        ) from e
    
    if len(file_content) == 0:
        raise JONXValidationError(
            f"Le fichier JSON est vide: {json_path}",
            {"path": json_path}
        )
    
    try:
        data = orjson.loads(file_content)
    except orjson.JSONDecodeError as e:
        raise JONXValidationError(
            f"Le fichier JSON est invalide: {json_path}",
            {"path": json_path, "error": str(e)}
        ) from e
    except Exception as e:
        raise JONXFileError(
            f"Erreur lors de la lecture du fichier JSON: {json_path}",
            {"path": json_path, "error": str(e)}
        ) from e
    
    # Encoder les données
    try:
        jonx_bytes = encode_to_bytes(data)
    except (JONXValidationError, JONXEncodeError) as e:
        # Ajouter le chemin du fichier aux détails
        if hasattr(e, 'details'):
            e.details['source_file'] = json_path
        raise
    
    # Écrire le fichier JONX
    try:
        # Créer le répertoire de destination si nécessaire
        dest_dir = os.path.dirname(jonx_path)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
        
        with open(jonx_path, "wb") as f:
            f.write(jonx_bytes)
    except IOError as e:
        raise JONXFileError(
            f"Impossible d'écrire le fichier JONX: {jonx_path}",
            {"path": jonx_path, "error": str(e)}
        ) from e
    
    print(f"✅ JONX créé : {len(data)} lignes, {len(data[0])} colonnes")
