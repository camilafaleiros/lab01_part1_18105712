import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine
import warnings

warnings.filterwarnings("ignore")

# definicao de caminhos e arquivos de saida
bronze_table = "credit_card_bronze"
silver_dir = "data/silver"
graficos_dir = os.path.join(silver_dir, "graficos")
parquet_path = os.path.join(silver_dir, "credit_card_silver.parquet")
relatorio_path = os.path.join(silver_dir, "relatorio_silver.md")

os.makedirs(silver_dir, exist_ok=True)
os.makedirs(graficos_dir, exist_ok=True)

def to_snake_case(nome):
    nome = nome.strip().lower()
    nome = re.sub(r"[^\w\s]", "", nome)
    nome = re.sub(r"\s+", "_", nome)
    return nome

def salvar_grafico(caminho):
    plt.tight_layout()
    plt.savefig(caminho, bbox_inches="tight")
    plt.close()


# lendo tabela bronze
engine = create_engine(
    "postgresql+psycopg2://postgres:1205@localhost:5432/lab01_dw"
)

df = pd.read_sql(f"SELECT * FROM {bronze_table}", engine)

linhas_antes = df.shape[0]
colunas_antes = df.shape[1]
tipos_antes = df.dtypes.astype(str)
nulos_antes = df.isnull().sum()
estatisticas_antes = df.describe(include="all").transpose()

insights = []

total_linhas = df.shape[0]

# identificacao de problemas (nulos e tipos categoricos)
for col in nulos_antes.index:
    nulos = nulos_antes[col]
    if nulos > 0:
        perc = (nulos / total_linhas) * 100
        insights.append(f"A coluna '{col}' possui {perc:.2f}% de valores nulos.")

for col, tipo in tipos_antes.items():
    if "object" in tipo:
        insights.append(f"A coluna '{col}' é categórica (object) e pode precisar de padronização.")

# padronizacao de colunas
df.columns = [to_snake_case(col) for col in df.columns]

# remocao de colunas irrelevantes
if "unnamed_0" in df.columns:
    insights.append("A coluna 'unnamed_0' aparenta ser um índice e pode ser removida.")
    df = df.drop(columns=["unnamed_0"])

# conversão de datas
df["trans_date_trans_time"] = pd.to_datetime(df["trans_date_trans_time"], errors="coerce")
df["dob"] = pd.to_datetime(df["dob"], errors="coerce")

insights.append("A coluna 'trans_date_trans_time' foi convertida para datetime para facilitar análises temporais.")
insights.append("A coluna 'dob' foi convertida para datetime.")

# tratamento de valores nulos
colunas_numericas = df.select_dtypes(include=["int64", "float64"]).columns
for col in colunas_numericas:
    if df[col].isnull().sum() > 0:
        df[col] = df[col].fillna(df[col].median())

colunas_categoricas = df.select_dtypes(include=["object"]).columns
for col in colunas_categoricas:
    if df[col].isnull().sum() > 0:
        df[col] = df[col].fillna("desconhecido")

# remoção de duplicatas
duplicatas_removidas = df.duplicated().sum()
df = df.drop_duplicates()

if duplicatas_removidas > 0:
    insights.append(f"Foram encontradas e removidas {duplicatas_removidas} linhas duplicadas.")
else:
    insights.append("Não foram encontradas linhas duplicadas.")

linhas_depois = df.shape[0]
colunas_depois = df.shape[1]
tipos_depois = df.dtypes.astype(str)
nulos_depois = df.isnull().sum()

# salva dados tratados em parquet e no banco
df.to_parquet(parquet_path, index=False)
df.to_sql("credit_card_silver", engine, if_exists="replace", index=False)


# gerando graficos
df["city"].value_counts().head(10).sort_values().plot(kind="barh")
plt.title("Top 10 Cidades com Mais Transações")
plt.xlabel("Quantidade")
plt.ylabel("Cidade")
salvar_grafico(os.path.join(graficos_dir, "01_cidades.png"))

