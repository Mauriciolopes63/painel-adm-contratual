import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ===============================
# CONFIGURAÇÕES
# ===============================
st.set_page_config("Painel Administração Contratual", layout="wide")

ARQ_AVALIACOES = "avaliacoes.json"

VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0,
    "NA": None
}

# ===============================
# FUNÇÕES AUXILIARES
# ===============================
def salvar_avaliacoes(dados):
    with open(ARQ_AVALIACOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_avaliacoes():
    if os.path.exists(ARQ_AVALIACOES):
        with open(ARQ_AVALIACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def calcular_media_ponderada(df):
    df = df[df["Resposta"] != "NA"].copy()
    if df.empty:
        return None
    df["valor"] = df["Resposta"].map(VALORES)
    return (df["valor"] * df["Peso"]).sum() / df["Peso"].sum()

def semaforo(nota):
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

def cor_pdf(emoji):
    return {
        "🟢": colors.green,
        "🟡": colors.yellow,
        "🟠": colors.orange,
        "🔴": colors.red,
        "⚪": colors.grey
    }.get(emoji, colors.grey)

# ===============================
# PDF
# ===============================
def gerar_pdf(cab, dados, caminho):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(caminho, pagesize=A4)
    story = []

    # CAPA
    story.append(Paragraph("<b>AVALIAÇÃO DE ADMINISTRAÇÃO CONTRATUAL</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    for k, v in cab.items():
        story.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))

    story.append(PageBreak())

    # RESUMO COM SEMÁFOROS
    story.append(Paragraph("<b>Resumo Geral</b>", styles["Heading2"]))
    story.append(Spacer(1, 12))

    tabela = [["Item", "Status"]]
    estilos = []

    for aba, df in dados.items():
        nota = calcular_media_ponderada(df)
        s = semaforo(nota)
        linha = len(tabela)
        tabela.append([aba, ""])
        estilos.append(("BACKGROUND", (1, linha), (1, linha), cor_pdf(s)))

    t = Table(tabela, colWidths=[400, 40])
    t.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
    ] + estilos))

    story.append(t)
    story.append(PageBreak())

    # JUSTIFICATIVAS
    story.append(Paragraph("<b>Justificativas</b>", styles["Heading2"]))
    story.append(Spacer(1, 12))

    for aba, df in dados.items():
        for _, row in df.iterrows():
            if row["Resposta"] in ["Ruim", "Crítico"] and row["Justificativa"]:
                story.append(Paragraph(f"<b>{aba}</b> – {row['Pergunta']}", styles["Normal"]))
                story.append(Paragraph(row["Justificativa"], styles["Italic"]))
                story.append(Spacer(1, 10))

    doc.build(story)

# ===============================
# ESTADO
# ===============================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

if "modo" not in st.session_state:
    st.session_state.modo = None

# ===============================
# TOPO
# ===============================
st.title("Painel Administração Contratual")

col1, col2 = st.columns(2)
with col1:
    if st.button("🆕 Nova Avaliação"):
        st.session_state.modo = "nova"
        st.session_state.avaliacoes = {}

with col2:
    if st.button("📂 Abrir Avaliação Existente"):
        st.session_state.modo = "abrir"

if st.session_state.modo is None:
    st.stop()

# ===============================
# CABEÇALHO
# ===============================
st.markdown("### Cabeçalho")
nome_projeto = st.text_input("Nome do Projeto")
cliente = st.text_input("Cliente")
responsavel = st.text_input("Responsável")

data = st.date_input("Data", datetime.now().date())
hora = st.time_input("Hora", (datetime.utcnow() - timedelta(hours=3)).time())

# ===============================
# ABRIR AVALIAÇÃO
# ===============================
if st.session_state.modo == "abrir":
    if not st.session_state.avaliacoes_por_data:
        st.info("Nenhuma avaliação salva.")
        st.stop()

    chave = st.selectbox(
        "Selecione a avaliação",
        sorted(st.session_state.avaliacoes_por_data.keys(), reverse=True)
    )

    if st.button("Abrir"):
        st.session_state.avaliacoes = {
            aba: pd.DataFrame(reg)
            for aba, reg in st.session_state.avaliacoes_por_data[chave]["dados"].items()
        }
        st.success("Avaliação carregada.")

# ===============================
# EXCEL
# ===============================
uploaded = st.file_uploader("Upload do Excel", type=["xlsx"])
if not uploaded:
    st.stop()

xls = pd.ExcelFile(uploaded)

# ===============================
# CANVAS
# ===============================
st.subheader("Canvas")

for aba in xls.sheet_names:
    if aba not in st.session_state.avaliacoes:
        df = xls.parse(aba)
        df["Resposta"] = "NA"
        df["Justificativa"] = ""
        st.session_state.avaliacoes[aba] = df
    else:
        df = st.session_state.avaliacoes[aba]

    nota = calcular_media_ponderada(df)
    s = semaforo(nota)

    with st.expander(f"{s} {aba}", expanded=False):
        for i, row in df.iterrows():
            resp = st.selectbox(
                row["Pergunta"],
                ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                index=["Bom","Médio","Ruim","Crítico","NA"].index(row["Resposta"]),
                key=f"{aba}_{i}"
            )
            df.at[i, "Resposta"] = resp

            if resp in ["Ruim", "Crítico"]:
                just = st.text_input(
                    "Justificativa",
                    value=row["Justificativa"],
                    key=f"{aba}_{i}_j"
                )
                df.at[i, "Justificativa"] = just

# ===============================
# SALVAR + PDF
# ===============================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data} {hora.strftime('%H:%M')}"
    st.session_state.avaliacoes_por_data[chave] = {
        "cabecalho": {
            "Projeto": nome_projeto,
            "Cliente": cliente,
            "Responsável": responsavel,
            "Data": chave
        },
        "dados": {
            aba: df.to_dict(orient="records")
            for aba, df in st.session_state.avaliacoes.items()
        }
    }
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success("Avaliação salva.")

if st.button("📄 Gerar PDF"):
    cab = {
        "Projeto": nome_projeto,
        "Cliente": cliente,
        "Responsável": responsavel,
        "Data": f"{data} {hora.strftime('%H:%M')}"
    }
    gerar_pdf(cab, st.session_state.avaliacoes, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF", f, file_name="avaliacao.pdf")
