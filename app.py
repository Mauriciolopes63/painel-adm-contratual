import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# =====================================================
# CONFIGURAÇÕES
# =====================================================
st.set_page_config(page_title="Painel Administração Contratual", layout="wide")
AVALIACOES_FILE = "avaliacoes.json"

# =====================================================
# PERSISTÊNCIA
# =====================================================
def salvar_avaliacoes(dados):
    with open(AVALIACOES_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_avaliacoes():
    if os.path.exists(AVALIACOES_FILE):
        with open(AVALIACOES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# =====================================================
# REGRAS DE NEGÓCIO
# =====================================================
VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0,
    "NA": None
}

def calcular_media_ponderada(df):
    df = df[df["Resposta"] != "NA"].copy()
    if df.empty:
        return None
    df["valor"] = df["Resposta"].map(VALORES)
    soma = (df["valor"] * df["Peso"]).sum()
    peso_total = df["Peso"].sum()
    return soma / peso_total if peso_total else None

def semaforo_tela(nota):
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

# =====================================================
# PDF – SEMÁFORO COM COR REAL
# =====================================================
def desenhar_semaforo_pdf(c, x, y, nota):
    if nota is None:
        cor = colors.lightgrey
        texto = "N/A"
    elif nota <= 0.25:
        cor = colors.green
        texto = "VERDE"
    elif nota <= 0.50:
        cor = colors.yellow
        texto = "AMARELO"
    elif nota < 0.75:
        cor = colors.orange
        texto = "LARANJA"
    else:
        cor = colors.red
        texto = "VERMELHO"

    c.setFillColor(cor)
    c.circle(x, y, 6, fill=1)
    c.setFillColor(colors.black)
    c.drawString(x + 12, y - 4, texto)

def gerar_pdf(cabecalho, avaliacoes, caminho):
    c = canvas.Canvas(caminho, pagesize=A4)
    largura, altura = A4

    # ==========================
    # PÁGINA 1 – RESUMO EXECUTIVO
    # ==========================
    y = altura - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "RELATÓRIO – PAINEL ADMINISTRAÇÃO CONTRATUAL")

    y -= 30
    c.setFont("Helvetica", 10)
    for k, v in cabecalho.items():
        c.drawString(40, y, f"{k}: {v}")
        y -= 14

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Resumo Executivo – Canvas")
    y -= 25

    for aba, registros in avaliacoes.items():
        df = pd.DataFrame(registros)
        nota = calcular_media_ponderada(df)

        desenhar_semaforo_pdf(c, 40, y, nota)
        c.drawString(90, y - 4, aba)

        y -= 22
        if y < 80:
            c.showPage()
            y = altura - 40

    # ==========================
    # PÁGINA 2 – JUSTIFICATIVAS
    # ==========================
    c.showPage()
    y = altura - 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Relatório de Pontos Críticos e Justificativas")
    y -= 25
    c.setFont("Helvetica", 10)

    encontrou = False

    for aba, registros in avaliacoes.items():
        df = pd.DataFrame(registros)
        criticos = df[df["Resposta"].isin(["Ruim", "Crítico"])]

        if criticos.empty:
            continue

        encontrou = True
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, f"Disciplina: {aba}")
        y -= 18
        c.setFont("Helvetica", 10)

        for _, row in criticos.iterrows():
            c.drawString(50, y, f"- {row['Pergunta']} ({row['Resposta']})")
            y -= 14
            c.drawString(60, y, f"Justificativa: {row.get('Justificativa','')}")
            y -= 16

            if y < 80:
                c.showPage()
                y = altura - 40

        y -= 10

    if not encontrou:
        c.drawString(40, y, "Não foram registrados pontos Ruim ou Crítico.")

    c.save()

# =====================================================
# ESTADO
# =====================================================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

# =====================================================
# INTERFACE
# =====================================================
st.title("Painel Administração Contratual")

# -------- Cabeçalho
st.subheader("Dados do Empreendimento")
col1, col2, col3 = st.columns(3)

with col1:
    projeto = st.text_input("Projeto")
with col2:
    cliente = st.text_input("Cliente")
with col3:
    responsavel = st.text_input("Responsável")

data_avaliacao = st.date_input("Data da Avaliação", datetime.now().date())
hora_avaliacao = st.time_input(
    "Hora",
    (datetime.utcnow() - timedelta(hours=3)).time()
)

# -------- Abrir Avaliação Existente
st.subheader("Avaliações Salvas")
datas = list(st.session_state.avaliacoes_por_data.keys())

if datas:
    data_sel = st.selectbox("Selecione uma avaliação", datas)
    if st.button("📂 Abrir Avaliação Existente"):
        st.session_state.avaliacoes = {
            aba: pd.DataFrame(reg)
            for aba, reg in st.session_state.avaliacoes_por_data[data_sel].items()
        }
        st.success("Avaliação carregada.")

# -------- Upload Excel
uploaded_file = st.file_uploader("Carregar Excel do Projeto", type=["xlsx"])
if not uploaded_file:
    st.stop()

xls = pd.ExcelFile(uploaded_file)

# -------- Canvas
st.subheader("Canvas do Projeto")

for aba in xls.sheet_names:
    base = xls.parse(aba)

    if aba not in st.session_state.avaliacoes:
        base["Resposta"] = "NA"
        base["Justificativa"] = ""
        st.session_state.avaliacoes[aba] = base
    else:
        base = st.session_state.avaliacoes[aba]

    nota = calcular_media_ponderada(base)

    with st.expander(f"{semaforo_tela(nota)} {aba}", expanded=False):
        for i, row in base.iterrows():
            st.markdown(f"**{row['Pergunta']}**")

            resposta = st.selectbox(
                "Avaliação",
                ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                index=["Bom","Médio","Ruim","Crítico","NA"].index(row["Resposta"]),
                key=f"{aba}_{i}"
            )

            justificativa = row["Justificativa"]
            if resposta in ["Ruim", "Crítico"]:
                justificativa = st.text_input(
                    "Justificativa",
                    value=justificativa,
                    key=f"{aba}_{i}_j"
                )

            base.at[i, "Resposta"] = resposta
            base.at[i, "Justificativa"] = justificativa

        st.session_state.avaliacoes[aba] = base

# -------- Ações
st.divider()
colA, colB = st.columns(2)

with colA:
    if st.button("💾 Salvar Avaliação"):
        chave = f"{data_avaliacao} {hora_avaliacao.strftime('%H:%M')}"
        st.session_state.avaliacoes_por_data[chave] = {
            aba: df.to_dict("records")
            for aba, df in st.session_state.avaliacoes.items()
        }
        salvar_avaliacoes(st.session_state.avaliacoes_por_data)
        st.success("Avaliação salva com sucesso.")

with colB:
    if st.button("📄 Gerar PDF"):
        cabecalho = {
            "Projeto": projeto,
            "Cliente": cliente,
            "Responsável": responsavel,
            "Data": f"{data_avaliacao} {hora_avaliacao.strftime('%H:%M')}"
        }
        gerar_pdf(cabecalho, st.session_state.avaliacoes, "avaliacao.pdf")
        with open("avaliacao.pdf", "rb") as f:
            st.download_button("⬇️ Download PDF", f, file_name="avaliacao.pdf")
