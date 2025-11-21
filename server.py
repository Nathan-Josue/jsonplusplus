from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from logical.encoder import detect_type, pack_column, encode_to_bytes
from logical.decoder import decode_from_bytes
import orjson
import zstandard as zstd

# Configuration de l'API
app = FastAPI(
    title="JONX API",
    description="API REST pour convertir entre JSON et JSON++ (JONX)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuration CORS pour permettre les requêtes depuis n'importe quelle origine
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modèles Pydantic pour les requêtes
class PreviewRequest(BaseModel):
    """Modèle pour la requête de prévisualisation"""
    data: List[Dict[str, Any]]

class EncodeRequest(BaseModel):
    """Modèle pour l'encodage JSON direct (alternative à l'upload de fichier)"""
    data: List[Dict[str, Any]]




# ==================== ENDPOINTS API ====================

@app.get("/")
async def root():
    """
    Endpoint racine - Informations sur l'API
    
    Returns:
        Message de bienvenue avec liens vers la documentation
    """
    return {
        "message": "JONX API - Convertisseur JSON ↔ JSON++",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "decode": "/api/decode (POST)",
            "encode": "/api/encode (POST)",
            "preview": "/api/preview (POST)"
        }
    }


@app.get("/health")
async def health_check():
    """
    Endpoint de santé pour vérifier que l'API est opérationnelle
    
    Returns:
        Statut de santé de l'API
    """
    return {
        "status": "healthy",
        "service": "JONX API",
        "version": "1.0.0"
    }


@app.post("/api/decode")
async def decode(file: UploadFile = File(...)):
    """
    Décode un fichier JONX et retourne les données JSON
    
    Args:
        file: Fichier JONX à décoder (upload)
        
    Returns:
        Dictionnaire contenant les métadonnées et les données JSON décodées
        
    Raises:
        HTTPException: Si le fichier n'est pas valide ou n'est pas au format JONX
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Aucun fichier sélectionné")
        
        # Lire les données du fichier
        file_data = await file.read()
        
        # Décoder le fichier JONX
        result = decode_from_bytes(file_data)
        
        return {
            "success": True,
            "file_name": file.filename,
            "file_size": len(file_data),
            "version": result["version"],
            "fields": result["fields"],
            "types": result["types"],
            "num_rows": result["num_rows"],
            "json_data": result["json_data"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du décodage: {str(e)}")


@app.post("/api/preview")
async def preview(request: PreviewRequest):
    """
    Prévisualise les métadonnées JONX sans générer le fichier
    
    Args:
        request: Données JSON à analyser
        
    Returns:
        Métadonnées estimées du fichier JONX qui serait généré
        
    Raises:
        HTTPException: Si les données JSON sont invalides
    """
    try:
        data = request.data
        if len(data) == 0:
            raise HTTPException(status_code=400, detail="La liste JSON ne peut pas être vide")
        
        # Détection automatique des colonnes
        fields = list(data[0].keys())
        columns = {field: [p.get(field) for p in data] for field in fields}
        
        # Détection des types
        types = {field: detect_type(vals) for field, vals in columns.items()}
        
        # Estimer la taille (approximation)
        c = zstd.ZstdCompressor(level=3)
        estimated_size = 8  # Header
        schema = {"fields": fields, "types": types}
        schema_compressed = c.compress(orjson.dumps(schema))
        estimated_size += 4 + len(schema_compressed)  # Schema
        
        for field in fields:
            packed = pack_column(columns[field], types[field])
            compressed = c.compress(packed)
            estimated_size += 4 + len(compressed)  # Colonne
        
        # Index (approximation)
        num_indexes = sum(1 for t in types.values() if t in ["int32", "float32"])
        estimated_size += 4  # Nombre d'index
        for field, col_type in types.items():
            if col_type in ["int32", "float32"]:
                sorted_index = sorted(range(len(columns[field])), key=lambda i: columns[field][i])
                idx_compressed = c.compress(orjson.dumps(sorted_index))
                estimated_size += 4 + len(field.encode("utf-8")) + 4 + len(idx_compressed)
        
        return {
            "success": True,
            "version": 1,
            "fields": fields,
            "types": types,
            "num_rows": len(data),
            "estimated_size": estimated_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la prévisualisation: {str(e)}")


@app.post("/api/encode")
async def encode(file: UploadFile = File(...)):
    """
    Encode un fichier JSON en format JONX
    
    Args:
        file: Fichier JSON à encoder (upload)
        
    Returns:
        Fichier JONX binaire en téléchargement
        
    Raises:
        HTTPException: Si le fichier JSON est invalide
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Aucun fichier sélectionné")
        
        # Lire et parser le JSON
        file_data = await file.read()
        json_data = orjson.loads(file_data)
        
        if not isinstance(json_data, list):
            raise HTTPException(status_code=400, detail="Le JSON doit être une liste d'objets")
        
        if len(json_data) == 0:
            raise HTTPException(status_code=400, detail="La liste JSON ne peut pas être vide")
        
        # Encoder en format JONX
        jonx_bytes = encode_to_bytes(json_data)
        
        # Générer le nom du fichier de sortie
        output_filename = file.filename.rsplit('.', 1)[0] + '.json++'
        
        # Retourner le fichier en tant que réponse
        return Response(
            content=jonx_bytes,
            media_type='application/octet-stream',
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"'
            }
        )
        
    except orjson.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Erreur de parsing JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'encodage: {str(e)}")


@app.post("/api/encode/json")
async def encode_from_json(request: EncodeRequest):
    """
    Encode des données JSON (envoyées dans le body) en format JONX
    
    Args:
        request: Données JSON à encoder
        
    Returns:
        Fichier JONX binaire en téléchargement
        
    Raises:
        HTTPException: Si les données JSON sont invalides
    """
    try:
        json_data = request.data
        
        if not isinstance(json_data, list):
            raise HTTPException(status_code=400, detail="Le JSON doit être une liste d'objets")
        
        if len(json_data) == 0:
            raise HTTPException(status_code=400, detail="La liste JSON ne peut pas être vide")
        
        # Encoder en format JONX
        jonx_bytes = encode_to_bytes(json_data)
        
        # Retourner le fichier en tant que réponse
        return Response(
            content=jonx_bytes,
            media_type='application/octet-stream',
            headers={
                "Content-Disposition": 'attachment; filename="output.json++"'
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'encodage: {str(e)}")


if __name__ == '__main__':
    import uvicorn
    print("JONX|JSON++ API démarrée sur http://localhost:8000")
    print("Documentation disponible sur http://localhost:8000/docs")
    print("Redoc disponible sur http://localhost:8000/redoc")
    uvicorn.run(app, host="0.0.0.0", port=8000)
