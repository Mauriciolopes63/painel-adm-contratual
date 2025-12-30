import streamlit as st
import pandas as pd

st.set_page_config(page_title="Painel Administração Contratual", layout="wide")

st.title("Painel Administração Contratual – Piloto Interno")

uploaded_file = st.file_uploader(
    "Carregar Excel do Projeto",
    type=["xlsx"]
)

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)

    if "avaliacoes" not in st.session_state:
        st.session_state.avaliacoes = {}

    for aba in xls.sheet_names:
        df = xls.parse(aba)

        if aba not in st.session_state.avaliacoes:
            df["Resposta"] = "NA"
            df["Justificativa"] = ""
            st.session_state.avaliacoes[aba] = df
        else:
            df = st.session_state.avaliacoes[aba]

        with st.expander(f"{aba}", expanded=False):
            for i, row in df.iterrows():
                resposta = st.selectbox(
                    row["Pergunta"],
                    ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                    index=["Bom", "Médio", "Ruim", "Crítico", "NA"].index(row["Resposta"]),
                    key=f"{aba}_{i}_resp"
                )

                justificativa = row["Justificativa"]
                if resposta in ["Ruim", "Crítico"]:
                    justificativa = st.text_input(
                        "Justificativa",
                        value=justificativa,
                        key=f"{aba}_{i}_just"
                    )
                else:
                    justificativa = ""

                df.at[i, "Resposta"] = resposta
                df.at[i, "Justificativa"] = justificativa

            st.session_state.avaliacoes[aba] = df
