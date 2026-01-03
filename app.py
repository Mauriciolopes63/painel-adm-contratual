import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="Painel Administração Contratual",
    layout="wide"
)

ARQUIVO_AVALIACOES = "avaliacoes.json"

# =====================================================
# PERSISTÊNCIA
# =====================================================
def salvar_avaliacoes(dados):
    with open(ARQUIVO_AVALIACOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_avaliacoes():
    if os.path.exists(ARQUIVO_AVALIACOES):
        with open(ARQUIVO_AVALIACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# =====================================================
# REGRAS DE NEGÓCIO
# =====================================================
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

    if peso_total == 0:
        return None

    return soma / peso_total

def semaforo(nota):
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

# =====================================================
# ESTADO
# =====================================================
if "avaliacoes_salvas" not in st.session_state:
    st.session_state.avaliacoes_salvas = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = None

if "modo" not in st.session_state:
    st.session_state.modo = None

# =====================================================
# TÍTULO
# =====================================================
st.title("Painel Administração Contratual")

# =====================================================
# MENU
# =====================================================
st.subheader("O que deseja fazer?")

c1, c2 = st.columns(2)

with c1:
    if st.button("🆕 Nova Avaliação", use_container_width=True):
        st.session_state.modo = "nova"
        st.session_state.avaliacao_atual = None

with c2:
    if st.button("📂 Abrir Avaliação Existente", use_container_width=True):
        st.session_state.modo = "abrir"

if st.session_state.modo is None:
    st.stop()

# =====================================================
# ABRIR AVALIAÇÃO EXISTENTE
# =====================================================
if st.session_state.modo == "abrir":

    if not st.session_state.avaliacoes_salvas:
        st.info("Nenhuma avaliação encontrada.")
        st.stop()

    datas = sorted(st.session_state.avaliacoes_salvas.keys(), reverse=True)

    escolha = st.selectbox("Selecione a avaliação", datas)

    if st.button("Abrir Avaliação"):
        # CLONE COMPLETO
        st.session_state.avaliacao_atual = json.loads(
            json.dumps(st.session_state.avaliacoes_salvas[escolha])
        )
        st.session_state.modo = "editar"
        st.rerun()

    st.stop()

# =====================================================
# CABEÇALHO
# =====================================================
st.subheader("Cabeçalho")

if st.session_state.avaliacao_atual is None:
    st.session_state.avaliacao_atual = {
        "cabecalho": {
            "projeto": "",
            "cliente": "",
            "responsavel": "",
            "data": datetime.now().date().strftime("%Y-%m-%d"),
            "hora": (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M")
        },
        "dados": {}
    }

cab = st.session_state.avaliacao_atual["cabecalho"]

c1, c2, c3 = st.columns(3)
cab["projeto"] = c1.text_input("Projeto", cab["projeto"])
cab["cliente"] = c2.text_input("Cliente", cab["cliente"])
cab["responsavel"] = c3.text_input("Responsável", cab["responsavel"])

c4, c5 = st.columns(2)
cab["data"] = c4.date_input(
    "Data",
    datetime.strptime(cab["data"], "%Y-%m-%d").date()
).strftime("%Y-%m-%d")

cab["hora"] = c5.time_input(
    "Hora",
    datetime.strptime(cab["hora"], "%H:%M").time()
).strftime("%H:%M")

# =====================================================
# UPLOAD EXCEL (OBRIGATÓRIO)
# =====================================================
uploaded_file = st.file_uploader(
    "Carregar Excel do Projeto",
    type=["xlsx"]
)

if not uploaded_file:
    st.info("⬆️ Faça upload do Excel para continuar.")
    st.stop()

xls = pd.ExcelFile(uploaded_file)

# =====================================================
# PREPARAR DADOS
# =====================================================
dados = {}

for aba in xls.sheet_names:
    base = xls.parse(aba)

    if aba in st.session_state.avaliacao_atual["dados"]:
        # AVALIAÇÃO EXISTENTE → converter para DataFrame
        respostas = pd.DataFrame(
            st.session_state.avaliacao_atual["dados"][aba]
        )

        base["Resposta"] = respostas["Resposta"].values
        base["Justificativa"] = respostas["Justificativa"].values
    else:
        base["Resposta"] = "NA"
        base["Justificativa"] = ""

    dados[aba] = base

st.session_state.avaliacao_atual["dados"] = dados

# =====================================================
# CANVAS
# =====================================================
st.subheader("Canvas do Projeto")

for aba, df in dados.items():

    codigo = df.iloc[0]["Codigo"]
    descricao = df.iloc[0]["Descricao"]

    nota = calcular_media_ponderada(df)
    cor = semaforo(nota)

    with st.expander(f"{cor} {codigo} – {descricao}"):

        for tipo in ["Procedimento", "Acompanhamento"]:
            bloco = df[df["Tipo"] == tipo]
            if bloco.empty:
                continue

            st.markdown(f"### {tipo}")

            for idx, row in bloco.iterrows():
                resp = st.selectbox(
                    row["Pergunta"],
                    ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                    index=["Bom", "Médio", "Ruim", "Crítico", "NA"].index(row["Resposta"]),
                    key=f"{aba}_{idx}"
                )

                just = row["Justificativa"]
                if resp in ["Ruim", "Crítico"]:
                    just = st.text_input(
                        "Justificativa",
                        value=just,
                        key=f"{aba}_{idx}_j"
                    )
                else:
                    just = ""

                df.at[idx, "Resposta"] = resp
                df.at[idx, "Justificativa"] = just

# =====================================================
# SALVAR
# =====================================================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{cab['data']} {cab['hora']}"

    snapshot = {
        "cabecalho": cab,
        "dados": {
            aba: df.to_dict(orient="records")
            for aba, df in st.session_state.avaliacao_atual["dados"].items()
        }
    }

    st.session_state.avaliacoes_salvas[chave] = snapshot
    salvar_avaliacoes(st.session_state.avaliacoes_salvas)

    st.success("Avaliação salva com sucesso.")
