import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm

# ======================================================
# CONFIG
# ======================================================
st.set_page_config("Painel Administração Contratual", layout="wide")

ARQUIVO_AVALIACOES = "avaliacoes.json"

VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0,
    "NA": None
}

# ======================================================
# PERSISTÊNCIA
# ======================================================
def salvar_avaliacoes(dados):
    with open(ARQUIVO_AVALIACOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_avaliacoes():
    if os.path.exists(ARQUIVO_AVALIACOES):
        with open(ARQUIVO_AVALIACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ======================================================
# FUNÇÕES DE NEGÓCIO
# ======================================================
def calcular_nota(df):
    df_validas = df[df["Resposta"] != "NA"].copy()
    if df_validas.empty:
        return None

    df_validas["valor"] = df_validas["Resposta"].map(VALORES)
    soma = (df_validas["valor"] * df_validas["Peso"]).sum()
    peso_total = df_validas["Peso"].sum()
    return soma / peso_total if peso_total > 0 else None

def cor_semaforo(nota):
    if nota is None:
        return colors.grey
    if nota <= 0.25:
        return colors.green
    elif nota <= 0.50:
        return colors.yellow
    elif nota < 0.75:
        return colors.orange
    else:
        return colors.red

def emoji_semaforo(nota):
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

# ======================================================
# PDF
# ======================================================
def gerar_pdf(cabecalho, avaliacao, caminho_pdf):

    doc = SimpleDocTemplate(
        caminho_pdf,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    story = []

    # -------- CAPA / CABEÇALHO --------
    story.append(Paragraph("<b>PAINEL DE ADMINISTRAÇÃO CONTRATUAL</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    for k, v in cabecalho.items():
        story.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))

    story.append(Spacer(1, 24))

    # -------- RESUMO EXECUTIVO --------
    story.append(Paragraph("<b>Resumo Executivo</b>", styles["Heading2"]))
    story.append(Spacer(1, 12))

    tabela = [["Disciplina", "Status"]]
    estilos = [
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("ALIGN", (1,1), (-1,-1), "CENTER")
    ]

    linha = 1
    for aba, df in avaliacao.items():
        codigo = df.iloc[0]["Codigo"]
        descricao = df.iloc[0]["Descricao"]
        nota = calcular_nota(df)

        tabela.append([f"{codigo} – {descricao}", ""])
        estilos.append(("BACKGROUND", (1, linha), (1, linha), cor_semaforo(nota)))
        linha += 1

    t = Table(tabela, colWidths=[13*cm, 3*cm])
    t.setStyle(TableStyle(estilos))
    story.append(t)

    # -------- JUSTIFICATIVAS --------
    story.append(PageBreak())
    story.append(Paragraph("<b>Justificativas</b>", styles["Heading2"]))
    story.append(Spacer(1, 12))

    for aba, df in avaliacao.items():
        df_j = df[df["Justificativa"].astype(str).str.strip() != ""]
        if df_j.empty:
            continue

        codigo = df.iloc[0]["Codigo"]
        descricao = df.iloc[0]["Descricao"]
        nota = calcular_nota(df)

        story.append(
            Paragraph(
                f"<b>{codigo} – {descricao}</b> ({emoji_semaforo(nota)})",
                styles["Heading3"]
            )
        )
        story.append(Spacer(1, 6))

        for tipo in ["Procedimento", "Acompanhamento"]:
            bloco = df_j[df_j["Tipo"] == tipo]
            if bloco.empty:
                continue

            story.append(Paragraph(f"<i>{tipo}</i>", styles["Normal"]))
            story.append(Spacer(1, 4))

            for _, row in bloco.iterrows():
                story.append(
                    Paragraph(
                        f"- <b>{row['Resposta']}</b>: {row['Justificativa']}",
                        styles["Normal"]
                    )
                )
                story.append(Spacer(1, 4))

        story.append(Spacer(1, 12))

    doc.build(story)

# ======================================================
# ESTADO
# ======================================================
if "avaliacoes_salvas" not in st.session_state:
    st.session_state.avaliacoes_salvas = carregar_avaliacoes()

if "avaliacao_ativa" not in st.session_state:
    st.session_state.avaliacao_ativa = None

# ======================================================
# CABEÇALHO
# ======================================================
st.title("Painel Administração Contratual")

st.subheader("Dados do Projeto")

col1, col2, col3 = st.columns(3)
nome_projeto = col1.text_input("Nome do Projeto")
cliente = col2.text_input("Cliente")
responsavel = col3.text_input("Responsável")

data_avaliacao = st.date_input("Data", datetime.now().date())
hora_avaliacao = st.time_input(
    "Hora",
    (datetime.utcnow() - timedelta(hours=3)).time()
)

cabecalho = {
    "Projeto": nome_projeto,
    "Cliente": cliente,
    "Responsável": responsavel,
    "Data": data_avaliacao.strftime("%d/%m/%Y"),
    "Hora": hora_avaliacao.strftime("%H:%M")
}

# ======================================================
# MENU
# ======================================================
st.divider()
opcao = st.radio("O que deseja fazer?", ["Nova Avaliação", "Abrir Avaliação Existente"])

# ======================================================
# ABRIR AVALIAÇÃO
# ======================================================
if opcao == "Abrir Avaliação Existente":

    if not st.session_state.avaliacoes_salvas:
        st.info("Nenhuma avaliação salva.")
        st.stop()

    chave = st.selectbox(
        "Selecione a avaliação",
        list(st.session_state.avaliacoes_salvas.keys())
    )

    dados = st.session_state.avaliacoes_salvas[chave]
    avaliacao = {}

    for aba, registros in dados["avaliacao"].items():
        avaliacao[aba] = pd.DataFrame(registros)

    st.session_state.avaliacao_ativa = avaliacao
    cabecalho = dados["cabecalho"]

# ======================================================
# UPLOAD EXCEL
# ======================================================
uploaded = st.file_uploader("Upload do Excel", type=["xlsx"])
if not uploaded:
    st.stop()

xls = pd.ExcelFile(uploaded)

if st.session_state.avaliacao_ativa is None:
    avaliacao = {}
    for aba in xls.sheet_names:
        df = xls.parse(aba)
        df["Resposta"] = "NA"
        df["Justificativa"] = ""
        avaliacao[aba] = df
    st.session_state.avaliacao_ativa = avaliacao

# ======================================================
# CANVAS
# ======================================================
st.subheader("Avaliação")

for aba, df in st.session_state.avaliacao_ativa.items():
    nota = calcular_nota(df)
    with st.expander(f"{emoji_semaforo(nota)} {df.iloc[0]['Codigo']} – {df.iloc[0]['Descricao']}"):
        for i, row in df.iterrows():
            resposta = st.selectbox(
                row["Pergunta"],
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
            else:
                justificativa = ""

            df.at[i, "Resposta"] = resposta
            df.at[i, "Justificativa"] = justificativa

# ======================================================
# SALVAR
# ======================================================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data_avaliacao} {hora_avaliacao.strftime('%H:%M:%S')}"
    st.session_state.avaliacoes_salvas[chave] = {
        "cabecalho": cabecalho,
        "avaliacao": {
            aba: df.to_dict(orient="records")
            for aba, df in st.session_state.avaliacao_ativa.items()
        }
    }
    salvar_avaliacoes(st.session_state.avaliacoes_salvas)
    st.success("Avaliação salva com sucesso.")

# ======================================================
# PDF
# ======================================================
if st.button("📄 Gerar PDF"):
    gerar_pdf(cabecalho, st.session_state.avaliacao_ativa, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button(
            "⬇️ Download PDF",
            f,
            file_name="avaliacao.pdf",
            mime="application/pdf"
        )
