import os
import pandas as pd
from sqlalchemy import create_engine, text

# configurando banco
gold_dir = "data/gold"
silver_parquet_path = "data/silver/credit_card_silver.parquet"

os.makedirs(gold_dir, exist_ok=True)

engine = create_engine(
    "postgresql+psycopg2://postgres:1205@localhost:5432/lab01_dw"
)

# lendo tabela silver
df = pd.read_parquet(silver_parquet_path)

df["trans_date_trans_time"] = pd.to_datetime(df["trans_date_trans_time"], errors="coerce")
df["dob"] = pd.to_datetime(df["dob"], errors="coerce")

df = df.dropna(subset=["trans_date_trans_time"]).copy()

df["idade"] = ((df["trans_date_trans_time"] - df["dob"]).dt.days / 365.25).fillna(0).astype(int)

df["data"] = df["trans_date_trans_time"].dt.date

# criando dimensoes

# dim_tempo
dim_tempo = df[["trans_date_trans_time", "data"]].drop_duplicates().copy()
dim_tempo["ano"] = dim_tempo["trans_date_trans_time"].dt.year
dim_tempo["trimestre"] = dim_tempo["trans_date_trans_time"].dt.quarter
dim_tempo["mes"] = dim_tempo["trans_date_trans_time"].dt.month
dim_tempo["dia"] = dim_tempo["trans_date_trans_time"].dt.day
dim_tempo["hora"] = dim_tempo["trans_date_trans_time"].dt.hour
dim_tempo["dia_semana_num"] = dim_tempo["trans_date_trans_time"].dt.dayofweek
dim_tempo["dia_semana"] = dim_tempo["trans_date_trans_time"].dt.day_name()
dim_tempo["fim_de_semana"] = dim_tempo["dia_semana_num"].isin([5, 6])

dim_tempo = dim_tempo.rename(columns={"trans_date_trans_time": "data_hora"})
dim_tempo = dim_tempo.reset_index(drop=True)
dim_tempo["tempo_sk"] = dim_tempo.index + 1

dim_tempo = dim_tempo[
    [
        "tempo_sk", "data_hora", "data", "ano", "trimestre", "mes",
        "dia", "hora", "dia_semana_num", "dia_semana", "fim_de_semana"
    ]
]

# dim_cliente 
cols_cliente = ["cc_num", "first", "last", "gender", "job", "dob", "idade"]
dim_cliente = df[cols_cliente].drop_duplicates().copy()
dim_cliente = dim_cliente.reset_index(drop=True)
dim_cliente["cliente_sk"] = dim_cliente.index + 1

dim_cliente = dim_cliente[
    ["cliente_sk", "cc_num", "first", "last", "gender", "job", "dob", "idade"]
]

# dim_categoria 
dim_categoria = df[["category"]].drop_duplicates().copy()
dim_categoria = dim_categoria.reset_index(drop=True)
dim_categoria["categoria_sk"] = dim_categoria.index + 1
dim_categoria = dim_categoria[["categoria_sk", "category"]]

# dim_merchant 
cols_merchant = ["merchant", "merch_lat", "merch_long"]
dim_merchant = df[cols_merchant].drop_duplicates().copy()
dim_merchant = dim_merchant.reset_index(drop=True)
dim_merchant["merchant_sk"] = dim_merchant.index + 1

dim_merchant = dim_merchant[
    ["merchant_sk", "merchant", "merch_lat", "merch_long"]
]

# dim_localizacao 
cols_localizacao = ["city", "state", "zip", "lat", "long", "city_pop"]
dim_localizacao = df[cols_localizacao].drop_duplicates().copy()
dim_localizacao = dim_localizacao.reset_index(drop=True)
dim_localizacao["localizacao_sk"] = dim_localizacao.index + 1

dim_localizacao = dim_localizacao[
    ["localizacao_sk", "city", "state", "zip", "lat", "long", "city_pop"]
]

# montando tabela fatp
fato = df.copy()

fato = fato.merge(
    dim_tempo[["tempo_sk", "data_hora"]],
    left_on="trans_date_trans_time",
    right_on="data_hora",
    how="left"
)

fato = fato.merge(
    dim_cliente[["cliente_sk", "cc_num", "first", "last", "gender", "job", "dob", "idade"]],
    on=["cc_num", "first", "last", "gender", "job", "dob", "idade"],
    how="left"
)

fato = fato.merge(
    dim_categoria,
    on="category",
    how="left"
)

fato = fato.merge(
    dim_merchant,
    on=["merchant", "merch_lat", "merch_long"],
    how="left"
)

fato = fato.merge(
    dim_localizacao,
    on=["city", "state", "zip", "lat", "long", "city_pop"],
    how="left"
)

