import orjson
import zstandard as zstd
import os
from .exceptions import (
    JONXValidationError,
    JONXEncodeError,
    JONXFileError,
)
from .utils.encoder import encode_to_bytes

ZSTD = zstd.ZstdCompressor(level=7)

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
