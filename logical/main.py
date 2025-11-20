from decoder import JONXFile
from encoder import jonx_encode

# Encoder
jonx_encode("../data/json/data.json", "json++/data_jonx.json++")

# Charger le fichier JONX
jonx_file = JONXFile("json++/data_jonx.json++")

# Accéder à la colonne "price"
col_prices = jonx_file.get_column("price")

# Trouver le prix minimum en utilisant l'index si disponible
min_price = jonx_file.find_min("price", col_prices, use_index=True)
print("Produit le moins cher :", min_price)
