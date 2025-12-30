import streamlit as st
import pandas as pd

VALOR_RESPOSTA = {
    "Bom": 0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1
}

def calcular_media_ponderada(df):
    if "Peso" not in df.columns:
        return None

    total_peso = 0
    soma = 0

    for _, row in df.iterrows():
        resposta = row["Resposta"]
        peso = row["Peso"]

        if resposta in VALOR_RESPOSTA:
            soma += VALOR_RESPOSTA[resposta] * peso
            total_peso += peso

    if total_peso == 0:
        return None

    return soma / total_peso


def semaforo(media):
    if media is None:
        return "⚪"
    if media <= 0.25:
        return "🟢"
    if media <= 0.50:
        return "🟡"
    if media < 0.75:
        return "🟠"
    return "🔴"

st.set_page_config(
    page_title="Painel Administração Contratual",
    layout="wide"
)

st.title("Painel Administração Contratual – Piloto Interno")

from datetime import date

if "data_avaliacao" not in st.session_state:
    st.session_state.data_avaliacao = date.today()

st.markdown("### 📅 Data da Avaliação")

st.session_state.data_avaliacao = st.date_input(
    "Selecione a data da avaliação",
    value=st.session_state.data_avaliacao
)

st.divider()


uploaded_file = st.file_uploader(
    "Carregar Excel do Projeto",
    type=["xlsx"]
)

if uploaded_file is not None:
    xls = pd.ExcelFile(uploaded_file)

    if "avaliacoes" not in st.session_state:
        st.session_state.avaliacoes = {}

    st.subheader("Painel Canvas")

    for aba in xls.sheet_names:
        df_original = xls.parse(aba)

        if aba not in st.session_state.avaliacoes:
            df_original["Resposta"] = "NA"
            df_original["Justificativa"] = ""
            st.session_state.avaliacoes[aba] = df_original.copy()

        df = st.session_state.avaliacoes[aba]

              codigo = df.iloc[0]["Codigo"] if "Codigo" in df.columns else aba
              descricao = df.iloc[0]["Descricao"] if "Descricao" in df.columns else ""

              media = calcular_media_ponderada(df)
              icone = semaforo(media)

              with st.expander(f"{icone} {codigo} – {descricao}", expanded=False):


            if "Pergunta" not in df.columns:
                st.error("Coluna 'Pergunta' não encontrada no Excel.")
                continue

            df_perguntas = df[df["Pergunta"].notna() & (df["Pergunta"] != "")]

            st.caption(f"Total de perguntas: {len(df_perguntas)}")

            if df_perguntas.empty:
                st.warning("Nenhuma pergunta encontrada neste processo.")
            else:
                for i, row in df_perguntas.iterrows():
                    st.markdown(f"**{row['Pergunta']}**")

                    resposta = st.radio(
                        "Avaliação",
                        ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                        index=["Bom", "Médio", "Ruim", "Crítico", "NA"].index(row["Resposta"]),
                        key=f"{aba}_{i}_resp",
                        horizontal=True
                    )

                    justificativa = row["Justificativa"]

                    if resposta in ["Ruim", "Crítico"]:
                        justificativa = st.text_area(
                            "Justificativa",
                            value=justificativa,
                            key=f"{aba}_{i}_just"
                        )
                    else:
                        justificativa = ""

                    df.at[i, "Resposta"] = resposta
                    df.at[i, "Justificativa"] = justificativa

                    st.divider()

            st.session_state.avaliacoes[aba] = df

