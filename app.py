import streamlit as st
import pandas as pd
# ============================
# SESSION STATE INICIAL
# ============================
if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm


def gerar_pdf_executivo(resultados_canvas, avaliacoes, meta):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, height - 2 * cm, "Relatório Executivo – Administração Contratual")

    y = height - 4 * cm
    c.setFont("Helvetica", 11)

    for processo, nota in resultados_canvas.items():
        c.drawString(2 * cm, y, f"{processo}: Nota {nota}")
        y -= 1 * cm
        if y < 3 * cm:
            c.showPage()
            y = height - 3 * cm

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def gerar_pdf_completo(avaliacoes, meta):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, height - 2 * cm, "Relatório Completo – Administração Contratual")

    y = height - 4 * cm
    c.setFont("Helvetica", 10)

    for processo, dados in avaliacoes.items():
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, processo)
        y -= 1 * cm

        c.setFont("Helvetica", 10)
        for resposta, justificativa in zip(dados["Resposta"], dados["Justificativa"]):
            linha = f"- {resposta}"
            if justificativa:
                linha += f": {justificativa}"

            c.drawString(2.5 * cm, y, linha)
            y -= 0.8 * cm

            if y < 3 * cm:
                c.showPage()
                y = height - 3 * cm

        y -= 0.5 * cm

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

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
    mapa = {
        "Bom": 0.0,
        "Médio": 0.3333,
        "Ruim": 0.6667,
        "Crítico": 1.0
    }

    df_validos = df[df["Resposta"].isin(mapa.keys())]

    if df_validos.empty:
        return None

    valores = df_validos["Resposta"].map(mapa)
    pesos = df_validos["Peso"]

    nota = (valores * pesos).sum() / pesos.sum()

    return round(nota, 4)


def status_por_nota(nota):
    if nota is None:
        return "NA"
    elif nota <= 0.25:
        return "Bom"
    elif nota <= 0.50:
        return "Médio"
    elif nota < 0.75:
        return "Ruim"
    else:
        return "Crítico"


uploaded_file = st.file_uploader("Carregar Excel do Projeto", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)

    if "avaliacoes" not in st.session_state:
        st.session_state.avaliacoes = {}

    st.subheader("Canvas do Projeto")

    # ============================
    # AVALIAÇÃO POR ABA
    # ============================
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

    resultados_canvas[aba] = {
        "nota": None,
        "status": "NA"
    }

    if nota_proc is None and nota_acomp is None:
        pass
    elif nota_proc is None:
        resultados_canvas[aba]["nota"] = nota_acomp
        resultados_canvas[aba]["status"] = status_por_nota(nota_acomp)
    elif nota_acomp is None:
        resultados_canvas[aba]["nota"] = nota_proc
        resultados_canvas[aba]["status"] = status_por_nota(nota_proc)
    else:
        nota_final = (nota_proc + nota_acomp) / 2
        resultados_canvas[aba]["nota"] = round(nota_final, 4)
        resultados_canvas[aba]["status"] = status_por_nota(nota_final)

    with st.expander(
        f"{aba} | "
        f"Procedimentos: {CORES[status_proc]} {status_proc} | "
        f"Acompanhamento: {CORES[status_acomp]} {status_acomp}"
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
                justificativa = st.text_input(
                    "Justificativa",
                    key=f"{aba}_{i}_pj"
                )

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
                justificativa = st.text_input(
                    "Justificativa",
                    key=f"{aba}_{i}_aj"
                )

            df.at[i, "Resposta"] = resposta
            df.at[i, "Justificativa"] = justificativa

        if st.button("Salvar Avaliação", key=f"salvar_{aba}"):
            st.session_state.avaliacoes[aba] = df[["Resposta", "Justificativa"]]
            st.success("Avaliação salva")
            st.rerun()


    # ============================
    # CONSOLIDAÇÃO PARA PDF
    # ============================
 
  if nota_proc is None and nota_acomp is None:
    pass
  elif nota_proc is None:
    resultados_canvas[aba]["nota"] = nota_acomp
    resultados_canvas[aba]["status"] = status_por_nota(nota_acomp)
  elif nota_acomp is None:
    resultados_canvas[aba]["nota"] = nota_proc
    resultados_canvas[aba]["status"] = status_por_nota(nota_proc)
  else:
    nota_final = (nota_proc + nota_acomp) / 2
    resultados_canvas[aba]["nota"] = round(nota_final, 4)
    resultados_canvas[aba]["status"] = status_por_nota(nota_final)


    # ============================
    # COMENTÁRIOS
    # ============================
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

# ============================
# CONSOLIDAÇÃO DO CANVAS
# ============================
resultados_canvas = {}

if uploaded_file and "avaliacoes" in st.session_state:
    for aba, dados in st.session_state.avaliacoes.items():
        df_base = xls.parse(aba)
        df_base[["Resposta", "Justificativa"]] = dados

        proc = df_base[df_base["Tipo"] == "Procedimento"]
        acomp = df_base[df_base["Tipo"] == "Acompanhamento"]

        nota_proc = calcular_nota(proc)
        nota_acomp = calcular_nota(acomp)

        if nota_proc is None and nota_acomp is None:
            resultados_canvas[aba] = "NA"
        elif nota_proc is None:
            resultados_canvas[aba] = nota_acomp
        elif nota_acomp is None:
            resultados_canvas[aba] = nota_proc
        else:
            resultados_canvas[aba] = round((nota_proc + nota_acomp) / 2, 2)


st.subheader("Relatórios")

if st.button("📄 Gerar PDF Executivo"):
    if not resultados_canvas:
        st.warning("Nenhuma avaliação foi salva ainda.")
    else:
        pdf_exec = gerar_pdf_executivo(
            resultados_canvas,
            st.session_state.avaliacoes,
            meta
        )
        st.download_button(
            "Download PDF Executivo",
            data=pdf_exec,
            file_name="relatorio_executivo_adm_contratual.pdf",
            mime="application/pdf",
            key="download_pdf_exec"
        )

if st.button("📄 Gerar PDF Completo"):
    if not st.session_state.avaliacoes:
        st.warning("Nenhuma avaliação foi salva ainda.")
    else:
        pdf_comp = gerar_pdf_completo(
            st.session_state.avaliacoes,
            meta
        )
        st.download_button(
            "Download PDF Completo",
            data=pdf_comp,
            file_name="relatorio_completo_adm_contratual.pdf",
            mime="application/pdf",
            key="download_pdf_completo"
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
