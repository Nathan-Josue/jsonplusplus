import orjson
import zstandard as zstd
import struct
import numpy as np
import os
from .exceptions import (
    JONXDecodeError,
    JONXFileError,
    JONXSchemaError,
    JONXValidationError,
    JONXIndexError
)


def decode_from_bytes(data: bytes) -> dict:
    """
    Décode des bytes JONX en données JSON avec validation complète.
    
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
                "expected": "4a4f4e58"  # "JONX" en hex
            }
        )
    
    try:
        version = struct.unpack("I", data[4:8])[0]
    except struct.error as e:
        raise JONXDecodeError(
            "Erreur lors de la lecture de la version",
            {"error": str(e)}
        ) from e
    
    if version != 1:
        raise JONXDecodeError(
            f"Version JONX non supportée: {version}",
            {"version": version, "supported": [1]}
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

        try:
            if col_type == "int16":
                n = len(packed) // 2
                if len(packed) % 2 != 0:
                    raise JONXDecodeError(
                        f"Taille invalide pour la colonne int16 '{field}'",
                        {"field": field, "packed_size": len(packed)}
                    )
                columns[field] = list(struct.unpack(f"{n}h", packed))

            elif col_type == "int32":
                n = len(packed) // 4
                if len(packed) % 4 != 0:
                    raise JONXDecodeError(
                        f"Taille invalide pour la colonne int32 '{field}'",
                        {"field": field, "packed_size": len(packed)}
                    )
                columns[field] = list(struct.unpack(f"{n}i", packed))

            elif col_type == "float16":
                if len(packed) % 2 != 0:
                    raise JONXDecodeError(
                        f"Taille invalide pour la colonne float16 '{field}'",
                        {"field": field, "packed_size": len(packed)}
                    )
                arr = np.frombuffer(packed, dtype=np.float16)
                columns[field] = arr.astype(np.float32).tolist()

            elif col_type == "float32":
                n = len(packed) // 4
                if len(packed) % 4 != 0:
                    raise JONXDecodeError(
                        f"Taille invalide pour la colonne float32 '{field}'",
                        {"field": field, "packed_size": len(packed)}
                    )
                columns[field] = list(struct.unpack(f"{n}f", packed))

            elif col_type == "bool":
                columns[field] = [bool(b) for b in packed]

            else:
                try:
                    columns[field] = orjson.loads(packed)
                except orjson.JSONDecodeError as e:
                    raise JONXDecodeError(
                        f"Erreur lors du parsing JSON de la colonne '{field}'",
                        {"field": field, "type": col_type, "error": str(e)}
                    ) from e
        except struct.error as e:
            raise JONXDecodeError(
                f"Erreur lors du décodage binaire de la colonne '{field}'",
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
        "json_data": json_data
    }


class JONXFile:
    def __init__(self, path):
        """
        Initialise un objet JONXFile pour accéder à un fichier JONX.
        
        Args:
            path: Chemin vers le fichier JONX
            
        Raises:
            JONXFileError: Si le fichier ne peut pas être lu
            JONXDecodeError: Si le fichier est corrompu
        """
        if not isinstance(path, str):
            raise JONXValidationError(
                "Le chemin doit être une chaîne de caractères",
                {"type": type(path).__name__}
            )
        
        if not os.path.exists(path):
            raise JONXFileError(
                f"Le fichier n'existe pas: {path}",
                {"path": path}
            )
        
        if not os.path.isfile(path):
            raise JONXFileError(
                f"Le chemin n'est pas un fichier: {path}",
                {"path": path}
            )
        
        if not os.access(path, os.R_OK):
            raise JONXFileError(
                f"Permission de lecture refusée: {path}",
                {"path": path}
            )
        
        self.path = path
        self.fields = []
        self.types = {}
        self.compressed_columns = {}
        self.indexes = {}
        self._load_file()

    def _load_file(self):
        try:
            with open(self.path, "rb") as f:
                data = f.read()
        except IOError as e:
            raise JONXFileError(
                f"Impossible de lire le fichier: {self.path}",
                {"path": self.path, "error": str(e)}
            ) from e
        
        if len(data) == 0:
            raise JONXFileError(
                f"Le fichier est vide: {self.path}",
                {"path": self.path}
            )

        try:
            result = decode_from_bytes(data)
            self.fields = result["fields"]
            self.types = result["types"]
        except (JONXDecodeError, JONXValidationError) as e:
            # Ajouter le chemin du fichier aux détails
            if hasattr(e, 'details'):
                e.details['file_path'] = self.path
            raise

        if not data.startswith(b"JONX"):
            raise JONXDecodeError(
                f"Le fichier n'est pas au format JONX: {self.path}",
                {"path": self.path}
            )

        offset = 8

        schema_size = struct.unpack("I", data[offset:offset + 4])[0]
        offset += 4 + schema_size

        # --- Colonnes compressées ---
        for field in self.fields:
            col_size = struct.unpack("I", data[offset:offset + 4])[0]
            offset += 4
            self.compressed_columns[field] = data[offset:offset + col_size]
            offset += col_size

        # --- Index compressés ---
        num_indexes = struct.unpack("I", data[offset:offset + 4])[0]
        offset += 4

        for _ in range(num_indexes):
            name_len = struct.unpack("I", data[offset:offset + 4])[0]
            offset += 4
            name = data[offset:offset + name_len].decode()
            offset += name_len

            idx_size = struct.unpack("I", data[offset:offset + 4])[0]
            offset += 4
            self.indexes[name] = data[offset:offset + idx_size]
            offset += idx_size

    def _validate_field_name(self, field_name):
        """
        Valide qu'un nom de colonne existe.
        
        Args:
            field_name: Nom de la colonne à valider
            
        Raises:
            JONXValidationError: Si la colonne n'existe pas
        """
        if not isinstance(field_name, str):
            raise JONXValidationError(
                "Le nom de colonne doit être une chaîne de caractères",
                {"type": type(field_name).__name__}
            )
        
        if field_name not in self.fields:
            raise JONXValidationError(
                f"La colonne '{field_name}' n'existe pas",
                {
                    "field": field_name,
                    "available_fields": self.fields
                }
            )
    
    def _validate_numeric_field(self, field_name):
        """
        Valide qu'une colonne est numérique.
        
        Args:
            field_name: Nom de la colonne à valider
            
        Raises:
            JONXValidationError: Si la colonne n'existe pas ou n'est pas numérique
        """
        self._validate_field_name(field_name)
        col_type = self.types.get(field_name)
        if col_type not in ("int16", "int32", "float16", "float32"):
            raise JONXValidationError(
                f"La colonne '{field_name}' n'est pas numérique",
                {"field": field_name, "type": col_type}
            )

    def _decompress_column(self, field_name, compressed):
        try:
            packed = zstd.ZstdDecompressor().decompress(compressed)
        except zstd.ZstdError as e:
            raise JONXDecodeError(
                f"Erreur lors de la décompression de la colonne '{field_name}'",
                {"field": field_name, "error": str(e)}
            ) from e
        
        t = self.types[field_name]

        try:
            if t == "int16":
                n = len(packed) // 2
                return list(struct.unpack(f"{n}h", packed))

            if t == "int32":
                n = len(packed) // 4
                return list(struct.unpack(f"{n}i", packed))

            if t == "float16":
                arr = np.frombuffer(packed, dtype=np.float16)
                return arr.astype(np.float32).tolist()

            if t == "float32":
                n = len(packed) // 4
                return list(struct.unpack(f"{n}f", packed))

            if t == "bool":
                return [bool(b) for b in packed]

            return orjson.loads(packed)
        except (struct.error, orjson.JSONDecodeError) as e:
            raise JONXDecodeError(
                f"Erreur lors du décodage de la colonne '{field_name}'",
                {"field": field_name, "type": t, "error": str(e)}
            ) from e

    def get_column(self, field_name):
        """
        Récupère une colonne décompressée avec validation.
        
        Args:
            field_name: Nom de la colonne
            
        Returns:
            list: Liste des valeurs de la colonne
            
        Raises:
            JONXValidationError: Si la colonne n'existe pas
            JONXDecodeError: Si la décompression échoue
        """
        self._validate_field_name(field_name)
        
        if field_name not in self.compressed_columns:
            raise JONXDecodeError(
                f"La colonne '{field_name}' n'est pas disponible dans le fichier",
                {"field": field_name, "available_columns": list(self.compressed_columns.keys())}
            )
        
        return self._decompress_column(field_name, self.compressed_columns[field_name])

    def find_min(self, field, column=None, use_index=False):
        """
        Trouve la valeur minimale d'une colonne.
        
        Args:
            field: Nom de la colonne
            column: Colonne pré-chargée (optionnel, récupérée automatiquement si None)
            use_index: Utiliser l'index pour une recherche O(1) (recommandé pour colonnes numériques)
        
        Returns:
            Valeur minimale de la colonne
            
        Raises:
            JONXValidationError: Si la colonne n'existe pas ou est vide
            JONXIndexError: Si l'index est demandé mais n'existe pas
        """
        self._validate_field_name(field)
        
        if column is None:
            column = self.get_column(field)
        
        if len(column) == 0:
            raise JONXValidationError(
                f"La colonne '{field}' est vide",
                {"field": field}
            )
        
        if use_index:
            if field not in self.indexes:
                raise JONXIndexError(
                    f"L'index pour la colonne '{field}' n'existe pas",
                    {"field": field, "available_indexes": list(self.indexes.keys())}
                )
            try:
                idx = orjson.loads(zstd.ZstdDecompressor().decompress(self.indexes[field]))
                if len(idx) == 0:
                    raise JONXIndexError(
                        f"L'index pour la colonne '{field}' est vide",
                        {"field": field}
                    )
                return column[idx[0]]
            except (zstd.ZstdError, orjson.JSONDecodeError) as e:
                raise JONXIndexError(
                    f"Erreur lors de la lecture de l'index pour '{field}'",
                    {"field": field, "error": str(e)}
                ) from e
        
        return min(column)

    def find_max(self, field, column=None, use_index=False):
        """
        Trouve la valeur maximale d'une colonne.
        
        Args:
            field: Nom de la colonne
            column: Colonne pré-chargée (optionnel, récupérée automatiquement si None)
            use_index: Utiliser l'index pour une recherche O(1) (recommandé pour colonnes numériques)
        
        Returns:
            Valeur maximale de la colonne
            
        Raises:
            JONXValidationError: Si la colonne n'existe pas ou est vide
            JONXIndexError: Si l'index est demandé mais n'existe pas
        """
        self._validate_field_name(field)
        
        if column is None:
            column = self.get_column(field)
        
        if len(column) == 0:
            raise JONXValidationError(
                f"La colonne '{field}' est vide",
                {"field": field}
            )
        
        if use_index:
            if field not in self.indexes:
                raise JONXIndexError(
                    f"L'index pour la colonne '{field}' n'existe pas",
                    {"field": field, "available_indexes": list(self.indexes.keys())}
                )
            try:
                idx = orjson.loads(zstd.ZstdDecompressor().decompress(self.indexes[field]))
                if len(idx) == 0:
                    raise JONXIndexError(
                        f"L'index pour la colonne '{field}' est vide",
                        {"field": field}
                    )
                return column[idx[-1]]  # Dernier élément de l'index trié = maximum
            except (zstd.ZstdError, orjson.JSONDecodeError) as e:
                raise JONXIndexError(
                    f"Erreur lors de la lecture de l'index pour '{field}'",
                    {"field": field, "error": str(e)}
                ) from e
        
        return max(column)

    def sum(self, field, column=None):
        """
        Calcule la somme d'une colonne numérique.
        
        Args:
            field: Nom de la colonne
            column: Colonne pré-chargée (optionnel, récupérée automatiquement si None)
        
        Returns:
            Somme des valeurs de la colonne
        
        Raises:
            JONXValidationError: Si la colonne n'existe pas ou n'est pas numérique
        """
        self._validate_numeric_field(field)
        
        if column is None:
            column = self.get_column(field)
        
        if len(column) == 0:
            raise JONXValidationError(
                f"La colonne '{field}' est vide",
                {"field": field}
            )
        
        return sum(column)

    def avg(self, field, column=None):
        """
        Calcule la moyenne d'une colonne numérique.
        
        Args:
            field: Nom de la colonne
            column: Colonne pré-chargée (optionnel, récupérée automatiquement si None)
        
        Returns:
            Moyenne des valeurs de la colonne
        
        Raises:
            JONXValidationError: Si la colonne n'existe pas, n'est pas numérique ou est vide
        """
        self._validate_numeric_field(field)
        
        if column is None:
            column = self.get_column(field)
        
        if len(column) == 0:
            raise JONXValidationError(
                f"La colonne '{field}' est vide",
                {"field": field}
            )
        
        return sum(column) / len(column)

    def count(self, field=None):
        """
        Compte le nombre d'éléments dans une colonne ou le nombre total de lignes.
        
        Args:
            field: Nom de la colonne (optionnel, si None retourne le nombre total de lignes)
        
        Returns:
            Nombre d'éléments dans la colonne ou nombre total de lignes
            
        Raises:
            JONXValidationError: Si la colonne spécifiée n'existe pas
        """
        if field is None:
            # Retourne le nombre total de lignes
            if len(self.fields) == 0:
                return 0
            return len(self.get_column(self.fields[0]))
        
        self._validate_field_name(field)
        return len(self.get_column(field))

    def get_columns(self, field_names):
        """
        Récupère plusieurs colonnes en une seule opération.
        
        Args:
            field_names: Liste des noms de colonnes à récupérer
        
        Returns:
            Dictionnaire {nom_colonne: [valeurs]}
            
        Raises:
            JONXValidationError: Si une colonne n'existe pas ou si field_names n'est pas une liste
        """
        if not isinstance(field_names, (list, tuple)):
            raise JONXValidationError(
                "field_names doit être une liste ou un tuple",
                {"type": type(field_names).__name__}
            )
        
        if len(field_names) == 0:
            raise JONXValidationError(
                "La liste de colonnes ne peut pas être vide",
                {"field_names": field_names}
            )
        
        # Valider toutes les colonnes d'abord
        for field in field_names:
            self._validate_field_name(field)
        
        return {field: self.get_column(field) for field in field_names}
