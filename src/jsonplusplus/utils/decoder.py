import orjson
import zstandard as zstd
import struct
import numpy as np
from datetime import datetime, date
from uuid import UUID
from ..exceptions import (
    JONXDecodeError,
    JONXSchemaError,
    JONXValidationError,
)

# Types numériques et leurs formats struct
NUMERIC_TYPES = {
    "int8": ("b", 1),  # signed char
    "int16": ("h", 2),  # signed short
    "int32": ("i", 4),  # signed int
    "int64": ("q", 8),  # signed long long
    "uint8": ("B", 1),  # unsigned char
    "uint16": ("H", 2),  # unsigned short
    "uint32": ("I", 4),  # unsigned int
    "uint64": ("Q", 8),  # unsigned long long
    "float16": (None, 2),  # numpy float16
    "float32": ("f", 4),  # float
    "float64": ("d", 8),  # double
}


def _parse_nullable_type(type_str):
    """
    Parse un type nullable et retourne (is_nullable, base_type).

    Args:
        type_str: Type string, ex: "nullable<int32>" ou "int32"

    Returns:
        tuple: (is_nullable: bool, base_type: str)
    """
    if isinstance(type_str, str) and type_str.startswith("nullable<") and type_str.endswith(">"):
        base_type = type_str[9:-1]
        return True, base_type
    return False, type_str


def _decode_numeric_column(packed, col_type, field):
    """
    Décode une colonne numérique.

    Args:
        packed: Données binaires compressées
        col_type: Type de la colonne
        field: Nom du champ (pour les messages d'erreur)

    Returns:
        list: Valeurs décodées
    """
    if col_type not in NUMERIC_TYPES:
        raise JONXDecodeError(
            f"Type numérique inconnu: {col_type}",
            {"field": field, "type": col_type}
        )

    format_char, size = NUMERIC_TYPES[col_type]

    if len(packed) % size != 0:
        raise JONXDecodeError(
            f"Taille invalide pour la colonne {col_type} '{field}'",
            {"field": field, "packed_size": len(packed), "expected_multiple": size}
        )

    n = len(packed) // size

    # float16 nécessite numpy
    if col_type == "float16":
        arr = np.frombuffer(packed, dtype=np.float16)
        return arr.astype(np.float32).tolist()

    # Autres types numériques
    try:
        return list(struct.unpack(f"{n}{format_char}", packed))
    except struct.error as e:
        raise JONXDecodeError(
            f"Erreur lors du décodage binaire de la colonne '{field}'",
            {"field": field, "type": col_type, "error": str(e)}
        ) from e


def _decode_temporal_column(packed, col_type, field):
    """
    Décode une colonne temporelle (date, datetime, timestamp_ms).

    Args:
        packed: Données binaires compressées
        col_type: Type de la colonne
        field: Nom du champ

    Returns:
        list: Valeurs décodées
    """
    try:
        raw_data = orjson.loads(packed)
    except orjson.JSONDecodeError as e:
        raise JONXDecodeError(
            f"Erreur lors du parsing JSON de la colonne temporelle '{field}'",
            {"field": field, "type": col_type, "error": str(e)}
        ) from e

    if col_type == "date":
        # Format ISO: "YYYY-MM-DD"
        return [datetime.fromisoformat(d).date() if d else None for d in raw_data]

    elif col_type == "datetime":
        # Format ISO: "YYYY-MM-DDTHH:MM:SS"
        return [datetime.fromisoformat(dt) if dt else None for dt in raw_data]

    elif col_type == "timestamp_ms":
        # Timestamps en millisecondes depuis epoch
        return [datetime.fromtimestamp(ts / 1000.0) if ts is not None else None for ts in raw_data]

    return raw_data


