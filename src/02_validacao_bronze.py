import pandas as pd
from sqlalchemy import create_engine

# raw
df_raw = pd.read_csv("data/raw/train.csv")

# bronze
engine = create_engine(
    "postgresql+psycopg2://postgres:1205@localhost:5432/lab01_dw"
)
df_bronze = pd.read_sql("SELECT * FROM credit_card_bronze", engine)

# validacoes
print("RAW shape:", df_raw.shape)
print("BRONZE shape:", df_bronze.shape)

print("\nColunas RAW:")
print(df_raw.columns.tolist())

print("\nColunas BRONZE:")
print(df_bronze.columns.tolist())

print("\nDados iguais?")
print(df_raw.equals(df_bronze))


