import pandas as pd
from sqlalchemy import create_engine

# lendo a raw
df = pd.read_csv("data/raw/train.csv")

# configurando banco
engine = create_engine(
    "postgresql+psycopg2://postgres:1205@localhost:5432/lab01_dw"
)

# salvando sem alteracoes - dado as-is
df.to_sql("credit_card_bronze", engine, if_exists="replace", index=False)


print("Bronze carregada")

