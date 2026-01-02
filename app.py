import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# ===============================
# CONFIGURAÇÃO
# ===============================
st.set_page_config(
    page_title="Painel Administração Contratual",
    layout="wide"
)

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
# REGRAS DE AVALIAÇÃO (INTERNO)
# ===============================
VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0,
    "NA": None
}

def calcular_media_ponderada(df):
    if "Peso" not in df.columns:
        df["Peso"] = 1.0

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
    if nota <= 0.25:
        return "🟢"
    elif nota <= 0.50:
        return "🟡"
    elif nota < 0.75:
        return "🟠"
    else:
        return "🔴"

# ===============================
# ESTADO
# ===============================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

if "modo" not in st.session_state:
    st.session_state.modo = None

# ===============================
# TÍTULO
# ===============================
st.title("Painel Administração Contratual")

# ===============================
# ESCOLHA DO MODO
# ===============================
col1, col2 = st.columns(2)

with col1:
    if st.button("🆕 Nova Avaliação", use_container_width=True):
        st.session_state.modo = "nova"

with col2:
    if st.button("📂 Abrir Avaliação Existente", use_container_width=True):
        st.session_state.modo = "abrir"

if st.session_state.modo is None:
    st.stop()

# ===============================
# ABRIR AVALIAÇÃO EXISTENTE
# ===============================
if st.session_state.modo == "abrir":

    avaliacoes = st.session_state.avaliacoes_por_data

    if not avaliacoes:
        st.info("ℹ️ Ainda não existem avaliações salvas.")
        st.stop()

    data_escolhida = st.selectbox(
        "Selecione a avaliação",
        sorted(avaliacoes.keys(), reverse=True)
    )

    if st.button("📂 Abrir Avaliação"):
        dados = avaliacoes[data_escolhida]
        st.session_state.avaliacoes = {
            aba: pd.DataFrame(registros)
            for aba, registros in dados.items()
        }
        st.success(f"Avaliação {data_escolhida} carregada.")

# ===============================
# DATA / HORA DA AVALIAÇÃO
# ===============================
st.markdown("### Informações da Avaliação")

data_avaliacao = st.date_input("Data da avaliação", datetime.now().date())
hora_avaliacao = st.time_input("Hora da avaliação", datetime.now().time())

# ===============================
# UPLOAD DO EXCEL
# ===============================

uploaded_file = None

# Upload só é obrigatório para nova avaliação
if st.session_state.modo == "nova":
    uploaded_file = st.file_uploader(
        "Carregar Excel do Projeto",
        type=["xlsx"]
    )

    if not uploaded_file:
        st.info("⬆️ Faça o upload do Excel para iniciar o Canvas.")
        st.stop()

# Para abrir avaliação existente, o Excel é opcional
if st.session_state.modo == "abrir" and uploaded_file is None:
    uploaded_file = st.file_uploader(
        "Carregar Excel do Projeto (somente se quiser revisar perguntas)",
        type=["xlsx"]
    )

xls = pd.ExcelFile(uploaded_file)

# ===============================
# CANVAS
# ===============================
st.subheader("Canvas do Projeto")

for aba in xls.sheet_names:

    if aba in st.session_state.avaliacoes:
        df = st.session_state.avaliacoes[aba]
    else:
        df = xls.parse(aba)
        df["Resposta"] = "NA"
        df["Justificativa"] = ""
        st.session_state.avaliacoes[aba] = df

    codigo = df.iloc[0]["Codigo"] if "Codigo" in df.columns else aba
    descricao = df.iloc[0]["Descricao"] if "Descricao" in df.columns else ""

    nota = calcular_media_ponderada(df)
    semaforo = cor_por_nota(nota)

    with st.expander(f"{semaforo} {codigo} – {descricao}", expanded=False):

        for i, row in df.iterrows():

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

            df.at[i, "Resposta"] = resposta
            df.at[i, "Justificativa"] = justificativa

        st.session_state.avaliacoes[aba] = df

# ===============================
# SALVAR AVALIAÇÃO
# ===============================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data_avaliacao.strftime('%Y-%m-%d')} {hora_avaliacao.strftime('%H:%M')}"

    dados = {
        aba: df.to_dict(orient="records")
        for aba, df in st.session_state.avaliacoes.items()
    }

    st.session_state.avaliacoes_por_data[chave] = dados
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)

    st.success(f"✅ Avaliação salva em {chave}")
