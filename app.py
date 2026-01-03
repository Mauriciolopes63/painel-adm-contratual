import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from io import BytesIO

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# ===============================
# CONFIGURAÇÕES
# ===============================
st.set_page_config("Painel Administração Contratual", layout="wide")

ARQUIVO_AVALIACOES = "avaliacoes.json"

# ===============================
# PERSISTÊNCIA
# ===============================
def salvar_avaliacoes(dados):
    with open(ARQUIVO_AVALIACOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_avaliacoes():
    if os.path.exists(ARQUIVO_AVALIACOES):
        with open(ARQUIVO_AVALIACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ===============================
# FUNÇÕES DE NEGÓCIO
# ===============================
VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0
}

def calcular_media(df):
    validas = df[df["Resposta"].isin(VALORES.keys())].copy()
    if validas.empty:
        return None
    validas["valor"] = validas["Resposta"].map(VALORES)
    return (validas["valor"] * validas["Peso"]).sum() / validas["Peso"].sum()

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

# ===============================
# PDF
# ===============================
def gerar_pdf(cabecalho, avaliacoes):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Capa
    story.append(Paragraph("<b>Relatório de Avaliação Contratual</b>", styles["Title"]))
    story.append(Spacer(1, 12))
    for k, v in cabecalho.items():
        story.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))
    story.append(Spacer(1, 20))

    # Resumo
    story.append(Paragraph("<b>Resumo por Disciplina</b>", styles["Heading2"]))
    tabela = [["Disciplina", "Status"]]

    for disciplina, df in avaliacoes.items():
        nota = calcular_media(df)
        tabela.append([disciplina, semaforo(nota)])

    story.append(Table(tabela, colWidths=[300, 100]))
    story.append(Spacer(1, 20))

    # Justificativas
    story.append(Paragraph("<b>Justificativas</b>", styles["Heading2"]))
    story.append(Spacer(1, 10))

    for disciplina, df in avaliacoes.items():
        for _, row in df.iterrows():
            if row["Resposta"] in ["Ruim", "Crítico"] and row.get("Justificativa"):
                story.append(
                    Paragraph(
                        f"<b>{disciplina}</b> {semaforo(calcular_media(df))} – "
                        f"{row['Resposta']}: {row['Justificativa']}",
                        styles["Normal"]
                    )
                )
                story.append(Spacer(1, 6))

    doc.build(story)
    buffer.seek(0)
    return buffer

# ===============================
# ESTADO
# ===============================
if "avaliacoes_salvas" not in st.session_state:
    st.session_state.avaliacoes_salvas = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {}

if "modo" not in st.session_state:
    st.session_state.modo = None

# ===============================
# INTERFACE
# ===============================
st.title("Painel Administração Contratual")

col1, col2 = st.columns(2)
with col1:
    if st.button("🆕 Nova Avaliação"):
        st.session_state.modo = "nova"
        st.session_state.avaliacao_atual = {}

with col2:
    if st.button("📂 Abrir Avaliação Existente"):
        st.session_state.modo = "abrir"

st.divider()

# ===============================
# ABRIR AVALIAÇÃO EXISTENTE
# ===============================
if st.session_state.modo == "abrir":

    if not st.session_state.avaliacoes_salvas:
        st.info("Nenhuma avaliação salva.")
        st.stop()

    data_escolhida = st.selectbox(
        "Selecione a avaliação",
        sorted(st.session_state.avaliacoes_salvas.keys(), reverse=True)
    )

    if st.button("Abrir"):
        dados = st.session_state.avaliacoes_salvas[data_escolhida]
        st.session_state.avaliacao_atual = {
            aba: pd.DataFrame(registros)
            for aba, registros in dados.items()
        }
        st.success(f"Avaliação {data_escolhida} carregada.")

# ===============================
# CABEÇALHO
# ===============================
st.markdown("### Dados do Projeto")
nome_projeto = st.text_input("Nome do Projeto")
cliente = st.text_input("Cliente")
responsavel = st.text_input("Responsável")

data_avaliacao = st.date_input("Data", datetime.now().date())
hora_avaliacao = st.time_input(
    "Hora",
    (datetime.utcnow() - timedelta(hours=3)).time()
)

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
st.subheader("Canvas de Avaliação")

for aba in xls.sheet_names:
    base = xls.parse(aba)

    if aba not in st.session_state.avaliacao_atual:
        base["Resposta"] = "Bom"
        base["Justificativa"] = ""
        st.session_state.avaliacao_atual[aba] = base
    else:
        base = st.session_state.avaliacao_atual[aba]

    nota = calcular_media(base)
    status = semaforo(nota)

    with st.expander(f"{status} {aba}", expanded=False):

        for i, row in base.iterrows():
            st.markdown(f"**{row['Pergunta']}**")

            resposta = st.selectbox(
                "Resposta",
                ["Bom", "Médio", "Ruim", "Crítico"],
                index=["Bom", "Médio", "Ruim", "Crítico"].index(row["Resposta"]),
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

        st.session_state.avaliacao_atual[aba] = base

# ===============================
# SALVAR
# ===============================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data_avaliacao.strftime('%Y-%m-%d')} {hora_avaliacao.strftime('%H:%M')}"
    st.session_state.avaliacoes_salvas[chave] = {
        aba: df.to_dict(orient="records")
        for aba, df in st.session_state.avaliacao_atual.items()
    }
    salvar_avaliacoes(st.session_state.avaliacoes_salvas)
    st.success("Avaliação salva com sucesso.")

# ===============================
# PDF
# ===============================
if st.session_state.avaliacao_atual:
    if st.button("📄 Gerar PDF"):
        cabecalho = {
            "Projeto": nome_projeto,
            "Cliente": cliente,
            "Responsável": responsavel,
            "Data": f"{data_avaliacao} {hora_avaliacao.strftime('%H:%M')}"
        }

        pdf = gerar_pdf(cabecalho, st.session_state.avaliacao_atual)

        st.download_button(
            "⬇️ Download do PDF",
            data=pdf,
            file_name="avaliacao_contratual.pdf",
            mime="application/pdf"
        )
