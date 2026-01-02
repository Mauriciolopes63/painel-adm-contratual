import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

AVALIACOES_FILE = "avaliacoes.json"

# ===============================
# PERSISTÊNCIA
# ===============================
def salvar_avaliacoes(dados):
    with open(AVALIACOES_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_avaliacoes():
    if os.path.exists(AVALIACOES_FILE):
        with open(AVALIACOES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ===============================
# CONFIG
# ===============================
st.set_page_config("Painel Administração Contratual", layout="wide")

# ===============================
# ESTADO
# ===============================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

# ===============================
# TÍTULO
# ===============================
st.title("Painel Administração Contratual")

# ===============================
# DATA / HORA
# ===============================
st.markdown("### Informações da Avaliação")

data_avaliacao = st.date_input("Data", datetime.now().date())
hora_avaliacao = st.time_input(
    "Hora",
    (datetime.utcnow() - timedelta(hours=3)).time()
)

# ===============================
# UPLOAD EXCEL
# ===============================
uploaded_file = st.file_uploader(
    "Carregar Excel do Projeto",
    type=["xlsx"]
)

if not uploaded_file:
    st.info("⬆️ Faça upload do Excel para iniciar.")
    st.stop()

xls = pd.ExcelFile(uploaded_file)

# ===============================
# CANVAS SIMPLES
# ===============================
st.subheader("Canvas do Projeto")

for aba in xls.sheet_names:
    df = xls.parse(aba)

    if aba not in st.session_state.avaliacoes:
        df["Resposta"] = "NA"
        st.session_state.avaliacoes[aba] = df
    else:
        df = st.session_state.avaliacoes[aba]

    with st.expander(aba):

        # garante que a coluna exista
        if "Justificativa" not in df.columns:
            df["Justificativa"] = ""

        for i, row in df.iterrows():

            resposta = st.selectbox(
                row["Pergunta"],
                ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                index=["Bom", "Médio", "Ruim", "Crítico", "NA"].index(row["Resposta"]),
                key=f"{aba}_{i}"
            )

            justificativa_atual = row["Justificativa"]

            justificativa = justificativa_atual
            if resposta in ["Ruim", "Crítico"]:
                justificativa = st.text_input(
                    "Justificativa",
                    value=justificativa_atual,
                    key=f"{aba}_{i}_j"
                )

            df.at[i, "Resposta"] = resposta
            df.at[i, "Justificativa"] = justificativa

        st.session_state.avaliacoes[aba] = df

# ===============================
# SALVAR
# ===============================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data_avaliacao} {hora_avaliacao.strftime('%H:%M')}"

    dados = {}
    for aba, df in st.session_state.avaliacoes.items():
        dados[aba] = df.to_dict(orient="records")

    st.session_state.avaliacoes_por_data[chave] = dados
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)

    st.success(f"Avaliação salva em {chave}")
