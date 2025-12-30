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

            codigo = df.iloc[0]["Codigo"] if "Codigo" in df.columns else aba
            descricao = df.iloc[0]["Descricao"] if "Descricao" in df.columns else ""

           with st.expander(f"🧩 {codigo} – {descricao}", expanded=False):

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


      
