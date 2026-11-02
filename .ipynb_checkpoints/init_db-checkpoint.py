import pandas as pd
import sqlite3
from pathlib import Path

# Define a raiz do projeto baseada na localização deste script
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "raw_data"
DB_PATH = BASE_DIR / "data" / "emporio_musica.db"

# Carrega todas as tabelas disponiveis
df_prod = pd.read_csv(DATA_DIR / "products.csv")
df_categ = pd.read_csv(DATA_DIR / "categories.csv")
df_ord = pd.read_csv(DATA_DIR / "orders.csv")
df_cust = pd.read_csv(DATA_DIR / "customers.csv")
df_item = pd.read_csv(DATA_DIR / "order_items.csv")
df_promo = pd.read_csv(DATA_DIR / "promotions.csv")

# Converte as colunas de id para string, facilitando as consultando no SQLite
df_prod['product_id'] = df_prod['product_id'].astype(str).str.strip()
df_prod['category_id'] = df_prod ['category_id'].astype(str).str.strip()
df_categ['category_id'] = df_categ ['category_id'].astype(str).str.strip()
df_ord['order_id'] = df_ord ['order_id'].astype(str).str.strip()
df_ord['customer_id'] = df_ord ['customer_id'].astype(str).str.strip()
df_item['order_id'] = df_item['order_id'].astype(str).str.strip()
df_item['product_id'] = df_item['product_id'].astype(str).str.strip()
df_promo['product_id'] = df_promo['product_id'].astype(str).str.strip()
df_promo['promotion_id'] = df_promo['promotion_id'].astype(str).str.strip()
df_cust['customer_id'] = df_cust['customer_id'].astype(str).str.strip()

df_categ = df_categ.rename(columns={"name": "category_name"})

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Conecta o SQLite com o arquivo local
conn = sqlite3.connect(DB_PATH)
# Salva os DataFrames na memoria em SQL
df_prod.to_sql("products", conn, if_exists="replace", index=False)
df_categ.to_sql("categories", conn, if_exists="replace", index=False)
df_ord.to_sql("orders", conn, if_exists="replace", index=False)
df_cust.to_sql("customers", conn, if_exists="replace", index=False)
df_item.to_sql("order_items", conn, if_exists="replace", index=False)
df_promo.to_sql("promotions", conn, if_exists="replace", index=False)
# Fecha a conexao com SQLite
conn.close()

print(f"Banco de dados inicializado com sucesso em: {DB_PATH}")