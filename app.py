import streamlit as st
import pandas as pd

st.set_page_config(page_title="Painel Administração Contratual", layout="wide")

st.title("Painel Administração Contratual – Piloto Interno")
st.caption("Upload do Excel e preenchimento manual das avaliações")

VALORES = {
    "Bom": 10,
    "Médio": 7,
    "Ruim": 4,
    "Crítico": 0
}

CORES = {
    "Bom": "🟢",
    "Médio": "🟡",
    "Ruim": "🔴",
    "Crítico": "⚫",
    "NA": "⚪"
}

def calcular_nota(df):
    df_calc = df[df["Resposta"] != "NA"].copy()
    if df_calc.empty:
        return None
    df_calc["Valor"] = df_calc["Resposta"].map(VALORES)
    nota = (df_calc["Valor"] * df_calc["Peso"]).sum() / df_calc["Peso"].sum()
    return round(nota, 2)

def status_por_nota(nota):
    if nota is None:
        return "NA"
    if nota >= 8:
        return "Bom"
    if nota >= 6:
        return "Médio"
    if nota >= 4:
        return "Ruim"
    return "Crítico"

uploaded_file = st.file_uploader("Carregar Excel do Projeto", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)

    if "avaliacoes" not in st.session_state:
        st.session_state.avaliacoes = {}

    st.subheader("Canvas do Projeto")

    for aba in xls.sheet_names:
        df = xls.parse(aba)

        if aba in st.session_state.avaliacoes:
            df[["Resposta", "Justificativa"]] = st.session_state.avaliacoes[aba]
        else:
            df["Resposta"] = "NA"
            df["Justificativa"] = ""

        proc = df[df["Tipo"] == "Procedimento"]
        acomp = df[df["Tipo"] == "Acompanhamento"]

        nota_proc = calcular_nota(proc)
        nota_acomp = calcular_nota(acomp)

        status_proc = status_por_nota(nota_proc)
        status_acomp = status_por_nota(nota_acomp)

        with st.expander(
            f"{aba} | Procedimentos: {CORES[status_proc]} {nota_proc} | "
            f"Acompanhamento: {CORES[status_acomp]} {nota_acomp}"
        ):
            st.markdown("### Procedimentos")
            for i, row in proc.iterrows():
                resposta = st.selectbox(
                    row["Pergunta"],
                    ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                    key=f"{aba}_{i}_p"
                )
                justificativa = ""
                if resposta in ["Ruim", "Crítico"]:
                    justificativa = st.text_input("Justificativa", key=f"{aba}_{i}_pj")

                df.at[i, "Resposta"] = resposta
                df.at[i, "Justificativa"] = justificativa

            st.markdown("### Acompanhamento")
            for i, row in acomp.iterrows():
                resposta = st.selectbox(
                    row["Pergunta"],
                    ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                    key=f"{aba}_{i}_a"
                )
                justificativa = ""
                if resposta in ["Ruim", "Crítico"]:
                    justificativa = st.text_input("Justificativa", key=f"{aba}_{i}_aj")

                df.at[i, "Resposta"] = resposta
                df.at[i, "Justificativa"] = justificativa

            if st.button("Salvar Avaliação", key=f"salvar_{aba}"):
                st.session_state.avaliacoes[aba] = df[["Resposta", "Justificativa"]]
                st.success("Avaliação salva")

    st.subheader("Comentários (Ruim / Crítico)")
    for aba, dados in st.session_state.avaliacoes.items():
        df_base = xls.parse(aba)
        df_base[["Resposta", "Justificativa"]] = dados
        problemas = df_base[df_base["Resposta"].isin(["Ruim", "Crítico"])]

        if not problemas.empty:
            st.markdown(f"### {aba}")
            for _, row in problemas.iterrows():
                st.markdown(f"**{row['Pergunta']}** ({row['Resposta']})")
                st.write(row["Justificativa"])
