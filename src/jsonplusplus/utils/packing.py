import orjson
import struct
import numpy as np
from datetime import datetime, date
from uuid import UUID

# Types numériques et leurs formats struct
NUMERIC_PACK_FORMATS = {
    "int8": "b",  # signed char
    "int16": "h",  # signed short
    "int32": "i",  # signed int
    "int64": "q",  # signed long long
    "uint8": "B",  # unsigned char
    "uint16": "H",  # unsigned short
    "uint32": "I",  # unsigned int
    "uint64": "Q",  # unsigned long long
    "float32": "f",  # float
    "float64": "d",  # double
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


def _pack_numeric(values, col_type):
    """
    Pack une colonne numérique.

    Args:
        values: Liste de valeurs numériques
        col_type: Type numérique (int8, int16, ..., float64)

    Returns:
        bytes: Données packées
    """
    if col_type == "float16":
        # float16 nécessite numpy
        arr = np.array(values, dtype=np.float16)
        return arr.tobytes()

    if col_type in NUMERIC_PACK_FORMATS:
        fmt = NUMERIC_PACK_FORMATS[col_type]
        return struct.pack(f"{len(values)}{fmt}", *values)

    raise ValueError(f"Type numérique inconnu: {col_type}")


def _pack_temporal(values, col_type):
    """
    Pack une colonne temporelle.

    Args:
        values: Liste de dates/datetime/timestamps
        col_type: Type temporel (date, datetime, timestamp_ms)

    Returns:
        bytes: Données packées en JSON
    """
    if col_type == "date":
        # Convertir date -> ISO string "YYYY-MM-DD"
        serialized = [
            v.isoformat() if isinstance(v, date) else (v if v is None else str(v))
            for v in values
        ]
    elif col_type == "datetime":
        # Convertir datetime -> ISO string "YYYY-MM-DDTHH:MM:SS"
        serialized = [
            v.isoformat() if isinstance(v, datetime) else (v if v is None else str(v))
            for v in values
        ]
    elif col_type == "timestamp_ms":
        # Convertir datetime -> millisecondes depuis epoch
        serialized = [
            int(v.timestamp() * 1000) if isinstance(v, datetime)
            else (v if v is None or isinstance(v, (int, float)) else None)
            for v in values
        ]
    else:
        raise ValueError(f"Type temporel inconnu: {col_type}")

    return orjson.dumps(serialized)


def _pack_enum(values, enum_mapping):
    """
    Pack une colonne enum en utilisant le mapping fourni.

    Args:
        values: Liste de valeurs enum
        enum_mapping: Dictionnaire {value: index}

    Returns:
        bytes: Indices packés en JSON
    """
    # Convertir les valeurs en indices selon le mapping
    indices = [enum_mapping.get(v) for v in values]
    return orjson.dumps(indices)


def _pack_string_dict(values, string_dict):
    """
    Pack une colonne string_dict en utilisant le dictionnaire fourni.

    Args:
        values: Liste de chaînes
        string_dict: Dictionnaire {string: index}

    Returns:
        bytes: Indices packés en JSON
    """
    # Convertir les chaînes en indices selon le dictionnaire
    indices = [string_dict.get(v) for v in values]
    return orjson.dumps(indices)


def _pack_uuid(values):
    """
    Pack une colonne UUID.

    Args:
        values: Liste d'UUID (objets ou strings)

    Returns:
        bytes: UUIDs en string packés en JSON
    """
    serialized = [
        str(v) if isinstance(v, UUID) else (v if v is None else str(v))
        for v in values
    ]
    return orjson.dumps(serialized)


def _pack_nullable(values, base_type, **kwargs):
    """
    Pack une colonne nullable en séparant le bitmap des nulls et les données.

    Format: [null_bitmap] + [packed_data]
    Le null_bitmap utilise 1 bit par valeur (packés en bytes)

    Args:
        values: Liste de valeurs avec possibles None
        base_type: Type de base (sans le nullable<>)
        **kwargs: Arguments additionnels pour le type de base

    Returns:
        bytes: Données packées avec bitmap de nulls
    """
    # Créer le bitmap des nulls (1 = null, 0 = valeur présente)
    null_bitmap = bytearray((len(values) + 7) // 8)  # 1 bit par valeur
    non_null_values = []

    for i, v in enumerate(values):
        if v is None:
            # Marquer comme null dans le bitmap
            byte_idx = i // 8
            bit_idx = i % 8
            null_bitmap[byte_idx] |= (1 << bit_idx)
        else:
            non_null_values.append(v)

    # Si tous les éléments sont null, retourner juste le bitmap
    if not non_null_values:
        return bytes(null_bitmap)

    # Packer les valeurs non-nulles selon leur type
    if base_type in NUMERIC_PACK_FORMATS or base_type in ("float16",):
        data_packed = _pack_numeric(non_null_values, base_type)
    elif base_type in ("date", "datetime", "timestamp_ms"):
        data_packed = _pack_temporal(non_null_values, base_type)
    elif base_type == "enum":
        data_packed = _pack_enum(non_null_values, kwargs.get("enum_mapping", {}))
    elif base_type == "string_dict":
        data_packed = _pack_string_dict(non_null_values, kwargs.get("string_dict", {}))
    elif base_type == "uuid":
        data_packed = _pack_uuid(non_null_values)
    elif base_type == "bool":
        data_packed = bytes((1 if v else 0) for v in non_null_values)
    elif base_type == "binary":
        data_packed = orjson.dumps(non_null_values)
    else:
        # string ou type inconnu
        data_packed = orjson.dumps(non_null_values)

    # Combiner bitmap + données
    return bytes(null_bitmap) + data_packed


# -----------------------------------------------------
#   PACKING PRINCIPAL
# -----------------------------------------------------

def pack_column(values, col_type, **kwargs):
    """
    Encode binaire en fonction du type.

    Supporte tous les types:
    - Numériques: int8, int16, int32, int64, uint8, uint16, uint32, uint64,
                  float16, float32, float64
    - Booléen: bool
    - Chaînes: string, string_dict
    - Temporels: date, datetime, timestamp_ms
    - Spéciaux: enum, uuid, binary
    - Nullable: nullable<T> pour tout type T

    Args:
        values: Liste de valeurs à packer
        col_type: Type de la colonne
        **kwargs: Arguments additionnels
            - enum_mapping: Dictionnaire pour les enums {value: index}
            - string_dict: Dictionnaire pour string_dict {string: index}

    Returns:
        bytes: Données packées

    Examples:
        >>> pack_column([1, 2, 3], "int32")
        b'\\x01\\x00\\x00\\x00\\x02\\x00\\x00\\x00\\x03\\x00\\x00\\x00'

        >>> pack_column([1.5, 2.5], "float32")
        b'\\x00\\x00\\xc0?\\x00\\x00 @'

        >>> pack_column(["a", "b", "a"], "enum", enum_mapping={"a": 0, "b": 1})
        b'[0,1,0]'

        >>> pack_column([1, None, 3], "nullable<int32>")
        b'\\x02...'  # bitmap + données compressées
    """
    # Parser le type pour détecter nullable
    is_nullable, base_type = _parse_nullable_type(col_type)

    if is_nullable:
        return _pack_nullable(values, base_type, **kwargs)

    # Types numériques standards
    if base_type in NUMERIC_PACK_FORMATS or base_type == "float16":
        return _pack_numeric(values, base_type)

    # Booléen
    if base_type == "bool":
        return bytes((1 if v else 0) for v in values)

    # Types temporels
    if base_type in ("date", "datetime", "timestamp_ms"):
        return _pack_temporal(values, base_type)

    # Enum
    if base_type == "enum":
        enum_mapping = kwargs.get("enum_mapping", {})
        if not enum_mapping:
            raise ValueError("enum_mapping requis pour le type enum")
        return _pack_enum(values, enum_mapping)

    # String dict
    if base_type == "string_dict":
        string_dict = kwargs.get("string_dict", {})
        if not string_dict:
            raise ValueError("string_dict requis pour le type string_dict")
        return _pack_string_dict(values, string_dict)

    # UUID
    if base_type == "uuid":
        return _pack_uuid(values)

    # Binary et string (fallback JSON)
    return orjson.dumps(values)