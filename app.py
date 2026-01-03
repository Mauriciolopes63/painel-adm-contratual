import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import copy

# ===============================
# CONFIGURAÇÕES
# ===============================
st.set_page_config(
    page_title="Painel Administração Contratual",
    layout="wide"
)

ARQUIVO_AVALIACOES = "avaliacoes.json"

# ===============================
# PERSISTÊNCIA
# ===============================
def salvar_avaliacoes(dados):
    with open(ARQUIVO_AVALIACOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_avaliacoes():
    if os.path.exists(ARQUIVO_AVALIACOES):
        with open(ARQUIVO_AVALIACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ===============================
# REGRAS DE NEGÓCIO
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
# ESTADO GLOBAL
# ===============================
if "avaliacoes_salvas" not in st.session_state:
    st.session_state.avaliacoes_salvas = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = None

if "modo" not in st.session_state:
    st.session_state.modo = None

# ===============================
# TÍTULO
# ===============================
st.title("Painel Administração Contratual")

# ===============================
# SELEÇÃO DE MODO
# ===============================
st.subheader("O que você deseja fazer?")

col1, col2 = st.columns(2)

with col1:
    if st.button("🆕 Nova Avaliação", use_container_width=True):
        st.session_state.modo = "nova"
        st.session_state.avaliacao_atual = None

with col2:
    if st.button("📂 Abrir Avaliação Existente", use_container_width=True):
        st.session_state.modo = "abrir"

if st.session_state.modo is None:
    st.stop()

# ===============================
# ABRIR AVALIAÇÃO EXISTENTE
# ===============================
if st.session_state.modo == "abrir":

    st.subheader("Avaliações Salvas")

    if not st.session_state.avaliacoes_salvas:
        st.info("ℹ️ Nenhuma avaliação encontrada.")
        st.stop()

    datas = sorted(st.session_state.avaliacoes_salvas.keys(), reverse=True)

    data_escolhida = st.selectbox(
        "Selecione a avaliação",
        datas
    )

    if st.button("📂 Abrir Avaliação Selecionada"):
        # RESET TOTAL DO ESTADO ATIVO
        st.session_state.avaliacao_atual = json.loads(
            json.dumps(st.session_state.avaliacoes_salvas[data_escolhida])
        )
        st.success(f"Avaliação de {data_escolhida} carregada.")
        st.session_state.modo = "editar"
        st.rerun()

    st.stop()

# ===============================
# INFORMAÇÕES DA AVALIAÇÃO
# ===============================
st.subheader("Informações da Avaliação")

data_avaliacao = st.date_input(
    "Data da avaliação",
    datetime.now().date()
)

hora_avaliacao = st.time_input(
    "Hora da avaliação",
    (datetime.utcnow() - timedelta(hours=3)).time()
)

# ===============================
# UPLOAD DO EXCEL
# ===============================
uploaded_file = st.file_uploader(
    "Carregar Excel do Projeto",
    type=["xlsx"]
)

if not uploaded_file:
    st.info("⬆️ Faça upload do Excel para iniciar a avaliação.")
    st.stop()

xls = pd.ExcelFile(uploaded_file)

# ===============================
# INICIALIZAÇÃO DA AVALIAÇÃO
# ===============================
if st.session_state.avaliacao_atual is None:
    st.session_state.avaliacao_atual = {}

    for aba in xls.sheet_names:
        df = xls.parse(aba)

        df["Resposta"] = "NA"
        df["Justificativa"] = ""

        st.session_state.avaliacao_atual[aba] = df

# ===============================
# CANVAS
# ===============================
st.subheader("Canvas do Projeto")

for aba in xls.sheet_names:

    df = st.session_state.avaliacao_atual[aba]

    codigo = df.iloc[0]["Codigo"]
    descricao = df.iloc[0]["Descricao"]

    nota = calcular_media_ponderada(df)
    semaforo = cor_por_nota(nota)

    with st.expander(f"{semaforo} {codigo} – {descricao}", expanded=False):

        for tipo in ["Procedimento", "Acompanhamento"]:
            df_tipo = df[df["Tipo"] == tipo]

            if df_tipo.empty:
                continue

            st.markdown(f"### {tipo}")

            for idx, row in df_tipo.iterrows():
                resposta = st.selectbox(
                    row["Pergunta"],
                    ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                    index=["Bom", "Médio", "Ruim", "Crítico", "NA"].index(row["Resposta"]),
                    key=f"{aba}_{idx}_{tipo}"
                )

                justificativa = row["Justificativa"]
                if resposta in ["Ruim", "Crítico"]:
                    justificativa = st.text_input(
                        "Justificativa",
                        value=justificativa,
                        key=f"{aba}_{idx}_{tipo}_j"
                    )
                else:
                    justificativa = ""

                df.at[idx, "Resposta"] = resposta
                df.at[idx, "Justificativa"] = justificativa

        st.session_state.avaliacao_atual[aba] = df

# ===============================
# SALVAR AVALIAÇÃO
# ===============================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data_avaliacao.strftime('%Y-%m-%d')} {hora_avaliacao.strftime('%H:%M')}"

    # SNAPSHOT PROFUNDO (ISOLAMENTO TOTAL)
    snapshot = json.loads(
        json.dumps(
            {
                aba: df.to_dict(orient="records")
                for aba, df in st.session_state.avaliacao_atual.items()
            }
        )
    )

    st.session_state.avaliacoes_salvas[chave] = snapshot
    salvar_avaliacoes(st.session_state.avaliacoes_salvas)

    st.success(f"✅ Avaliação salva com sucesso em {chave}")