def _decode_special_column(packed, col_type, field, schema):
    """
    Décode une colonne spéciale (enum, uuid, binary, string_dict).

    Args:
        packed: Données binaires compressées
        col_type: Type de la colonne
        field: Nom du champ
        schema: Schéma complet pour accéder aux métadonnées

    Returns:
        list: Valeurs décodées
    """
    try:
        raw_data = orjson.loads(packed)
    except orjson.JSONDecodeError as e:
        raise JONXDecodeError(
            f"Erreur lors du parsing JSON de la colonne '{field}'",
            {"field": field, "type": col_type, "error": str(e)}
        ) from e

    if col_type == "enum":
        # Décoder les indices en valeurs via le mapping
        enum_mappings = schema.get("enum_mappings", {})
        mapping = enum_mappings.get(field, {})
        # Inverser le mapping: {value: index} -> {index: value}
        reverse_mapping = {v: k for k, v in mapping.items()}
        return [reverse_mapping.get(idx) for idx in raw_data]

    elif col_type == "string_dict":
        # Décoder les indices en chaînes via le dictionnaire
        string_dicts = schema.get("string_dicts", {})
        dictionary = string_dicts.get(field, {})
        # raw_data contient des indices, dictionary map index -> string
        return [dictionary.get(str(idx)) if idx is not None else None for idx in raw_data]

    elif col_type == "uuid":
        # Convertir les chaînes en objets UUID
        return [UUID(u) if u else None for u in raw_data]

    elif col_type == "binary":
        # Les données binaires sont stockées en base64 ou bytes
        return raw_data

    return raw_data


def _decode_nullable_column(packed, col_type, field, schema):
    """
    Décode une colonne nullable.

    Args:
        packed: Données binaires compressées
        col_type: Type nullable complet (ex: "nullable<int32>")
        field: Nom du champ
        schema: Schéma complet

    Returns:
        list: Valeurs décodées avec None pour les valeurs nulles
    """
    # Le format nullable stocke: [bitmap des nulls (bytes)] + [données compressées du type de base]
    # Pour simplifier, on suppose que c'est géré dans pack_column/unpack_column
    # et que les données décompressées contiennent déjà les None

    is_nullable, base_type = _parse_nullable_type(col_type)

    # Décoder selon le type de base
    if base_type in NUMERIC_TYPES:
        return _decode_numeric_column(packed, base_type, field)
    elif base_type in ("date", "datetime", "timestamp_ms"):
        return _decode_temporal_column(packed, base_type, field)
    elif base_type in ("enum", "string_dict", "uuid", "binary"):
        return _decode_special_column(packed, base_type, field, schema)
    elif base_type == "bool":
        return [bool(b) if b != 255 else None for b in packed]  # 255 = null marker
    else:
        # string ou autre
        try:
            return orjson.loads(packed)
        except orjson.JSONDecodeError as e:
            raise JONXDecodeError(
                f"Erreur lors du parsing JSON de la colonne '{field}'",
                {"field": field, "type": col_type, "error": str(e)}
            ) from e


