import orjson
import zstandard as zstd
import struct

def decode_from_bytes(data: bytes) -> dict:
    """
    Décode un fichier JONX depuis des bytes en mémoire
    
    Args:
        data: Bytes du fichier JONX
        
    Returns:
        Dictionnaire contenant les métadonnées et les données JSON décodées
        
    Raises:
        ValueError: Si le fichier n'est pas au format JONX
    """
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

class JONXFile:
    def __init__(self, path):
        self.path = path
        self.fields = []
        self.types = {}
        self.compressed_columns = {}  # <- stocke chaque colonne compressée
        self.indexes = {}
        self._load_file()

    def _load_file(self):
        with open(self.path, "rb") as f:
            data = f.read()
        
        # Utiliser la fonction decode_from_bytes pour extraire les métadonnées
        result = decode_from_bytes(data)
        self.fields = result["fields"]
        self.types = result["types"]
        
        # Recharger les données pour extraire les colonnes compressées et index
        if not data.startswith(b"JONX"):
            raise ValueError("Le fichier n'est pas au format JONX")
        
        c = zstd.ZstdDecompressor()
        offset = 8
        
        # Lire le schéma (déjà fait, mais on doit avancer l'offset)
        schema_size = struct.unpack("I", data[offset:offset+4])[0]
        offset += 4
        offset += schema_size
        
        # Lire les colonnes compressées
        self.compressed_columns = {}
        for field in self.fields:
            col_size = struct.unpack("I", data[offset:offset+4])[0]
            offset += 4
            self.compressed_columns[field] = data[offset:offset+col_size]
            offset += col_size
        
        # Lire les index compressés
        num_indexes = struct.unpack("I", data[offset:offset+4])[0]
        offset += 4
        for _ in range(num_indexes):
            field_name_len = struct.unpack("I", data[offset:offset+4])[0]
            offset += 4
            field_name = data[offset:offset+field_name_len].decode("utf-8")
            offset += field_name_len
            idx_size = struct.unpack("I", data[offset:offset+4])[0]
            offset += 4
            self.indexes[field_name] = data[offset:offset+idx_size]
            offset += idx_size

    def get_column(self, field_name):
        if field_name not in self.compressed_columns:
            raise ValueError(f"Colonne {field_name} inexistante")
        compressed_data = self.compressed_columns[field_name]
        return self._decompress_column(field_name, compressed_data)

    def _decompress_column(self, field_name, compressed_data):
        c = zstd.ZstdDecompressor()
        packed = c.decompress(compressed_data)
        col_type = self.types[field_name]
        if col_type == "int32":
            n = len(packed) // 4
            return list(struct.unpack(f"{n}i", packed))
        elif col_type == "float32":
            n = len(packed) // 4
            return list(struct.unpack(f"{n}f", packed))
        elif col_type == "bool":
            return [bool(b) for b in packed]
        else:
            return orjson.loads(packed)

    def find_min(self, field_name, column_data=None, use_index=False):
        if column_data is None:
            column_data = self.get_column(field_name)
        if use_index and field_name in self.indexes:
            idx = orjson.loads(zstd.ZstdDecompressor().decompress(self.indexes[field_name]))
            min_idx = idx[0]
            return column_data[min_idx]
        return min(column_data)