fato_transacoes = fato[
    [
        "trans_num",
        "tempo_sk",
        "cliente_sk",
        "categoria_sk",
        "merchant_sk",
        "localizacao_sk",
        "amt",
        "is_fraud",
        "unix_time"
    ]
].copy()

fato_transacoes["quantidade_transacoes"] = 1
fato_transacoes = fato_transacoes.reset_index(drop=True)
fato_transacoes["transacao_sk"] = fato_transacoes.index + 1

fato_transacoes = fato_transacoes[
    [
        "transacao_sk",
        "trans_num",
        "tempo_sk",
        "cliente_sk",
        "categoria_sk",
        "merchant_sk",
        "localizacao_sk",
        "amt",
        "is_fraud",
        "unix_time",
        "quantidade_transacoes"
    ]
]

# criando tabelas no postgresql
ddl = """
DROP TABLE IF EXISTS fato_transacoes;
DROP TABLE IF EXISTS dim_tempo;
DROP TABLE IF EXISTS dim_cliente;
DROP TABLE IF EXISTS dim_categoria;
DROP TABLE IF EXISTS dim_merchant;
DROP TABLE IF EXISTS dim_localizacao;

CREATE TABLE dim_tempo (
    tempo_sk INTEGER PRIMARY KEY,
    data_hora TIMESTAMP,
    data DATE,
    ano INTEGER,
    trimestre INTEGER,
    mes INTEGER,
    dia INTEGER,
    hora INTEGER,
    dia_semana_num INTEGER,
    dia_semana VARCHAR(20),
    fim_de_semana BOOLEAN
);

CREATE TABLE dim_cliente (
    cliente_sk INTEGER PRIMARY KEY,
    cc_num BIGINT,
    first VARCHAR(100),
    last VARCHAR(100),
    gender VARCHAR(20),
    job TEXT,
    dob TIMESTAMP,
    idade INTEGER
);

CREATE TABLE dim_categoria (
    categoria_sk INTEGER PRIMARY KEY,
    category VARCHAR(100)
);

CREATE TABLE dim_merchant (
    merchant_sk INTEGER PRIMARY KEY,
    merchant VARCHAR(255),
    merch_lat DOUBLE PRECISION,
    merch_long DOUBLE PRECISION
);

CREATE TABLE dim_localizacao (
    localizacao_sk INTEGER PRIMARY KEY,
    city VARCHAR(100),
    state VARCHAR(10),
    zip INTEGER,
    lat DOUBLE PRECISION,
    long DOUBLE PRECISION,
    city_pop INTEGER
);

CREATE TABLE fato_transacoes (
    transacao_sk INTEGER PRIMARY KEY,
    trans_num VARCHAR(100),
    tempo_sk INTEGER REFERENCES dim_tempo(tempo_sk),
    cliente_sk INTEGER REFERENCES dim_cliente(cliente_sk),
    categoria_sk INTEGER REFERENCES dim_categoria(categoria_sk),
    merchant_sk INTEGER REFERENCES dim_merchant(merchant_sk),
    localizacao_sk INTEGER REFERENCES dim_localizacao(localizacao_sk),
    amt DOUBLE PRECISION,
    is_fraud INTEGER,
    unix_time BIGINT,
    quantidade_transacoes INTEGER
);
"""

with engine.begin() as conn:
    conn.execute(text(ddl))

# carga as tabelas
dim_tempo.to_sql("dim_tempo", engine, if_exists="append", index=False)
dim_cliente.to_sql("dim_cliente", engine, if_exists="append", index=False)
dim_categoria.to_sql("dim_categoria", engine, if_exists="append", index=False)
dim_merchant.to_sql("dim_merchant", engine, if_exists="append", index=False)
dim_localizacao.to_sql("dim_localizacao", engine, if_exists="append", index=False)
fato_transacoes.to_sql("fato_transacoes", engine, if_exists="append", index=False)

# salvando copias em parquet
dim_tempo.to_parquet(os.path.join(gold_dir, "dim_tempo.parquet"), index=False)
dim_cliente.to_parquet(os.path.join(gold_dir, "dim_cliente.parquet"), index=False)
dim_categoria.to_parquet(os.path.join(gold_dir, "dim_categoria.parquet"), index=False)
dim_merchant.to_parquet(os.path.join(gold_dir, "dim_merchant.parquet"), index=False)
dim_localizacao.to_parquet(os.path.join(gold_dir, "dim_localizacao.parquet"), index=False)
fato_transacoes.to_parquet(os.path.join(gold_dir, "fato_transacoes.parquet"), index=False)

print("Camada Gold criada com sucesso!")
print("Tabelas criadas no PostgreSQL:")
print("- dim_tempo")
print("- dim_cliente")
print("- dim_categoria")
print("- dim_merchant")
print("- dim_localizacao")
print("- fato_transacoes")