def decode_from_bytes(data: bytes) -> dict:
    """
    Décode des bytes JONX en données JSON avec validation complète.

    Supporte les types:
    - Entiers signés: int8, int16, int32, int64
    - Entiers non-signés: uint8, uint16, uint32, uint64
    - Flottants: float16, float32, float64
    - Booléens: bool
    - Chaînes: string, string_dict
    - Temporels: date, datetime, timestamp_ms
    - Spéciaux: enum, uuid, binary
    - Nullable: nullable<T> pour tout type T

    Args:
        data: Données JONX à décoder

    Returns:
        dict: Dictionnaire avec version, fields, types, num_rows, json_data

    Raises:
        JONXDecodeError: Si le décodage échoue
        JONXValidationError: Si les données sont corrompues
    """
    if not isinstance(data, bytes):
        raise JONXValidationError(
            "Les données doivent être de type bytes",
            {"type": type(data).__name__}
        )

    if len(data) < 8:
        raise JONXDecodeError(
            "Les données JONX sont trop courtes (header manquant)",
            {"data_length": len(data), "min_length": 8}
        )

    if not data.startswith(b"JONX"):
        raise JONXDecodeError(
            "Le fichier n'est pas au format JONX (signature invalide)",
            {
                "signature": data[:4].hex() if len(data) >= 4 else "insuffisant",
                "expected": "4a4f4e58"
            }
        )

    try:
        version = struct.unpack("I", data[4:8])[0]
    except struct.error as e:
        raise JONXDecodeError(
            "Erreur lors de la lecture de la version",
            {"error": str(e)}
        ) from e

    if version not in (1, 2, 3):
        raise JONXDecodeError(
            f"Version JONX non supportée: {version}",
            {"version": version, "supported": [1, 2, 3]}
        )

    c = zstd.ZstdDecompressor()
    offset = 8

    # --- Lire le schéma ---
    if len(data) < offset + 4:
        raise JONXDecodeError(
            "Données insuffisantes pour lire la taille du schéma",
            {"offset": offset, "data_length": len(data)}
        )

    try:
        schema_size = struct.unpack("I", data[offset:offset + 4])[0]
    except struct.error as e:
        raise JONXDecodeError(
            "Erreur lors de la lecture de la taille du schéma",
            {"error": str(e)}
        ) from e

    offset += 4

    if len(data) < offset + schema_size:
        raise JONXDecodeError(
            "Données insuffisantes pour lire le schéma",
            {"offset": offset, "schema_size": schema_size, "data_length": len(data)}
        )

    try:
        schema_bytes = c.decompress(data[offset:offset + schema_size])
        schema = orjson.loads(schema_bytes)
    except zstd.ZstdError as e:
        raise JONXDecodeError(
            "Erreur lors de la décompression du schéma",
            {"error": str(e)}
        ) from e
    except orjson.JSONDecodeError as e:
        raise JONXDecodeError(
            "Erreur lors du parsing du schéma JSON",
            {"error": str(e)}
        ) from e

    offset += schema_size

    # Valider le schéma
    if not isinstance(schema, dict):
        raise JONXSchemaError(
            "Le schéma doit être un dictionnaire",
            {"schema_type": type(schema).__name__}
        )

    if "fields" not in schema or "types" not in schema:
        raise JONXSchemaError(
            "Le schéma doit contenir 'fields' et 'types'",
            {"schema_keys": list(schema.keys())}
        )

    fields = schema["fields"]
    types = schema["types"]

    if not isinstance(fields, list) or not isinstance(types, dict):
        raise JONXSchemaError(
            "Le schéma a un format invalide",
            {
                "fields_type": type(fields).__name__,
                "types_type": type(types).__name__
            }
        )

    if len(fields) == 0:
        raise JONXSchemaError(
            "Le schéma ne contient aucune colonne",
            {"num_fields": 0}
        )

    # Vérifier que tous les champs ont un type défini
    for field in fields:
        if field not in types:
            raise JONXSchemaError(
                f"Le champ '{field}' n'a pas de type défini",
                {"field": field, "available_types": list(types.keys())}
            )

    columns = {}

    # --- Lire les colonnes ---
    for field in fields:
        if len(data) < offset + 4:
            raise JONXDecodeError(
                f"Données insuffisantes pour lire la taille de la colonne '{field}'",
                {"field": field, "offset": offset, "data_length": len(data)}
            )

        try:
            col_size = struct.unpack("I", data[offset:offset + 4])[0]
        except struct.error as e:
            raise JONXDecodeError(
                f"Erreur lors de la lecture de la taille de la colonne '{field}'",
                {"field": field, "error": str(e)}
            ) from e

        offset += 4

        if len(data) < offset + col_size:
            raise JONXDecodeError(
                f"Données insuffisantes pour lire la colonne '{field}'",
                {"field": field, "offset": offset, "col_size": col_size, "data_length": len(data)}
            )

        try:
            packed = c.decompress(data[offset:offset + col_size])
        except zstd.ZstdError as e:
            raise JONXDecodeError(
                f"Erreur lors de la décompression de la colonne '{field}'",
                {"field": field, "error": str(e)}
            ) from e

        offset += col_size

        col_type = types[field]
        is_nullable, base_type = _parse_nullable_type(col_type)

        try:
            # Décoder selon le type
            if is_nullable:
                columns[field] = _decode_nullable_column(packed, col_type, field, schema)
            elif base_type in NUMERIC_TYPES:
                columns[field] = _decode_numeric_column(packed, base_type, field)
            elif base_type in ("date", "datetime", "timestamp_ms"):
                columns[field] = _decode_temporal_column(packed, base_type, field)
            elif base_type in ("enum", "string_dict", "uuid", "binary"):
                columns[field] = _decode_special_column(packed, base_type, field, schema)
            elif base_type == "bool":
                columns[field] = [bool(b) for b in packed]
            else:
                # string ou type inconnu - fallback JSON
                try:
                    columns[field] = orjson.loads(packed)
                except orjson.JSONDecodeError as e:
                    raise JONXDecodeError(
                        f"Erreur lors du parsing JSON de la colonne '{field}'",
                        {"field": field, "type": col_type, "error": str(e)}
                    ) from e

        except JONXDecodeError:
            raise
        except Exception as e:
            raise JONXDecodeError(
                f"Erreur inattendue lors du décodage de la colonne '{field}'",
                {"field": field, "type": col_type, "error": str(e)}
            ) from e

    # Vérifier que toutes les colonnes ont la même longueur
    if fields:
        expected_length = len(columns[fields[0]])
        for field in fields[1:]:
            if len(columns[field]) != expected_length:
                raise JONXSchemaError(
                    f"La colonne '{field}' a une longueur incohérente",
                    {
                        "field": field,
                        "expected_length": expected_length,
                        "actual_length": len(columns[field])
                    }
                )

    # --- Lire les index (ignorés pour la reconstruction) ---
    if len(data) < offset + 4:
        raise JONXDecodeError(
            "Données insuffisantes pour lire le nombre d'index",
            {"offset": offset, "data_length": len(data)}
        )

    try:
        num_indexes = struct.unpack("I", data[offset:offset + 4])[0]
    except struct.error as e:
        raise JONXDecodeError(
            "Erreur lors de la lecture du nombre d'index",
            {"error": str(e)}
        ) from e

    offset += 4

    for i in range(num_indexes):
        if len(data) < offset + 4:
            raise JONXDecodeError(
                f"Données insuffisantes pour lire l'index {i}",
                {"index": i, "offset": offset, "data_length": len(data)}
            )

        try:
            name_len = struct.unpack("I", data[offset:offset + 4])[0]
        except struct.error as e:
            raise JONXDecodeError(
                f"Erreur lors de la lecture de la taille du nom d'index {i}",
                {"index": i, "error": str(e)}
            ) from e

        offset += 4

        if len(data) < offset + name_len:
            raise JONXDecodeError(
                f"Données insuffisantes pour lire le nom d'index {i}",
                {"index": i, "offset": offset, "name_len": name_len, "data_length": len(data)}
            )

        offset += name_len

        if len(data) < offset + 4:
            raise JONXDecodeError(
                f"Données insuffisantes pour lire la taille de l'index {i}",
                {"index": i, "offset": offset, "data_length": len(data)}
            )

        try:
            idx_size = struct.unpack("I", data[offset:offset + 4])[0]
        except struct.error as e:
            raise JONXDecodeError(
                f"Erreur lors de la lecture de la taille de l'index {i}",
                {"index": i, "error": str(e)}
            ) from e

        offset += 4

        if len(data) < offset + idx_size:
            raise JONXDecodeError(
                f"Données insuffisantes pour lire l'index {i}",
                {"index": i, "offset": offset, "idx_size": idx_size, "data_length": len(data)}
            )

        offset += idx_size

    # --- Reconstruire JSON ---
    num_rows = len(columns[fields[0]]) if fields else 0
    json_data = [
        {field: columns[field][i] for field in fields}
        for i in range(num_rows)
    ]

    return {
        "version": version,
        "fields": fields,
        "types": types,
        "num_rows": num_rows,
        "json_data": json_data,
        "schema": schema  # Inclure le schéma complet pour debug
    }