np.log1p(df["amt"]).plot(kind="hist", bins=30)
plt.title("Distribuição do Valor das Transações (escala log)")
plt.xlabel("log(valor)")
plt.ylabel("Frequência")
salvar_grafico(os.path.join(graficos_dir, "02_valor_transacoes.png"))

df["category"].value_counts().head(10).sort_values().plot(kind="barh")
plt.title("Top 10 Categorias")
plt.xlabel("Quantidade")
salvar_grafico(os.path.join(graficos_dir, "03_categorias.png"))

df["gender"].value_counts(normalize=True).plot(kind="bar")
plt.title("Proporção por Gênero")
plt.ylabel("Proporção")
salvar_grafico(os.path.join(graficos_dir, "04_genero.png"))

df["state"].value_counts().head(10).sort_values().plot(kind="barh")
plt.title("Top 10 Estados")
plt.xlabel("Quantidade")
salvar_grafico(os.path.join(graficos_dir, "05_estados.png"))


# gerando relatorio
with open(relatorio_path, "w", encoding="utf-8") as f:
    f.write("# Relatório da Camada Silver\n\n")
    f.write("## 1. Visão Geral\n\n")
    f.write(f"- Linhas antes da limpeza: {linhas_antes}\n")
    f.write(f"- Colunas antes da limpeza: {colunas_antes}\n")
    f.write(f"- Linhas após a limpeza: {linhas_depois}\n")
    f.write(f"- Colunas após a limpeza: {colunas_depois}\n")
    f.write(f"- Duplicatas removidas: {duplicatas_removidas}\n\n")

    f.write("## 2. Tipos das Colunas\n\n")
    f.write(tipos_antes.to_frame("tipo").to_markdown())
    f.write("\n\n")

    f.write("## 3. Contagem de Nulos Antes da Limpeza\n\n")
    f.write(nulos_antes.to_frame("nulos").to_markdown())
    f.write("\n\n")

    f.write("## 4. Estatísticas Descritivas\n\n")
    f.write(estatisticas_antes.to_markdown())
    f.write("\n\n")

    f.write("## 5. Contagem de Nulos Após a Limpeza\n\n")
    f.write(nulos_depois.to_frame("nulos").to_markdown())
    f.write("\n\n")

    f.write("## 6. Limpezas Realizadas\n\n")
    f.write("- Padronização dos nomes das colunas para snake_case.\n")
    f.write("- Remoção da coluna 'unnamed_0' por aparentar ser um índice sem valor analítico.\n")
    f.write("- Conversão das colunas de data para datetime.\n")
    f.write("- Tratamento de valores ausentes por imputação.\n")
    f.write("- Remoção de registros duplicados.\n")
    f.write("- Salvamento final em formato Parquet.\n")
    f.write("- Salvamento da camada Silver no PostgreSQL.\n\n")

    f.write("## 7. Gráficos\n\n")
    f.write("### 7.1 Top 10 Cidades com Mais Transações\n\n")
    f.write("![Top 10 Cidades com Mais Transações](graficos/01_cidades.png)\n\n")

    f.write("### 7.2 Distribuição do Valor das Transações\n\n")
    f.write("![Distribuição do Valor das Transações](graficos/02_valor_transacoes.png)\n\n")

    f.write("### 7.3 Top 10 Categorias\n\n")
    f.write("![Top 10 Categorias](graficos/03_categorias.png)\n\n")

    f.write("### 7.4 Distribuição por Gênero\n\n")
    f.write("![Distribuição por Gênero](graficos/04_genero.png)\n\n")

    f.write("### 7.5 Top 10 Estados\n\n")
    f.write("![Top 10 Estados](graficos/05_estados.png)\n\n")

    f.write("## 8. Problemas Identificados\n\n")
    if insights:
        for i in insights:
            f.write(f"- {i}\n")
    else:
        f.write("- Não foram encontrados problemas relevantes nos dados.\n")

print("Camada Silver processada com sucesso!")
print(f"Parquet salvo em: {parquet_path}")
print(f"Relatório salvo em: {relatorio_path}")
print(f"Gráficos salvos em: {graficos_dir}")
print("Tabela credit_card_silver salva no PostgreSQL!")