import orjson
import zstandard as zstd
import struct
import io
from datetime import datetime
from ..exceptions import (
    JONXValidationError,
    JONXEncodeError,
    JONXSchemaError
)
from .packing import pack_column
from .type_detection import detect_type

ZSTD = zstd.ZstdCompressor(level=7)

# Types supportés
NUMERIC_TYPES = {
    "int8", "int16", "int32", "int64",
    "uint8", "uint16", "uint32", "uint64",
    "float16", "float32", "float64"
}

TEMPORAL_TYPES = {"date", "datetime", "timestamp_ms"}
INDEXABLE_TYPES = NUMERIC_TYPES | TEMPORAL_TYPES


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


def _parse_nullable_type(type_str):
    """
    Parse un type nullable et retourne (is_nullable, base_type).

    Args:
        type_str: Type string, ex: "nullable<int32>" ou "int32"

    Returns:
        tuple: (is_nullable: bool, base_type: str)
    """
    if isinstance(type_str, str) and type_str.startswith("nullable<") and type_str.endswith(">"):
        base_type = type_str[9:-1]  # Extract type between "nullable<" and ">"
        return True, base_type
    return False, type_str


def encode_to_bytes(json_data):
    """
    Encode des données JSON en bytes JONX avec validation complète.

    Supporte les types:
    - Entiers signés: int8, int16, int32, int64
    - Entiers non-signés: uint8, uint16, uint32, uint64
    - Flottants: float16, float32, float64
    - Booléens: bool
    - Chaînes: string, string_dict (dictionnaire de chaînes)
    - Temporels: date, datetime, timestamp_ms
    - Spéciaux: enum, uuid, binary
    - Nullable: nullable<T> pour tout type T

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
        enum_mappings = {}  # Pour stocker les mappings enum
        string_dicts = {}  # Pour stocker les dictionnaires string_dict

        for f, col in columns.items():
            if len(col) == 0:
                raise JONXValidationError(
                    f"La colonne '{f}' est vide",
                    {"field": f}
                )
            try:
                detected = detect_type(col)

                # Gérer les types complexes retournés comme dict
                if isinstance(detected, dict):
                    type_name = detected.get("type")

                    if type_name == "enum":
                        types[f] = "enum"
                        enum_mappings[f] = detected.get("mapping", {})
                    elif type_name == "string_dict":
                        types[f] = "string_dict"
                        string_dicts[f] = detected.get("dictionary", {})
                    elif type_name and type_name.startswith("nullable<"):
                        types[f] = type_name
                        # Si le type sous-jacent a des metadata, les stocker
                        if "mapping" in detected:
                            enum_mappings[f] = detected["mapping"]
                        if "dictionary" in detected:
                            string_dicts[f] = detected["dictionary"]
                    else:
                        types[f] = type_name or detected
                else:
                    types[f] = detected

            except Exception as e:
                raise JONXEncodeError(
                    f"Erreur lors de la détection du type pour la colonne '{f}'",
                    {"field": f, "error": str(e)}
                ) from e

        # Compression colonnes
        compressed_columns = {}
        for f in fields:
            try:
                # Préparer les métadonnées pour pack_column
                pack_kwargs = {}

                is_nullable, base_type = _parse_nullable_type(types[f])

                if base_type == "enum" or (is_nullable and base_type == "enum"):
                    pack_kwargs["enum_mapping"] = enum_mappings.get(f, {})
                elif base_type == "string_dict" or (is_nullable and base_type == "string_dict"):
                    pack_kwargs["string_dict"] = string_dicts.get(f, {})

                blob = pack_column(columns[f], types[f], **pack_kwargs)
                compressed_columns[f] = ZSTD.compress(blob)
            except Exception as e:
                raise JONXEncodeError(
                    f"Erreur lors de l'encodage de la colonne '{f}'",
                    {"field": f, "type": types[f], "error": str(e)}
                ) from e

        # Index auto (types numériques et temporels)
        indexes = {}

        for f, t in types.items():
            # Parse nullable type
            is_nullable, base_type = _parse_nullable_type(t)

            if base_type in INDEXABLE_TYPES:
                try:
                    # Fonction de tri qui gère les None
                    def sort_key(i):
                        val = columns[f][i]
                        if val is None:
                            return float('-inf')
                        return val

                    sorted_idx = sorted(range(len(columns[f])), key=sort_key)
                    indexes[f] = ZSTD.compress(orjson.dumps(sorted_idx))
                except Exception as e:
                    raise JONXEncodeError(
                        f"Erreur lors de la création de l'index pour '{f}'",
                        {"field": f, "error": str(e)}
                    ) from e

        out = io.BytesIO()

        # Header
        out.write(b"JONX")
        out.write(struct.pack("I", 3))  # Version 3 pour tous les nouveaux types

        # Schema avec toutes les métadonnées
        schema = {
            "fields": fields,
            "types": types,
        }

        # Ajouter les métadonnées optionnelles seulement si présentes
        if enum_mappings:
            schema["enum_mappings"] = enum_mappings
        if string_dicts:
            schema["string_dicts"] = string_dicts

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