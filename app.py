import streamlit as st
import pandas as pd
import json
import os
import io
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

# ==================================================
# CONFIGURAÇÃO
# ==================================================
st.set_page_config("Painel Administração Contratual", layout="wide")
AVALIACOES_FILE = "avaliacoes.json"

# ==================================================
# PERSISTÊNCIA
# ==================================================
def salvar_avaliacoes(dados):
    with open(AVALIACOES_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_avaliacoes():
    if os.path.exists(AVALIACOES_FILE):
        with open(AVALIACOES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ==================================================
# REGRAS DE AVALIAÇÃO (INTERNO)
# ==================================================
VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0,
    "NA": None
}

def calcular_media_ponderada(df):
    if "Peso" not in df.columns:
        df["Peso"] = 1.0

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

# ==================================================
# PDF
# ==================================================
def gerar_pdf(avaliacoes, cabecalho):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    styles = getSampleStyleSheet()
    story = []

    # Cabeçalho
    story.append(Paragraph("<b>Painel Administração Contratual – Avaliação</b>", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Projeto:</b> {cabecalho['projeto']}", styles["Normal"]))
    story.append(Paragraph(f"<b>Cliente:</b> {cabecalho['cliente']}", styles["Normal"]))
    story.append(Paragraph(f"<b>Responsável:</b> {cabecalho['responsavel']}", styles["Normal"]))
    story.append(Paragraph(f"<b>Data:</b> {cabecalho['data']}", styles["Normal"]))
    story.append(Spacer(1, 20))

    # Canvas
    story.append(Paragraph("<b>Resumo Executivo – Canvas</b>", styles["Heading2"]))
    story.append(Spacer(1, 12))

    for aba, df in avaliacoes.items():
        nota = calcular_media_ponderada(df)
        semaforo = cor_por_nota(nota)
        story.append(Paragraph(f"{semaforo} <b>{aba}</b>", styles["Normal"]))
        story.append(Spacer(1, 6))

    story.append(PageBreak())

    # Comentários
    story.append(Paragraph("<b>Comentários – Pontos Críticos</b>", styles["Heading2"]))
    story.append(Spacer(1, 12))

    encontrou = False
    for aba, df in avaliacoes.items():
        criticos = df[df["Resposta"].isin(["Ruim", "Crítico"])]
        if not criticos.empty:
            encontrou = True
            story.append(Paragraph(f"<b>{aba}</b>", styles["Heading3"]))
            for _, row in criticos.iterrows():
                story.append(Paragraph(
                    f"- <b>{row['Pergunta']}</b> ({row['Resposta']})",
                    styles["Normal"]
                ))
                story.append(Paragraph(
                    f"Justificativa: {row['Justificativa']}",
                    styles["Italic"]
                ))
                story.append(Spacer(1, 6))
            story.append(Spacer(1, 12))

    if not encontrou:
        story.append(Paragraph("Nenhum ponto crítico identificado.", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer

# ==================================================
# ESTADO
# ==================================================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

# ==================================================
# INTERFACE
# ==================================================
st.title("Painel Administração Contratual")

st.markdown("### Informações da Avaliação")
data_avaliacao = st.date_input("Data da avaliação", datetime.now().date())
hora_avaliacao = st.time_input("Hora da avaliação", datetime.now().time())

uploaded_file = st.file_uploader("Carregar Excel do Projeto", type=["xlsx"])
if not uploaded_file:
    st.info("⬆️ Faça upload do Excel para iniciar.")
    st.stop()

xls = pd.ExcelFile(uploaded_file)

st.subheader("Canvas do Projeto")

for aba in xls.sheet_names:
    df = xls.parse(aba)

    if aba not in st.session_state.avaliacoes:
        df["Resposta"] = "NA"
        df["Justificativa"] = ""
        st.session_state.avaliacoes[aba] = df
    else:
        df = st.session_state.avaliacoes[aba]

    nota = calcular_media_ponderada(df)
    semaforo = cor_por_nota(nota)

    with st.expander(f"{semaforo} {aba}", expanded=False):
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

            df.at[i, "Resposta"] = resposta
            df.at[i, "Justificativa"] = justificativa

        st.session_state.avaliacoes[aba] = df

st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data_avaliacao.strftime('%Y-%m-%d')} {hora_avaliacao.strftime('%H:%M')}"
    dados = {aba: df.to_dict(orient="records") for aba, df in st.session_state.avaliacoes.items()}
    st.session_state.avaliacoes_por_data[chave] = dados
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success(f"Avaliação salva em {chave}")

st.divider()
st.subheader("Exportação em PDF")

nome_projeto = st.text_input("Nome do Projeto")
nome_cliente = st.text_input("Nome do Cliente")
responsavel = st.text_input("Responsável")

if st.button("📄 Gerar PDF"):
    if not nome_projeto or not nome_cliente or not responsavel:
        st.error("Preencha todos os campos do cabeçalho.")
    else:
        cabecalho = {
            "projeto": nome_projeto,
            "cliente": nome_cliente,
            "responsavel": responsavel,
            "data": f"{data_avaliacao.strftime('%d/%m/%Y')} {hora_avaliacao.strftime('%H:%M')}"
        }
        pdf = gerar_pdf(st.session_state.avaliacoes, cabecalho)
        st.download_button(
            "⬇️ Download do PDF",
            data=pdf,
            file_name="Painel_Administracao_Contratual.pdf",
            mime="application/pdf"
        )
