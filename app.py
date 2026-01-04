import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# ===============================
# CONFIGURAÇÃO
# ===============================
st.set_page_config("Painel Administração Contratual", layout="wide")

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
# ESTADO GLOBAL
# ===============================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {}

if "modo" not in st.session_state:
    st.session_state.modo = None

# ===============================
# FUNÇÕES DE NEGÓCIO
# ===============================
OPCOES = ["NA", "Bom", "Médio", "Ruim", "Crítico"]

VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0
}

def calcular_semaforo(df):
    df_validas = df[df["Resposta"] != "NA"].copy()
    if df_validas.empty:
        return "⚪"

    df_validas["valor"] = df_validas["Resposta"].map(VALORES)
    nota = (df_validas["valor"] * df_validas["Peso"]).sum() / df_validas["Peso"].sum()

    if nota <= 0.25:
        return "🟢"
    elif nota <= 0.50:
        return "🟡"
    elif nota < 0.75:
        return "🟠"
    else:
        return "🔴"

# ===============================
# TÍTULO
# ===============================
st.title("Painel Administração Contratual")

# ===============================
# MENU INICIAL
# ===============================
col1, col2 = st.columns(2)

with col1:
    if st.button("🆕 Nova Avaliação", use_container_width=True):
        st.session_state.modo = "nova"
        st.session_state.avaliacao_atual = {}

with col2:
    if st.button("📂 Abrir Avaliação Existente", use_container_width=True):
        st.session_state.modo = "abrir"

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
# ABRIR AVALIAÇÃO EXISTENTE
# ===============================
if st.session_state.modo == "abrir":

    if not st.session_state.avaliacoes_por_data:
        st.info("Nenhuma avaliação salva.")
        st.stop()

    datas = sorted(st.session_state.avaliacoes_por_data.keys(), reverse=True)

    data_sel = st.selectbox("Selecione a avaliação", datas)

    if st.button("Abrir Avaliação"):
        dados = st.session_state.avaliacoes_por_data[data_sel]
        st.session_state.avaliacao_atual = {
            aba: pd.DataFrame(registros) for aba, registros in dados.items()
        }
        st.success(f"Avaliação {data_sel} carregada.")

# ===============================
# UPLOAD EXCEL
# ===============================
uploaded_file = st.file_uploader(
    "Carregar Excel do Projeto",
    type=["xlsx"]
)

if not uploaded_file:
    st.stop()

xls = pd.ExcelFile(uploaded_file)

# ===============================
# TELA DE PERGUNTAS
# ===============================
for aba in xls.sheet_names:
    base = xls.parse(aba)

    if aba not in st.session_state.avaliacao_atual:
        base["Resposta"] = "NA"
        base["Justificativa"] = ""
        st.session_state.avaliacao_atual[aba] = base
    else:
        base = st.session_state.avaliacao_atual[aba]

    fase = base.iloc[0]["Fase"]
    grupo = base.iloc[0]["Grupo"]
    codigo = base.iloc[0]["Codigo"]
    descricao = base.iloc[0]["Descricao"]

    st.markdown(f"## {fase}")
    st.markdown(f"### {grupo}")

    semaforo = calcular_semaforo(base)

    with st.expander(f"{semaforo} {codigo} – {descricao}", expanded=False):

        for tipo in ["Procedimento", "Acompanhamento"]:
            st.markdown(f"#### {tipo}")

            df_tipo = base[base["Tipo"] == tipo]

            for i, r in df_tipo.iterrows():
                resp = st.selectbox(
                    r["Pergunta"],
                    OPCOES,
                    index=OPCOES.index(r["Resposta"]),
                    key=f"{aba}_{i}"
                )

                base.at[i, "Resposta"] = resp

                if resp in ["Ruim", "Crítico"]:
                    just = st.text_input(
                        "Justificativa",
                        value=r["Justificativa"],
                        key=f"{aba}_{i}_j"
                    )
                    base.at[i, "Justificativa"] = just
                else:
                    base.at[i, "Justificativa"] = ""

    st.session_state.avaliacao_atual[aba] = base

# ===============================
# SALVAR AVALIAÇÃO
# ===============================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data_avaliacao} {hora_avaliacao.strftime('%H:%M')}"

    dados = {
        aba: df.to_dict(orient="records")
        for aba, df in st.session_state.avaliacao_atual.items()
    }

    st.session_state.avaliacoes_por_data[chave] = dados
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)

    st.success(f"Avaliação salva em {chave}")
