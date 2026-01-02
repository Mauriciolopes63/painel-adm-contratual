import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ===============================
# ARQUIVOS
# ===============================
AVALIACOES_FILE = "avaliacoes.json"
LOGO_M2L = "logo_m2l.png"

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
# SEMÁFORO
# ===============================
VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0,
    "NA": None
}

def calcular_media(df):
    df = df[df["Resposta"] != "NA"].copy()
    if df.empty:
        return None
    df["valor"] = df["Resposta"].map(VALORES)
    return (df["valor"] * df["Peso"]).sum() / df["Peso"].sum()

def cor_semaforo(nota):
    if nota is None:
        return "⚪"
    if nota <= 0.25:
        return "🟢"
    if nota <= 0.50:
        return "🟡"
    if nota < 0.75:
        return "🟠"
    return "🔴"

# ===============================
# PDF
# ===============================
def gerar_pdf(cabecalho, dados, logo_cliente_path):
    c = canvas.Canvas("avaliacao.pdf", pagesize=A4)
    width, height = A4

    # Logos
    if os.path.exists(LOGO_M2L):
        c.drawImage(LOGO_M2L, 40, height - 80, width=120, preserveAspectRatio=True)

    if logo_cliente_path:
        c.drawImage(logo_cliente_path, width - 160, height - 80, width=120, preserveAspectRatio=True)

    # Cabeçalho
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 50, cabecalho["projeto"])

    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 70, f"Cliente: {cabecalho['cliente']}")
    c.drawCentredString(width / 2, height - 85, f"Data da Avaliação: {cabecalho['data']}")

    y = height - 120

    # Canvas
    for disciplina, info in dados.items():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, f"{info['semaforo']} {disciplina}")
        y -= 18

    c.showPage()

    # Página de justificativas
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 40, "Justificativas")

    y = height - 70
    c.setFont("Helvetica", 10)

    for disciplina, info in dados.items():
        for j in info["justificativas"]:
            c.drawString(40, y, f"{disciplina}: {j}")
            y -= 15
            if y < 50:
                c.showPage()
                y = height - 50

    c.save()

# ===============================
# APP
# ===============================
st.set_page_config("Painel Administração Contratual", layout="wide")
st.title("Painel Administração Contratual")

# Cabeçalho
st.subheader("Dados do Relatório")

projeto = st.text_input("Nome do Projeto")
cliente = st.text_input("Cliente")
logo_cliente = st.file_uploader("Logo do Cliente (opcional)", type=["png", "jpg"])

data = st.date_input("Data", datetime.now().date())
hora = st.time_input("Hora", (datetime.utcnow() - timedelta(hours=3)).time())

# Upload Excel
uploaded = st.file_uploader("Excel do Questionário", type=["xlsx"])
if not uploaded:
    st.stop()

xls = pd.ExcelFile(uploaded)

resultados = {}
justificativas = {}

st.subheader("Canvas")

for aba in xls.sheet_names:
    df = xls.parse(aba)

    if "Resposta" not in df.columns:
        df["Resposta"] = "NA"
    if "Justificativa" not in df.columns:
        df["Justificativa"] = ""

    codigo = df.iloc[0]["Codigo"] if "Codigo" in df.columns else aba
    descricao = df.iloc[0]["Descricao"] if "Descricao" in df.columns else ""

    nota = calcular_media(df)
    semaforo = cor_semaforo(nota)

    with st.expander(f"{semaforo} {codigo} – {descricao}"):
        for i, row in df.iterrows():
            resp = st.selectbox(
                row["Pergunta"],
                ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                index=["Bom", "Médio", "Ruim", "Crítico", "NA"].index(row["Resposta"]),
                key=f"{aba}_{i}"
            )
            df.at[i, "Resposta"] = resp

            if resp in ["Ruim", "Crítico"]:
                df.at[i, "Justificativa"] = st.text_input(
                    "Justificativa",
                    value=row["Justificativa"],
                    key=f"{aba}_{i}_j"
                )

    resultados[codigo] = {
        "semaforo": semaforo,
        "justificativas": df[df["Justificativa"] != ""]["Justificativa"].tolist()
    }

# PDF
st.divider()

if st.button("📄 Gerar PDF"):
    logo_path = None
    if logo_cliente:
        logo_path = "logo_cliente.png"
        with open(logo_path, "wb") as f:
            f.write(logo_cliente.read())

    gerar_pdf(
        {
            "projeto": projeto,
            "cliente": cliente,
            "data": f"{data.strftime('%d/%m/%Y')} {hora.strftime('%H:%M')}"
        },
        resultados,
        logo_path
    )

    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Baixar PDF", f, file_name="avaliacao.pdf")
