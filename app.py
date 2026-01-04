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
    return (df_validas["valor"] * df_validas["Peso"]).sum() / df_validas["Peso"].sum()

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

    doc = SimpleDocTemplate(caminho_pdf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # CAPA
    story.append(Paragraph("<b>PAINEL DE ADMINISTRAÇÃO CONTRATUAL</b>", styles["Title"]))
    story.append(Spacer(1, 12))
    for k, v in cabecalho.items():
        story.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))
    story.append(Spacer(1, 24))

    # RESUMO EXECUTIVO
    story.append(Paragraph("<b>Resumo Executivo</b>", styles["Heading2"]))
    story.append(Spacer(1, 12))

    tabela = [["Disciplina", "Status"]]
    estilos = [("GRID", (0,0), (-1,-1), 0.5, colors.black)]

    linha = 1
    for aba, df in avaliacao.items():
        nota = calcular_nota(df)
        tabela.append([f"{df.iloc[0]['Codigo']} – {df.iloc[0]['Descricao']}", ""])
        estilos.append(("BACKGROUND", (1, linha), (1, linha), cor_semaforo(nota)))
        linha += 1

    t = Table(tabela, colWidths=[14*cm, 2*cm])
    t.setStyle(TableStyle(estilos))
    story.append(t)

    # JUSTIFICATIVAS
    story.append(PageBreak())
    story.append(Paragraph("<b>Justificativas</b>", styles["Heading2"]))
    story.append(Spacer(1, 12))

    for aba, df in avaliacao.items():
        df_j = df[df["Justificativa"].astype(str).str.strip() != ""]
        if df_j.empty:
            continue

        nota = calcular_nota(df)

        cab = Table(
            [[f"{df.iloc[0]['Codigo']} – {df.iloc[0]['Descricao']}", ""]],
            colWidths=[14*cm, 2*cm]
        )
        cab.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("BACKGROUND", (1,0), (1,0), cor_semaforo(nota))
        ]))
        story.append(cab)
        story.append(Spacer(1, 6))

        for tipo in ["Procedimento", "Acompanhamento"]:
            bloco = df_j[df_j["Tipo"] == tipo]
            if bloco.empty:
                continue

            story.append(Paragraph(f"<b>{tipo}</b>", styles["Normal"]))
            story.append(Spacer(1, 4))

            for _, r in bloco.iterrows():
                story.append(Paragraph(
                    f"- <b>{r['Resposta']}</b>: {r['Justificativa']}",
                    styles["Normal"]
                ))
                story.append(Spacer(1, 3))

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

col1, col2, col3 = st.columns(3)
projeto = col1.text_input("Projeto")
cliente = col2.text_input("Cliente")
responsavel = col3.text_input("Responsável")

data = st.date_input("Data", datetime.now().date())
hora = st.time_input("Hora", (datetime.utcnow() - timedelta(hours=3)).time())

cabecalho = {
    "Projeto": projeto,
    "Cliente": cliente,
    "Responsável": responsavel,
    "Data": data.strftime("%d/%m/%Y"),
    "Hora": hora.strftime("%H:%M")
}

# ======================================================
# MENU
# ======================================================
opcao = st.radio("O que deseja fazer?", ["Nova Avaliação", "Abrir Avaliação Existente"])

if opcao == "Abrir Avaliação Existente":
    chave = st.selectbox("Selecione a avaliação", st.session_state.avaliacoes_salvas.keys())
    dados = st.session_state.avaliacoes_salvas[chave]
    st.session_state.avaliacao_ativa = {
        k: pd.DataFrame(v) for k, v in dados["avaliacao"].items()
    }
    cabecalho = dados["cabecalho"]

uploaded = st.file_uploader("Upload do Excel", type=["xlsx"])
if not uploaded:
    st.stop()

xls = pd.ExcelFile(uploaded)

if st.session_state.avaliacao_ativa is None:
    st.session_state.avaliacao_ativa = {}
    for aba in xls.sheet_names:
        df = xls.parse(aba)
        df["Resposta"] = "NA"
        df["Justificativa"] = ""
        st.session_state.avaliacao_ativa[aba] = df

# ======================================================
# CANVAS
# ======================================================
st.subheader("Avaliação")

for aba, df in st.session_state.avaliacao_ativa.items():
    nota = calcular_nota(df)

    with st.expander(f"{emoji_semaforo(nota)} {df.iloc[0]['Codigo']} – {df.iloc[0]['Descricao']}"):

        for tipo in ["Procedimento", "Acompanhamento"]:
            bloco = df[df["Tipo"] == tipo]

            if bloco.empty:
                continue

            with st.expander(tipo, expanded=True):
                for i, row in bloco.iterrows():
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
# SALVAR / PDF
# ======================================================
if st.button("💾 Salvar Avaliação"):
    chave = f"{data} {hora.strftime('%H:%M:%S')}"
    st.session_state.avaliacoes_salvas[chave] = {
        "cabecalho": cabecalho,
        "avaliacao": {
            k: v.to_dict(orient="records")
            for k, v in st.session_state.avaliacao_ativa.items()
        }
    }
    salvar_avaliacoes(st.session_state.avaliacoes_salvas)
    st.success("Avaliação salva.")

if st.button("📄 Gerar PDF"):
    gerar_pdf(cabecalho, st.session_state.avaliacao_ativa, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF", f, "avaliacao.pdf", "application/pdf")
