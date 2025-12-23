import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import date
import io

st.set_page_config(page_title="Painel Administração Contratual", layout="wide")

st.title("Painel Administração Contratual – Piloto Interno")
st.subheader("Dados do Relatório")

col1, col2 = st.columns(2)
with col1:
    nome_projeto = st.text_input("Nome do Projeto")
    cliente = st.text_input("Cliente")
with col2:
    responsavel = st.text_input("Responsável / Consultor")
    empresa = st.text_input("Empresa / Assinatura", value="M2L – Gestão de Empreendimentos")

data_avaliacao = st.date_input("Data da Avaliação", value=date.today())

st.divider()
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

    # ============================
# Consolidação de notas por processo (para PDF)
# ============================
resultados_canvas = {}

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

    # Nota média simples do processo
    nota_final = round((nota_proc + nota_acomp) / 2, 2)

    resultados_canvas[aba] = nota_final
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
meta = {
    "Projeto": nome_projeto,
    "Cliente": cliente,
    "Responsável": responsavel,
    "Empresa": empresa,
    "Data": data_avaliacao.strftime("%d/%m/%Y")
}

st.subheader("Relatórios")

if st.button("📄 Gerar PDF Executivo"):
    pdf_exec = gerar_pdf_executivo(
    resultados_canvas,
    st.session_state.avaliacoes,
    meta
)

    st.download_button(
        "Download PDF Executivo",
        data=pdf_exec,
        file_name="relatorio_executivo_adm_contratual.pdf",
        mime="application/pdf"
    )

if stpdf_comp = gerar_pdf_completo(
    st.session_state.avaliacoes,
    meta
)

    st.download_button(
        "Download PDF Completo",
        data=pdf_comp,
        file_name="relatorio_completo_adm_contratual.pdf",
        mime="application/pdf"
    )
def gerar_pdf_executivo(dados, respostas, meta):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph("<b>Relatório Executivo – Administração Contratual</b>", styles["Title"]))
    elementos.append(Spacer(1, 12))

    for k, v in meta.items():
        elementos.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))

    elementos.append(Spacer(1, 12))

    tabela = [["Processo", "Nota"]]
    for processo, nota in dados.items():
        tabela.append([processo, f"{nota:.2f}"])

    t = Table(tabela)
    t.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey)
    ]))

    elementos.append(t)
    doc.build(elementos)
    buffer.seek(0)
    return buffer


def gerar_pdf_completo(respostas, meta):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph("<b>Relatório Completo – Administração Contratual</b>", styles["Title"]))
    elementos.append(Spacer(1, 12))

    for k, v in meta.items():
        elementos.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))

    elementos.append(PageBreak())

    for processo, itens in respostas.items():
        elementos.append(Paragraph(f"<b>{processo}</b>", styles["Heading2"]))
        elementos.append(Spacer(1, 8))

        for item in itens:
            elementos.append(Paragraph(
                f"{item['codigo']} – {item['pergunta']}<br/>"
                f"<b>Avaliação:</b> {item['avaliacao']}<br/>"
                f"<b>Comentário:</b> {item['comentario']}",
                styles["Normal"]
            ))
            elementos.append(Spacer(1, 6))

        elementos.append(PageBreak())

    doc.build(elementos)
    buffer.seek(0)
    return buffer
