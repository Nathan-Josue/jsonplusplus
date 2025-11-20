from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from encoder import detect_type, pack_column
import io
import os
import orjson
import zstandard as zstd
import struct

app = FastAPI(title="JONX Converter", description="Convertisseur JSON ↔ JSON++ (JONX)")

# Configuration CORS pour permettre les requêtes depuis le navigateur
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PreviewRequest(BaseModel):
    data: List[Dict[str, Any]]

# Fonction helper pour servir les fichiers HTML
def get_html_file(filename: str) -> str:
    """Récupère le contenu d'un fichier HTML depuis le dossier template"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, 'template /', filename)
    
    if not os.path.exists(html_path):
        # Essayer aussi sans espace
        html_path_alt = os.path.join(base_dir, 'template', filename)
        if os.path.exists(html_path_alt):
            html_path = html_path_alt
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Fichier {filename} non trouvé"
            )
    
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la lecture de {filename}: {str(e)}"
        )

# Fonction pour décoder JONX depuis des bytes en mémoire
def decode_jonx_from_bytes(data):
    """Décode un fichier JONX depuis des bytes en mémoire"""
    if not data.startswith(b"JONX"):
        raise ValueError("Le fichier n'est pas au format JONX")
    
    version = struct.unpack("I", data[4:8])[0]
    c = zstd.ZstdDecompressor()
    offset = 8
    
    # Lire le schéma
    schema_size = struct.unpack("I", data[offset:offset+4])[0]
    offset += 4
    schema_compressed = data[offset:offset+schema_size]
    schema = orjson.loads(c.decompress(schema_compressed))
    fields = schema["fields"]
    types = schema["types"]
    offset += schema_size
    
    # Lire les colonnes
    columns = {}
    for field in fields:
        col_size = struct.unpack("I", data[offset:offset+4])[0]
        offset += 4
        col_compressed = data[offset:offset+col_size]
        offset += col_size
        
        # Décompresser la colonne
        packed = c.decompress(col_compressed)
        col_type = types[field]
        
        if col_type == "int32":
            n = len(packed) // 4
            columns[field] = list(struct.unpack(f"{n}i", packed))
        elif col_type == "float32":
            n = len(packed) // 4
            columns[field] = list(struct.unpack(f"{n}f", packed))
        elif col_type == "bool":
            columns[field] = [bool(b) for b in packed]
        else:
            columns[field] = orjson.loads(packed)
    
    # Lire les index (on les ignore pour la reconstruction JSON)
    num_indexes = struct.unpack("I", data[offset:offset+4])[0]
    offset += 4
    for _ in range(num_indexes):
        field_name_len = struct.unpack("I", data[offset:offset+4])[0]
        offset += 4
        offset += field_name_len
        idx_size = struct.unpack("I", data[offset:offset+4])[0]
        offset += 4
        offset += idx_size
    
    # Reconstruire les objets JSON
    num_rows = len(columns[fields[0]]) if fields else 0
    json_data = []
    for i in range(num_rows):
        obj = {}
        for field in fields:
            obj[field] = columns[field][i]
        json_data.append(obj)
    
    return {
        "version": version,
        "fields": fields,
        "types": types,
        "num_rows": num_rows,
        "json_data": json_data
    }

@app.get("/", response_class=HTMLResponse)
async def index():
    """Sert la page d'accueil"""
    content = get_html_file('index.html')
    return HTMLResponse(content=content)

@app.get("/about.html", response_class=HTMLResponse)
async def about():
    """Sert la page À propos"""
    content = get_html_file('about.html')
    return HTMLResponse(content=content)

@app.get("/contact.html", response_class=HTMLResponse)
async def contact():
    """Sert la page Contact"""
    content = get_html_file('contact.html')
    return HTMLResponse(content=content)

@app.post("/api/decode")
async def decode(file: UploadFile = File(...)):
    """API endpoint pour décoder un fichier JONX"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Aucun fichier sélectionné")
        
        # Lire les données du fichier
        file_data = await file.read()
        
        # Décoder le fichier JONX
        result = decode_jonx_from_bytes(file_data)
        
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/preview")
async def preview(request: PreviewRequest):
    """API endpoint pour prévisualiser les métadonnées JSON++ sans générer le fichier"""
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/encode")
async def encode(file: UploadFile = File(...)):
    """API endpoint pour encoder un fichier JSON en JONX"""
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
        
        # Détection automatique des colonnes
        fields = list(json_data[0].keys())
        columns = {field: [p.get(field) for p in json_data] for field in fields}
        
        # Détection des types
        types = {field: detect_type(vals) for field, vals in columns.items()}
        
        # Compression des colonnes
        c = zstd.ZstdCompressor(level=3)
        compressed_columns = {}
        for field, vals in columns.items():
            packed = pack_column(vals, types[field])
            compressed_columns[field] = c.compress(packed)
        
        # Création d'index automatique pour colonnes numériques
        indexes = {}
        for field, col_type in types.items():
            if col_type in ["int32", "float32"]:
                sorted_index = sorted(range(len(columns[field])), key=lambda i: columns[field][i])
                indexes[field] = c.compress(orjson.dumps(sorted_index))
        
        # Créer le fichier JONX en mémoire
        output = io.BytesIO()
        
        # Header
        output.write(b"JONX")
        output.write(struct.pack("I", 1))  # version
        
        # Schema JSON compressé
        schema = {"fields": fields, "types": types}
        schema_compressed = c.compress(orjson.dumps(schema))
        output.write(struct.pack("I", len(schema_compressed)))
        output.write(schema_compressed)
        
        # Colonnes compressées
        for field in fields:
            col_data = compressed_columns[field]
            output.write(struct.pack("I", len(col_data)))
            output.write(col_data)
        
        # Index compressés
        output.write(struct.pack("I", len(indexes)))
        for field, idx in indexes.items():
            output.write(struct.pack("I", len(field)))
            output.write(field.encode("utf-8"))
            output.write(struct.pack("I", len(idx)))
            output.write(idx)
        
        output.seek(0)
        
        # Générer le nom du fichier de sortie
        output_filename = file.filename.rsplit('.', 1)[0] + '.json++'
        
        # Retourner le fichier en tant que réponse
        return Response(
            content=output.read(),
            media_type='application/octet-stream',
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"'
            }
        )
        
    except orjson.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Erreur de parsing JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    print("🚀 Serveur JONX Converter démarré sur http://localhost:8000")
    print("📂 Ouvrez votre navigateur et accédez à http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
