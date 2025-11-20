import orjson
import zstandard as zstd
import struct

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
        self.fields = schema["fields"]
        self.types = schema["types"]
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
