import os
import pandas as pd
from sqlalchemy import create_engine, text

# configurando banco
engine = create_engine(
    "postgresql+psycopg2://postgres:1205@localhost:5432/lab01_dw"
)

output_dir = "data/gold"
os.makedirs(output_dir, exist_ok=True)

# dict para auxiliar a substituicao das siglas pelos nomes dos estados
nomes_estados = {
    "AL": "Alabama",
    "AK": "Alasca",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "Califórnia",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Flórida",
    "GA": "Geórgia",
    "HI": "Havaí",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "Novo México",
    "NY": "Nova York",
    "NC": "Carolina do Norte",
    "ND": "Dakota do Norte",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pensilvânia",
    "RI": "Rhode Island",
    "SC": "Carolina do Sul",
    "SD": "Dakota do Sul",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virgínia",
    "WA": "Washington",
    "WV": "Virgínia Ocidental",
    "WI": "Wisconsin",
    "WY": "Wyoming"
}

# dict para auxiliar na traducao dos dias da semana
dias_semana_pt = {
    "Monday": "Segunda-feira",
    "Tuesday": "Terça-feira",
    "Wednesday": "Quarta-feira",
    "Thursday": "Quinta-feira",
    "Friday": "Sexta-feira",
    "Saturday": "Sábado",
    "Sunday": "Domingo"
}

