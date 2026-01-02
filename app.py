import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# ======================================================
# CONFIGURAÇÕES
# ======================================================
st.set_page_config(
    page_title="Painel Administração Contratual",
    layout="wide"
)

AVALIACOES_FILE = "avaliacoes.json"

# ======================================================
# PERSISTÊNCIA
# ======================================================
def salvar_avaliacoes(dados):
    with open(AVALIACOES_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_avaliacoes():
    if os.path.exists(AVALIACOES_FILE):
        with open(AVALIACOES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ======================================================
# REGRAS DE AVALIAÇÃO
# ======================================================
VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0,
    "NA": None
}

def calcular_media_ponderada(df):
    if "Resposta" not in df.columns or "Peso" not in df.columns:
        return None

    df_validas = df[df["Resposta"] != "NA"].copy()
    if df_validas.empty:
        return None

    df_validas["valor"] = df_validas["Resposta"].map(VALORES)
    soma = (df_validas["valor"] * df_validas["Peso"]).sum()
    peso_total = df_validas["Peso"].sum()

    if peso_total == 0:
        return None

    return soma / peso_total

def cor_por_nota(nota):
    if nota is None:
        return "⚪"
    elif nota <= 0.25:
        return "🟢"
    elif nota <= 0.50:
        return "🟡"
    elif nota < 0.75:
        return "🟠"
    else:
        return "🔴"

# ======================================================
# ESTADO
# ======================================================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

# ======================================================
# TÍTULO
# ======================================================
st.title("Painel Administração Contratual")

# ======================================================
# DATA / HORA DA AVALIAÇÃO
# ======================================================
st.markdown("### Informações da Avaliação")

data_avaliacao = st.date_input(
    "Data da avaliação",
    datetime.now().date()
)

hora_avaliacao = st.time_input(
    "Hora da avaliação",
    (datetime.utcnow() - timedelta(hours=3)).time()
)

# ======================================================
# UPLOAD DO EXCEL
# ======================================================
uploaded_file = st.file_uploader(
    "Carregar Excel do Projeto",
    type=["xlsx"]
)

if not uploaded_file:
    st.info("⬆️ Faça upload do Excel para iniciar a avaliação.")
    st.stop()

xls = pd.ExcelFile(uploaded_file)

# ======================================================
# CANVAS DO PROJETO
# ======================================================
st.subheader("Canvas do Projeto")

for aba in xls.sheet_names:
    df_excel = xls.parse(aba)

    if aba not in st.session_state.avaliacoes:
        df_excel["Resposta"] = "NA"
        df_excel["Justificativa"] = ""
        st.session_state.avaliacoes[aba] = df_excel
    else:
        df_excel = st.session_state.avaliacoes[aba]

    nota = calcular_media_ponderada(df_excel)
    semaforo = cor_por_nota(nota)

    with st.expander(f"{semaforo} {aba}", expanded=False):

        for i, row in df_excel.iterrows():
            st.markdown(f"**{row['Pergunta']}**")

            resposta = st.selectbox(
                "Avaliação",
                ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                index=["Bom", "Médio", "Ruim", "Crítico", "NA"].index(row["Resposta"]),
                key=f"{aba}_{i}"
            )

            justificativa = row["Justificativa"]

            if resposta in ["Ruim", "Crítico"]:
                justificativa = st.text_input(
                    "Justificativa",
                    value=justificativa,
                    key=f"{aba}_{i}_j"
                )
            else:
                justificativa = ""

            df_excel.at[i, "Resposta"] = resposta
            df_excel.at[i, "Justificativa"] = justificativa

        st.session_state.avaliacoes[aba] = df_excel

# ======================================================
# SALVAR AVALIAÇÃO
# ======================================================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data_avaliacao.strftime('%Y-%m-%d')} {hora_avaliacao.strftime('%H:%M')}"

    dados_serializaveis = {}
    for aba, df in st.session_state.avaliacoes.items():
        dados_serializaveis[aba] = df.to_dict(orient="records")

    st.session_state.avaliacoes_por_data[chave] = dados_serializaveis
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)

    st.success(f"✅ Avaliação salva em {chave}")
