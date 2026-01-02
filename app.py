import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

QUESTIONARIO_FILE = "questionario_base.json"
AVALIACOES_FILE = "avaliacoes.json"


def salvar_questionario_base(dados):
    with open(QUESTIONARIO_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def carregar_questionario_base():
    if os.path.exists(QUESTIONARIO_FILE):
        with open(QUESTIONARIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def salvar_avaliacoes(dados):
    with open(AVALIACOES_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def carregar_avaliacoes():
    if os.path.exists(AVALIACOES_FILE):
        with open(AVALIACOES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


st.set_page_config(page_title="Painel Administração Contratual", layout="wide")

# ===============================
# TELA INICIAL – MODO DE USO
# ===============================

if "modo_app" not in st.session_state:
    st.session_state.modo_app = None

st.title("Painel Administração Contratual")

st.subheader("O que você deseja fazer?")

col1, col2 = st.columns(2)

with col1:
    if st.button("🆕 Nova Avaliação", use_container_width=True):
        st.session_state.modo_app = "nova"

with col2:
    if st.button("📂 Abrir Avaliação Existente", use_container_width=True):
        st.session_state.modo_app = "abrir"

# ===============================
# ESTADOS GLOBAIS
# ===============================
if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

# ===============================
# CARREGAR HISTÓRICO SALVO
# ===============================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

# ===============================
# FUNÇÕES DE NEGÓCIO
# ===============================
VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0,
    "NA": None
}

def calcular_media_ponderada(df):
    df_validas = df[df["Resposta"] != "NA"].copy()
    if df_validas.empty:
        return None

    df_validas["valor"] = df_validas["Resposta"].map(VALORES)
    soma = (df_validas["valor"] * df_validas["Peso"]).sum()
    peso_total = df_validas["Peso"].sum()

    return soma / peso_total if peso_total > 0 else None


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
# INTERFACE
# ===============================
st.title("Painel Administração Contratual")

from datetime import timedelta

st.markdown("### Informações da Avaliação")

data_avaliacao_usuario = st.date_input(
    "Data da avaliação",
    value=datetime.now().date()
)

hora_avaliacao_usuario = st.time_input(
    "Hora da avaliação",
    value=(datetime.utcnow() - timedelta(hours=3)).time()
)

if st.session_state.modo_app is None:
    st.stop()

# ===============================
# MODO: ABRIR AVALIAÇÃO EXISTENTE
# ===============================

if st.session_state.modo_app == "abrir":

    st.subheader("Avaliações Salvas")

    avaliacoes = st.session_state.get("avaliacoes_por_data", {})

    if not avaliacoes:
        st.info("ℹ️ Ainda não existem avaliações salvas.")
        st.stop()

    datas_disponiveis = sorted(avaliacoes.keys(), reverse=True)

    data_selecionada = st.selectbox(
        "Selecione a data da avaliação",
        datas_disponiveis
    )

    if st.button("📂 Abrir Avaliação Selecionada"):
        aval = avaliacoes[data_selecionada]

        st.session_state.avaliacoes = {}

        for aba, registros in aval.items():
            st.session_state.avaliacoes[aba] = pd.DataFrame(registros)

        st.success(f"Avaliação de {data_selecionada} carregada.")

   uploaded_file = st.file_uploader(
       "Carregar Excel do Projeto",
       type=["xlsx"]
   )

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)

    st.subheader("Canvas do Projeto")

    for aba in xls.sheet_names:
        df = xls.parse(aba)

        # Inicialização
        if aba not in st.session_state.avaliacoes:
            df["Resposta"] = "NA"
            df["Justificativa"] = ""
            st.session_state.avaliacoes[aba] = df
        else:
            df = st.session_state.avaliacoes[aba]

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

    st.divider()

    if st.button("Salvar Avaliação desta Data"):
        data_key = f"{data_avaliacao_usuario.strftime('%Y-%m-%d')} {hora_avaliacao_usuario.strftime('%H:%M')}"

        dados_serializaveis = {}

        for aba, df in st.session_state.avaliacoes.items():
            dados_serializaveis[aba] = df.to_dict(orient="records")

        st.session_state.avaliacoes_por_data[data_key] = dados_serializaveis

        salvar_avaliacoes(st.session_state.avaliacoes_por_data)

        st.success(
            f"✅ Avaliação salva para {data_avaliacao_usuario.strftime('%d/%m/%Y')} às {hora_avaliacao_usuario.strftime('%H:%M')}"
        )


else:
    st.info("⬆️ Faça o upload do Excel para iniciar a avaliação.")

