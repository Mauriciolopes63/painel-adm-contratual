import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Painel Administração Contratual", layout="wide")

# ===============================
# ESTADOS GLOBAIS
# ===============================
if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = {}

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

data_avaliacao = datetime.now().strftime("%d/%m/%Y %H:%M")
st.markdown(f"**Data da Avaliação:** {data_avaliacao}")

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
        data_key = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.session_state.avaliacoes_por_data[data_key] = st.session_state.avaliacoes.copy()
        st.success(f"✅ Avaliação salva com sucesso em {data_key}")

else:
    st.info("⬆️ Faça o upload do Excel para iniciar a avaliação.")

