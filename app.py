import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# ===============================
# CONFIG
# ===============================
st.set_page_config("Painel Administração Contratual", layout="wide")

AVALIACOES_FILE = "avaliacoes.json"

# ===============================
# PERSISTÊNCIA
# ===============================
def salvar_avaliacoes(dados):
    with open(AVALIACOES_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_avaliacoes():
    if os.path.exists(AVALIACOES_FILE):
        with open(AVALIACOES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ===============================
# FUNÇÕES DE NEGÓCIO
# ===============================
VALORES = {
    "Bom": 0.0,
    "Médio": 0.33,
    "Ruim": 0.66,
    "Crítico": 1.0,
    "NA": None
}

def calcular_media(df):
    validas = df[df["Resposta"] != "NA"].copy()
    if validas.empty:
        return None
    validas["valor"] = validas["Resposta"].map(VALORES)
    return (validas["valor"] * validas["Peso"]).sum() / validas["Peso"].sum()

def texto_semaforo(nota):
    if nota is None:
        return "N/A"
    if nota <= 0.25:
        return "VERDE"
    elif nota <= 0.50:
        return "AMARELO"
    elif nota < 0.75:
        return "LARANJA"
    else:
        return "VERMELHO"

# ===============================
# PDF
# ===============================
def gerar_pdf(cabecalho, avaliacoes, caminho):
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>Painel Administração Contratual</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    for k, v in cabecalho.items():
        story.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))

    story.append(PageBreak())

    for aba, registros in avaliacoes.items():
        df = pd.DataFrame(registros)
        nota = calcular_media(df)
        status = texto_semaforo(nota)

        story.append(Paragraph(f"<b>{aba}</b> – Status: {status}", styles["Heading2"]))
        story.append(Spacer(1, 8))

        for _, row in df.iterrows():
            story.append(Paragraph(
                f"- {row['Pergunta']} | Resposta: {row['Resposta']} | Justificativa: {row.get('Justificativa','')}",
                styles["Normal"]
            ))

        story.append(PageBreak())

    pdf = SimpleDocTemplate(caminho, pagesize=A4)
    pdf.build(story)

# ===============================
# ESTADO
# ===============================
if "modo" not in st.session_state:
    st.session_state.modo = None

if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

# ===============================
# TELA INICIAL
# ===============================
st.title("Painel Administração Contratual")
st.subheader("O que deseja fazer?")

col1, col2 = st.columns(2)

with col1:
    if st.button("🆕 Nova Avaliação", use_container_width=True):
        st.session_state.modo = "nova"

with col2:
    if st.button("📂 Abrir Avaliação Existente", use_container_width=True):
        st.session_state.modo = "abrir"

if st.session_state.modo is None:
    st.stop()

# ===============================
# CABEÇALHO
# ===============================
st.markdown("### Dados do Empreendimento")

nome_projeto = st.text_input("Nome do Projeto")
nome_cliente = st.text_input("Cliente")
responsavel = st.text_input("Responsável")

data_avaliacao = st.date_input("Data", datetime.now().date())
hora_avaliacao = st.time_input(
    "Hora",
    (datetime.utcnow() - timedelta(hours=3)).time()
)

cabecalho = {
    "Projeto": nome_projeto,
    "Cliente": nome_cliente,
    "Responsável": responsavel,
    "Data": data_avaliacao.strftime("%d/%m/%Y"),
    "Hora": hora_avaliacao.strftime("%H:%M")
}

# ===============================
# ABRIR AVALIAÇÃO
# ===============================
if st.session_state.modo == "abrir":
    if not st.session_state.avaliacoes_por_data:
        st.info("ℹ️ Nenhuma avaliação salva.")
        st.stop()

    data_sel = st.selectbox(
        "Selecione a avaliação",
        sorted(st.session_state.avaliacoes_por_data.keys(), reverse=True)
    )

    if st.button("📂 Carregar Avaliação"):
        st.session_state.avaliacoes = {
            aba: pd.DataFrame(registros)
            for aba, registros in st.session_state.avaliacoes_por_data[data_sel].items()
        }
        st.success("Avaliação carregada.")

# ===============================
# UPLOAD EXCEL
# ===============================
uploaded_file = st.file_uploader("Upload do Excel", type=["xlsx"])

if not uploaded_file:
    st.stop()

xls = pd.ExcelFile(uploaded_file)

# ===============================
# CANVAS
# ===============================
st.subheader("Canvas do Projeto")

for aba in xls.sheet_names:
    df = xls.parse(aba)

    if aba not in st.session_state.avaliacoes:
        df["Resposta"] = "NA"
        df["Justificativa"] = ""
        st.session_state.avaliacoes[aba] = df
    else:
        df = st.session_state.avaliacoes[aba]

    nota = calcular_media(df)
    status = texto_semaforo(nota)

    with st.expander(f"{status} – {aba}", expanded=False):
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

# ===============================
# SALVAR / PDF
# ===============================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data_avaliacao} {hora_avaliacao.strftime('%H:%M')}"

    dados = {
        aba: df.to_dict(orient="records")
        for aba, df in st.session_state.avaliacoes.items()
    }

    st.session_state.avaliacoes_por_data[chave] = dados
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)

    st.success("Avaliação salva.")

if st.button("📄 Gerar PDF"):
    gerar_pdf(cabecalho, dados, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF", f, "avaliacao.pdf")
