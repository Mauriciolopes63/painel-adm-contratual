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

# =========================================================
# CONFIGURAÇÕES
# =========================================================
st.set_page_config("Painel Administração Contratual", layout="wide")

ARQ_AVALIACOES = "avaliacoes.json"

VALORES = {
    "Bom": 0.0,
    "Médio": 0.33,
    "Ruim": 0.66,
    "Crítico": 1.0,
    "NA": None
}

CORES = {
    "verde": colors.green,
    "amarelo": colors.yellow,
    "laranja": colors.orange,
    "vermelho": colors.red,
    "cinza": colors.lightgrey
}

# =========================================================
# PERSISTÊNCIA
# =========================================================
def carregar_avaliacoes():
    if os.path.exists(ARQ_AVALIACOES):
        with open(ARQ_AVALIACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_avaliacoes(dados):
    with open(ARQ_AVALIACOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# =========================================================
# CÁLCULOS
# =========================================================
def media_ponderada(df):
    df = df[df["Resposta"] != "NA"].copy()
    if df.empty:
        return None
    df["valor"] = df["Resposta"].map(VALORES)
    return (df["valor"] * df["Peso"]).sum() / df["Peso"].sum()

def cor_semaforo(nota):
    if nota is None:
        return "cinza"
    if nota <= 0.25:
        return "verde"
    if nota <= 0.5:
        return "amarelo"
    if nota < 0.75:
        return "laranja"
    return "vermelho"

def emoji(cor):
    return {
        "verde": "🟢",
        "amarelo": "🟡",
        "laranja": "🟠",
        "vermelho": "🔴",
        "cinza": "⚪"
    }[cor]

# =========================================================
# PDF
# =========================================================
def gerar_pdf(cabecalho, avaliacao, caminho):
    styles = getSampleStyleSheet()
    story = []

    # Capa
    story.append(Paragraph("<b>RELATÓRIO DE AVALIAÇÃO CONTRATUAL</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    for k, v in cabecalho.items():
        story.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))

    story.append(Spacer(1, 24))

    # Resumo por disciplina
    story.append(Paragraph("<b>Resumo por Disciplina</b>", styles["Heading2"]))
    story.append(Spacer(1, 12))

    tabela = [["", "Disciplina"]]

    for aba, df in avaliacao.items():
        nota = media_ponderada(df)
        cor = cor_semaforo(nota)
        tabela.append(["■", f"{df.iloc[0]['Codigo']} – {df.iloc[0]['Descricao']}"])

    t = Table(tabela, colWidths=[20, 450])
    estilo = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (0, -1), "CENTER")
    ]

    for i, (aba, df) in enumerate(avaliacao.items(), start=1):
        cor = CORES[cor_semaforo(media_ponderada(df))]
        estilo.append(("BACKGROUND", (0, i), (0, i), cor))

    t.setStyle(TableStyle(estilo))
    story.append(t)

    # Justificativas
    story.append(PageBreak())
    story.append(Paragraph("<b>Justificativas</b>", styles["Heading2"]))
    story.append(Spacer(1, 12))

    for aba, df in avaliacao.items():
        df_j = df[df["Resposta"].isin(["Ruim", "Crítico"])]
        if df_j.empty:
            continue

        cor = CORES[cor_semaforo(media_ponderada(df))]
        story.append(
            Table(
                [["", f"{df.iloc[0]['Codigo']} – {df.iloc[0]['Descricao']}"]],
                colWidths=[15, 455],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (0, 0), cor),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey)
                ])
            )
        )
        story.append(Spacer(1, 6))

        for _, r in df_j.iterrows():
            story.append(Paragraph(
                f"- <b>{r['Resposta']}:</b> {r['Justificativa']}",
                styles["Normal"]
            ))
            story.append(Spacer(1, 4))

        story.append(Spacer(1, 12))

    SimpleDocTemplate(caminho, pagesize=A4).build(story)

# =========================================================
# ESTADO
# =========================================================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {}

if "modo" not in st.session_state:
    st.session_state.modo = None

# =========================================================
# UI – TOPO
# =========================================================
st.title("Painel Administração Contratual")

col1, col2 = st.columns(2)
with col1:
    if st.button("🆕 Nova Avaliação"):
        st.session_state.modo = "nova"
        st.session_state.avaliacao_atual = {}

with col2:
    if st.button("📂 Abrir Avaliação Existente"):
        st.session_state.modo = "abrir"

# =========================================================
# ABRIR AVALIAÇÃO
# =========================================================
if st.session_state.modo == "abrir":
    avals = st.session_state.avaliacoes_por_data
    if not avals:
        st.info("Nenhuma avaliação salva.")
        st.stop()

    data_sel = st.selectbox("Selecione a avaliação", list(avals.keys()))
    if st.button("Abrir"):
        nova = {}
        for aba, registros in avals[data_sel].items():
            nova[aba] = pd.DataFrame(registros)
        st.session_state.avaliacao_atual = nova
        st.success("Avaliação carregada.")

# =========================================================
# DADOS DA AVALIAÇÃO
# =========================================================
st.markdown("### Informações da Avaliação")
data = st.date_input("Data", datetime.now().date())
hora = st.time_input("Hora", (datetime.utcnow() - timedelta(hours=3)).time())

# =========================================================
# UPLOAD EXCEL
# =========================================================
arquivo = st.file_uploader("Upload do Excel", type=["xlsx"])
if not arquivo:
    st.stop()

xls = pd.ExcelFile(arquivo)

# =========================================================
# CANVAS
# =========================================================
for aba in xls.sheet_names:
    if aba not in st.session_state.avaliacao_atual:
        df = xls.parse(aba)
        df["Resposta"] = "NA"
        df["Justificativa"] = ""
        st.session_state.avaliacao_atual[aba] = df
    else:
        df = st.session_state.avaliacao_atual[aba]

    nota = media_ponderada(df)
    cor = cor_semaforo(nota)

    with st.expander(f"{emoji(cor)} {df.iloc[0]['Codigo']} – {df.iloc[0]['Descricao']}"):
        for i, r in df.iterrows():
            resp = st.selectbox(
                r["Pergunta"],
                ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                index=["Bom", "Médio", "Ruim", "Crítico", "NA"].index(r["Resposta"]),
                key=f"{aba}_{i}"
            )
            df.at[i, "Resposta"] = resp

            if resp in ["Ruim", "Crítico"]:
                df.at[i, "Justificativa"] = st.text_input(
                    "Justificativa",
                    value=r["Justificativa"],
                    key=f"{aba}_{i}_j"
                )

# =========================================================
# SALVAR / PDF
# =========================================================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data} {hora.strftime('%H:%M')}"
    st.session_state.avaliacoes_por_data[chave] = {
        aba: df.to_dict(orient="records")
        for aba, df in st.session_state.avaliacao_atual.items()
    }
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success("Avaliação salva.")

if st.button("📄 Gerar PDF"):
    cab = {
        "Data": data.strftime("%d/%m/%Y"),
        "Hora": hora.strftime("%H:%M")
    }
    gerar_pdf(cab, st.session_state.avaliacao_atual, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Baixar PDF", f, file_name="avaliacao.pdf")
