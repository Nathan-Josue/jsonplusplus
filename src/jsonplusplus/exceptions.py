"""
Exceptions personnalisées pour jsonplusplus.
"""


class JONXError(Exception):
    """Exception de base pour toutes les erreurs JONX."""
    
    def __init__(self, message: str, details: dict = None):
        """
        Initialise une exception JONX.
        
        Args:
            message: Message d'erreur principal
            details: Dictionnaire optionnel avec des détails supplémentaires
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self):
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class JONXValidationError(JONXError):
    """Exception levée lors d'erreurs de validation des données."""
    pass


class JONXEncodeError(JONXError):
    """Exception levée lors d'erreurs d'encodage."""
    pass


class JONXDecodeError(JONXError):
    """Exception levée lors d'erreurs de décodage."""
    pass


class JONXFileError(JONXError):
    """Exception levée lors d'erreurs de manipulation de fichiers."""
    pass


class JONXSchemaError(JONXError):
    """Exception levée lors d'erreurs de schéma (colonnes manquantes, types incompatibles, etc.)."""
    pass


class JONXIndexError(JONXError):
    """Exception levée lors d'erreurs liées aux index."""
    pass

