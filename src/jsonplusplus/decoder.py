import orjson
import zstandard as zstd
import struct
import numpy as np
import os
from .utils.decoder import decode_from_bytes


from .exceptions import (
    JONXDecodeError,
    JONXFileError,
    JONXValidationError,
    JONXIndexError
)

# Types numériques supportés
NUMERIC_TYPES = {
    "int8", "int16", "int32", "int64",
    "uint8", "uint16", "uint32", "uint64",
    "float16", "float32", "float64"
}

# Tous les types supportés
SUPPORTED_TYPES = NUMERIC_TYPES | {
    "bool", "str", "json", "binary",
    "uuid", "date", "datetime", "timestamp_ms",
    "enum", "string_dict"
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

        # Gérer les types nullable
        base_type = col_type
        if isinstance(col_type, str) and col_type.startswith("nullable<") and col_type.endswith(">"):
            base_type = col_type[9:-1]

        if base_type not in NUMERIC_TYPES:
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

        # Mapping des types numériques vers leurs formats struct
        numeric_formats = {
            "int8": ("b", 1),
            "int16": ("h", 2),
            "int32": ("i", 4),
            "int64": ("q", 8),
            "uint8": ("B", 1),
            "uint16": ("H", 2),
            "uint32": ("I", 4),
            "uint64": ("Q", 8),
            "float32": ("f", 4),
            "float64": ("d", 8),
        }

        try:
            # Types numériques standards
            if t in numeric_formats:
                fmt, size = numeric_formats[t]
                n = len(packed) // size
                return list(struct.unpack(f"{n}{fmt}", packed))

            # float16 nécessite numpy
            if t == "float16":
                arr = np.frombuffer(packed, dtype=np.float16)
                return arr.astype(np.float32).tolist()

            # bool
            if t == "bool":
                return [bool(b) for b in packed]

            # Tous les autres types (str, json, uuid, date, datetime, enum, string_dict, binary, etc.)
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

    # ============================================================================
    # MÉTHODES UTILITAIRES
    # ============================================================================

    def info(self):
        """
        Retourne un dictionnaire avec toutes les métadonnées du fichier JONX.
        
        Returns:
            dict: Dictionnaire contenant :
                - path: Chemin du fichier
                - version: Version du format JONX
                - num_rows: Nombre de lignes
                - num_columns: Nombre de colonnes
                - fields: Liste des noms de colonnes
                - types: Dictionnaire des types par colonne
                - indexes: Liste des colonnes avec index
                - file_size: Taille du fichier en bytes
        """
        try:
            file_size = os.path.getsize(self.path)
        except OSError:
            file_size = None
        
        return {
            "path": self.path,
            "version": 1,  # Version actuelle du format
            "num_rows": self.count() if len(self.fields) > 0 else 0,
            "num_columns": len(self.fields),
            "fields": self.fields.copy(),
            "types": self.types.copy(),
            "indexes": list(self.indexes.keys()),
            "file_size": file_size
        }

    def has_index(self, field):
        """
        Vérifie si une colonne a un index disponible.
        
        Args:
            field: Nom de la colonne à vérifier
        
        Returns:
            bool: True si la colonne a un index, False sinon
            
        Raises:
            JONXValidationError: Si la colonne n'existe pas
        """
        self._validate_field_name(field)
        return field in self.indexes

    def is_numeric(self, field):
        """
        Vérifie si une colonne est de type numérique.

        Args:
            field: Nom de la colonne à vérifier

        Returns:
            bool: True si la colonne est numérique, False sinon

        Raises:
            JONXValidationError: Si la colonne n'existe pas
        """
        self._validate_field_name(field)
        col_type = self.types.get(field)

        # Gérer les types nullable
        base_type = col_type
        if isinstance(col_type, str) and col_type.startswith("nullable<") and col_type.endswith(">"):
            base_type = col_type[9:-1]

        return base_type in NUMERIC_TYPES

    def check_schema(self):
        """
        Vérifie la cohérence du schéma du fichier JONX.
        
        Returns:
            dict: Dictionnaire avec les résultats de la vérification :
                - valid: bool - True si le schéma est valide
                - errors: list - Liste des erreurs trouvées
                - warnings: list - Liste des avertissements
        
        Raises:
            JONXFileError: Si le fichier ne peut pas être lu
        """
        errors = []
        warnings = []
        
        # Vérifier que tous les champs ont un type défini
        for field in self.fields:
            if field not in self.types:
                errors.append(f"Le champ '{field}' n'a pas de type défini")
        
        # Vérifier que tous les types correspondent à des champs
        for field_name, field_type in self.types.items():
            if field_name not in self.fields:
                errors.append(f"Le type '{field_type}' est défini pour un champ inexistant: '{field_name}'")
        
        # Vérifier que les index correspondent à des colonnes numériques
        for index_field in self.indexes.keys():
            if index_field not in self.fields:
                errors.append(f"L'index pour le champ inexistant '{index_field}' existe")
            elif not self.is_numeric(index_field):
                warnings.append(f"L'index pour le champ non-numérique '{index_field}' existe (inhabituel)")
        
        # Vérifier que les colonnes compressées existent pour tous les champs
        for field in self.fields:
            if field not in self.compressed_columns:
                errors.append(f"La colonne '{field}' n'a pas de données compressées")
        
        # Vérifier la cohérence des longueurs (si possible sans décompression)
        if len(self.fields) > 0:
            try:
                first_col = self.get_column(self.fields[0])
                expected_length = len(first_col)
                
                for field in self.fields[1:]:
                    col = self.get_column(field)
                    if len(col) != expected_length:
                        errors.append(
                            f"La colonne '{field}' a une longueur incohérente "
                            f"(attendu: {expected_length}, obtenu: {len(col)})"
                        )
            except Exception as e:
                warnings.append(f"Impossible de vérifier la cohérence des longueurs: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def validate(self):
        """
        Valide l'intégrité complète du fichier JONX.
        
        Cette méthode effectue une validation approfondie en :
        - Vérifiant le schéma
        - Vérifiant l'intégrité des données
        - Tentant de décompresser toutes les colonnes
        - Vérifiant les index
        
        Returns:
            dict: Dictionnaire avec les résultats de la validation :
                - valid: bool - True si le fichier est valide
                - errors: list - Liste des erreurs trouvées
                - warnings: list - Liste des avertissements
        
        Raises:
            JONXFileError: Si le fichier ne peut pas être lu
            JONXDecodeError: Si le fichier est corrompu
        """
        errors = []
        warnings = []
        
        # 1. Vérifier le schéma
        schema_check = self.check_schema()
        errors.extend(schema_check["errors"])
        warnings.extend(schema_check["warnings"])
        
        # 2. Vérifier que le fichier existe et est lisible
        if not os.path.exists(self.path):
            errors.append(f"Le fichier n'existe pas: {self.path}")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings
            }
        
        if not os.access(self.path, os.R_OK):
            errors.append(f"Permission de lecture refusée: {self.path}")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings
            }
        
        # 3. Vérifier que toutes les colonnes peuvent être décompressées
        for field in self.fields:
            try:
                column = self.get_column(field)
                if len(column) == 0:
                    warnings.append(f"La colonne '{field}' est vide")
            except Exception as e:
                errors.append(f"Erreur lors de la décompression de la colonne '{field}': {str(e)}")
        
        # 4. Vérifier que tous les index peuvent être lus
        for index_field in self.indexes.keys():
            try:
                idx = orjson.loads(zstd.ZstdDecompressor().decompress(self.indexes[index_field]))
                if len(idx) == 0:
                    warnings.append(f"L'index pour '{index_field}' est vide")
                elif len(idx) != self.count():
                    errors.append(
                        f"L'index pour '{index_field}' a une longueur incohérente "
                        f"(attendu: {self.count()}, obtenu: {len(idx)})"
                    )
            except Exception as e:
                errors.append(f"Erreur lors de la lecture de l'index '{index_field}': {str(e)}")
        
        # 5. Vérifier la cohérence des types
        for field, col_type in self.types.items():
            # Gérer les types nullable
            base_type = col_type
            if isinstance(col_type, str) and col_type.startswith("nullable<") and col_type.endswith(">"):
                base_type = col_type[9:-1]

            if base_type not in SUPPORTED_TYPES:
                warnings.append(f"Type inconnu pour la colonne '{field}': {col_type}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