# funcoes auxiliares
def executar_query(query: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql_query(text(query), conn)

def formatar_categoria(texto):
    if pd.isna(texto):
        return "Não identificado"
    return str(texto).replace("_", " ").title()

def formatar_valor(valor):
    return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def calcular_por_mil(total_fraudes, total_transacoes):
    if total_transacoes == 0:
        return 0.0
    return round((float(total_fraudes) / float(total_transacoes)) * 1000, 1)

queries = {
    "estado_maior_taxa_fraude": """
        SELECT
            dl.state AS estado,
            COUNT(*) AS total_transacoes,
            SUM(ft.is_fraud) AS total_fraudes,
            ROUND(100.0 * SUM(ft.is_fraud) / COUNT(*), 2) AS taxa_fraude_percentual
        FROM fato_transacoes ft
        JOIN dim_localizacao dl
            ON ft.localizacao_sk = dl.localizacao_sk
        GROUP BY dl.state
        HAVING COUNT(*) >= 1000
        ORDER BY taxa_fraude_percentual DESC, total_fraudes DESC
        LIMIT 1
    """,

    "categoria_maior_valor_fraudado": """
        SELECT
            dc.category AS categoria,
            COUNT(*) AS total_fraudes,
            ROUND(SUM(ft.amt)::numeric, 2) AS valor_total_fraudado,
            ROUND(AVG(ft.amt)::numeric, 2) AS ticket_medio_fraudado
        FROM fato_transacoes ft
        JOIN dim_categoria dc
            ON ft.categoria_sk = dc.categoria_sk
        WHERE ft.is_fraud = 1
        GROUP BY dc.category
        ORDER BY valor_total_fraudado DESC, total_fraudes DESC
        LIMIT 1
    """,

    "faixa_etaria_maior_taxa_fraude": """
        SELECT
            CASE
                WHEN dc.idade < 25 THEN 'Até 24 anos'
                WHEN dc.idade BETWEEN 25 AND 34 THEN 'De 25 a 34 anos'
                WHEN dc.idade BETWEEN 35 AND 44 THEN 'De 35 a 44 anos'
                WHEN dc.idade BETWEEN 45 AND 54 THEN 'De 45 a 54 anos'
                WHEN dc.idade BETWEEN 55 AND 64 THEN 'De 55 a 64 anos'
                ELSE '65 anos ou mais'
            END AS faixa_etaria,
            COUNT(*) AS total_transacoes,
            SUM(ft.is_fraud) AS total_fraudes,
            ROUND(100.0 * SUM(ft.is_fraud) / COUNT(*), 2) AS taxa_fraude_percentual
        FROM fato_transacoes ft
        JOIN dim_cliente dc
            ON ft.cliente_sk = dc.cliente_sk
        GROUP BY 1
        HAVING COUNT(*) >= 1000
        ORDER BY taxa_fraude_percentual DESC, total_fraudes DESC
        LIMIT 1
    """,

    "horario_maior_taxa_fraude": """
        SELECT
            dt.hora AS hora_do_dia,
            COUNT(*) AS total_transacoes,
            SUM(ft.is_fraud) AS total_fraudes,
            ROUND(100.0 * SUM(ft.is_fraud) / COUNT(*), 2) AS taxa_fraude_percentual
        FROM fato_transacoes ft
        JOIN dim_tempo dt
            ON ft.tempo_sk = dt.tempo_sk
        GROUP BY dt.hora
        HAVING COUNT(*) >= 1000
        ORDER BY taxa_fraude_percentual DESC, total_fraudes DESC
        LIMIT 1
    """,

    "dia_semana_maior_taxa_fraude": """
        SELECT
            dt.dia_semana AS dia_da_semana,
            COUNT(*) AS total_transacoes,
            SUM(ft.is_fraud) AS total_fraudes,
            ROUND(100.0 * SUM(ft.is_fraud) / COUNT(*), 2) AS taxa_fraude_percentual
        FROM fato_transacoes ft
        JOIN dim_tempo dt
            ON ft.tempo_sk = dt.tempo_sk
        GROUP BY dt.dia_semana, dt.dia_semana_num
        ORDER BY taxa_fraude_percentual DESC, total_fraudes DESC
        LIMIT 1
    """
}

# executando as queries
resultados = {}

for nome, query in queries.items():
    df = executar_query(query)
    resultados[nome] = df

# gerando relatorios
linhas_relatorio = []
linhas_relatorio.append("# Relatório de Métricas de Negócio da Camada Gold\n")
linhas_relatorio.append(
    "Este relatório apresenta os principais resultados analíticos obtidos a partir da camada Gold, com foco na identificação de padrões de fraude em transações financeiras.\n"
)

# querie 1 = estado com maior taxa de fraude
df1 = resultados["estado_maior_taxa_fraude"]
if not df1.empty:
    top1 = df1.iloc[0]
    estado_nome = nomes_estados.get(top1["estado"], top1["estado"])
    taxa_por_mil_1 = calcular_por_mil(top1["total_fraudes"], top1["total_transacoes"])

    linhas_relatorio.append("## 1. Estado com maior taxa de fraude\n")
    linhas_relatorio.append(
        f"O estado com maior taxa de fraude, considerando apenas estados com volume relevante de transações, foi **{estado_nome}**. "
        f"Foram registradas **{int(top1['total_fraudes'])} fraudes** em **{int(top1['total_transacoes'])} transações**, "
        f"o que representa uma taxa de **{top1['taxa_fraude_percentual']}%**, equivalente a aproximadamente **{taxa_por_mil_1} fraudes por mil transações**.\n"
    )
else:
    linhas_relatorio.append("## 1. Estado com maior taxa de fraude\n")
    linhas_relatorio.append(
        "Não foi possível identificar um estado com volume suficiente de transações para essa análise.\n"
    )

# querie 2 = categoria de negocio com maior taxa de fraude
df2 = resultados["categoria_maior_valor_fraudado"]
if not df2.empty:
    top2 = df2.iloc[0]
    categoria_nome = formatar_categoria(top2["categoria"])

    linhas_relatorio.append("## 2. Categoria com maior valor total fraudado\n")
    linhas_relatorio.append(
        f"A categoria com maior impacto financeiro em fraudes foi **{categoria_nome}**. "
        f"Ela acumulou **{int(top2['total_fraudes'])} transações fraudulentas**, "
        f"totalizando **US$ {formatar_valor(top2['valor_total_fraudado'])}** em valor fraudado, "
        f"com um ticket médio de **US$ {formatar_valor(top2['ticket_medio_fraudado'])}** por transação fraudulenta.\n"
    )
else:
    linhas_relatorio.append("## 2. Categoria com maior valor total fraudado\n")
    linhas_relatorio.append(
        "Não foi possível identificar uma categoria com valor fraudado para essa análise.\n"
    )

# queria 3 = faixa etaria com maior taxa de fraude
df3 = resultados["faixa_etaria_maior_taxa_fraude"]
if not df3.empty:
    top3 = df3.iloc[0]
    taxa_por_mil_3 = calcular_por_mil(top3["total_fraudes"], top3["total_transacoes"])

    linhas_relatorio.append("## 3. Faixa etária com maior taxa de fraude\n")
    linhas_relatorio.append(
        f"A faixa etária com maior taxa de fraude foi **{top3['faixa_etaria']}**. "
        f"Nesse grupo, ocorreram **{int(top3['total_fraudes'])} fraudes** em **{int(top3['total_transacoes'])} transações**, "
        f"resultando em uma taxa de **{top3['taxa_fraude_percentual']}%**, o equivalente a aproximadamente **{taxa_por_mil_3} fraudes por mil transações**.\n"
    )
else:
    linhas_relatorio.append("## 3. Faixa etária com maior taxa de fraude\n")
    linhas_relatorio.append(
        "Não foi possível identificar uma faixa etária com volume suficiente de transações para essa análise.\n"
    )

# queria 4 = horario com maior taxa de fraude
df4 = resultados["horario_maior_taxa_fraude"]
if not df4.empty:
    top4 = df4.iloc[0]
    taxa_por_mil_4 = calcular_por_mil(top4["total_fraudes"], top4["total_transacoes"])

    linhas_relatorio.append("## 4. Horário com maior taxa de fraude\n")
    linhas_relatorio.append(
        f"O horário com maior taxa de fraude foi **{int(top4['hora_do_dia']):02d}:00**. "
        f"Nesse período, foram registradas **{int(top4['total_fraudes'])} fraudes** em **{int(top4['total_transacoes'])} transações**, "
        f"equivalendo a **{top4['taxa_fraude_percentual']}%**, ou aproximadamente **{taxa_por_mil_4} fraudes por mil transações**.\n"
    )
else:
    linhas_relatorio.append("## 4. Horário com maior taxa de fraude\n")
    linhas_relatorio.append(
        "Não foi possível identificar um horário com volume suficiente de transações para essa análise.\n"
    )

# querie 5 = dia da semana com maior taxa de fraude
df5 = resultados["dia_semana_maior_taxa_fraude"]
if not df5.empty:
    top5 = df5.iloc[0]
    taxa_por_mil_5 = calcular_por_mil(top5["total_fraudes"], top5["total_transacoes"])
    dia_traduzido = dias_semana_pt.get(
        str(top5["dia_da_semana"]).title(),
        top5["dia_da_semana"]
    )

    linhas_relatorio.append("## 5. Dia da semana com maior taxa de fraude\n")
    linhas_relatorio.append(
        f"O dia da semana com maior taxa de fraude foi **{dia_traduzido}**. "
        f"Nesse dia, foram registradas **{int(top5['total_fraudes'])} fraudes** em **{int(top5['total_transacoes'])} transações**, "
        f"o que corresponde a **{top5['taxa_fraude_percentual']}%**, ou aproximadamente **{taxa_por_mil_5} fraudes por mil transações**.\n"
    )
else:
    linhas_relatorio.append("## 5. Dia da semana com maior taxa de fraude\n")
    linhas_relatorio.append(
        "Não foi possível identificar um dia da semana para essa análise.\n"
    )

# salvando relatorio final 
relatorio_path = f"{output_dir}/relatorio_metricas_gold.md"
with open(relatorio_path, "w", encoding="utf-8") as f:
    f.write("\n".join(linhas_relatorio))

print("Análise da Gold concluída com sucesso.")
print(f"Relatório salvo em: {os.path.abspath(relatorio_path)}")