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

# =====================================================
# CONFIGURAÇÕES DE ARQUIVO
# =====================================================
AVALIACOES_FILE = "avaliacoes.json"
PDF_FILE = "avaliacao.pdf"

# =====================================================
# FUNÇÕES DE PERSISTÊNCIA
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
# FUNÇÕES DE NEGÓCIO
# =====================================================
VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0,
    "NA": None
}

def calcular_media(df):
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
    elif nota <= 0.5:
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
    elif nota <= 0.5:
        return "🟡"
    elif nota < 0.75:
        return "🟠"
    else:
        return "🔴"

# =====================================================
# PDF
# =====================================================
def gerar_pdf(cabecalho, avaliacoes, caminho):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(caminho, pagesize=A4)
    elementos = []

    # ---------- CAPA ----------
    elementos.append(Paragraph("<b>PAINEL DE ADMINISTRAÇÃO CONTRATUAL</b>", styles["Title"]))
    elementos.append(Spacer(1, 12))

    for k, v in cabecalho.items():
        elementos.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))

    elementos.append(Spacer(1, 20))

    tabela_resumo = [["Código", "Disciplina", "Status"]]

    for codigo, dados in avaliacoes.items():
        df = pd.DataFrame(dados)
        nota = calcular_media(df)
        tabela_resumo.append([
            codigo,
            df.iloc[0]["Descricao"],
            ""
        ])

    table = Table(tabela_resumo, colWidths=[60, 300, 60])
    style = TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("ALIGN", (-1,1), (-1,-1), "CENTER"),
    ])

    for i, (codigo, dados) in enumerate(avaliacoes.items(), start=1):
        df = pd.DataFrame(dados)
        nota = calcular_media(df)
        style.add("BACKGROUND", (-1,i), (-1,i), cor_semaforo(nota))

    table.setStyle(style)
    elementos.append(table)
    elementos.append(PageBreak())

    # ---------- DETALHAMENTO ----------
    for codigo, dados in avaliacoes.items():
        df = pd.DataFrame(dados)

        elementos.append(Paragraph(f"<b>{codigo} – {df.iloc[0]['Descricao']}</b>", styles["Heading2"]))
        elementos.append(Spacer(1, 10))

        for tipo in ["Procedimento", "Acompanhamento"]:
            df_tipo = df[df["Tipo"] == tipo]
            if df_tipo.empty:
                continue

            nota = calcular_media(df_tipo)
            elementos.append(Paragraph(f"<b>{tipo}</b>", styles["Heading3"]))

            t = Table(
                [["", ""]] ,
                colWidths=[20, 450]
            )
            t.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (0,0), cor_semaforo(nota)),
                ("GRID", (0,0), (-1,-1), 0.25, colors.black)
            ]))
            elementos.append(t)
            elementos.append(Spacer(1, 8))

            justificativas = df_tipo[
                (df_tipo["Resposta"].isin(["Ruim", "Crítico"])) &
                (df_tipo["Justificativa"] != "")
            ]

            for _, row in justificativas.iterrows():
                elementos.append(Paragraph(f"- {row['Justificativa']}", styles["Normal"]))

            elementos.append(Spacer(1, 12))

        elementos.append(PageBreak())

    doc.build(elementos)

# =====================================================
# STREAMLIT APP
# =====================================================
st.set_page_config("Painel Administração Contratual", layout="wide")
st.title("Painel Administração Contratual")

# ---------- ESTADO ----------
if "modo" not in st.session_state:
    st.session_state.modo = None

if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

# ---------- BOTÕES ----------
col1, col2 = st.columns(2)

with col1:
    if st.button("🆕 Nova Avaliação"):
        st.session_state.modo = "nova"
        st.session_state.avaliacoes = {}

with col2:
    if st.button("📂 Abrir Avaliação Existente"):
        st.session_state.modo = "abrir"

# ---------- CABEÇALHO ----------
st.markdown("### Dados do Empreendimento")
nome_projeto = st.text_input("Nome do Projeto")
cliente = st.text_input("Cliente")
responsavel = st.text_input("Responsável")

data_avaliacao = st.date_input("Data", datetime.now().date())
hora_avaliacao = st.time_input(
    "Hora",
    (datetime.utcnow() - timedelta(hours=3)).time()
)

# ---------- ABRIR ----------
if st.session_state.modo == "abrir":
    if not st.session_state.avaliacoes_por_data:
        st.info("Não existem avaliações salvas.")
        st.stop()

    chave = st.selectbox(
        "Selecione a avaliação",
        sorted(st.session_state.avaliacoes_por_data.keys(), reverse=True)
    )

    if st.button("Abrir"):
        dados = st.session_state.avaliacoes_por_data[chave]
        st.session_state.avaliacoes = {
            k: pd.DataFrame(v) for k, v in dados.items()
        }
        st.success("Avaliação carregada.")

# ---------- UPLOAD ----------
uploaded_file = st.file_uploader("Upload do Excel", type=["xlsx"])
if not uploaded_file:
    st.stop()

xls = pd.ExcelFile(uploaded_file)

# ---------- CANVAS ----------
st.subheader("Canvas da Avaliação")

for aba in xls.sheet_names:
    df = xls.parse(aba)

    if aba not in st.session_state.avaliacoes:
        df["Resposta"] = "NA"
        df["Justificativa"] = ""
        st.session_state.avaliacoes[aba] = df
    else:
        df = st.session_state.avaliacoes[aba]

    nota = calcular_media(df)
    semaforo = emoji_semaforo(nota)

    with st.expander(f"{semaforo} {df.iloc[0]['Codigo']} – {df.iloc[0]['Descricao']}"):
        for tipo in ["Procedimento", "Acompanhamento"]:
            df_tipo = df[df["Tipo"] == tipo]
            if df_tipo.empty:
                continue

            with st.expander(tipo):
                for i, row in df_tipo.iterrows():
                    resp = st.selectbox(
                        row["Pergunta"],
                        ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                        index=["Bom","Médio","Ruim","Crítico","NA"].index(row["Resposta"]),
                        key=f"{aba}_{i}"
                    )
                    df.at[i, "Resposta"] = resp

                    if resp in ["Ruim", "Crítico"]:
                        df.at[i, "Justificativa"] = st.text_input(
                            "Justificativa",
                            value=row["Justificativa"],
                            key=f"{aba}_{i}_j"
                        )

    st.session_state.avaliacoes[aba] = df

# ---------- SALVAR / PDF ----------
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
    cabecalho = {
        "Projeto": nome_projeto,
        "Cliente": cliente,
        "Responsável": responsavel,
        "Data": f"{data_avaliacao} {hora_avaliacao.strftime('%H:%M')}"
    }
    gerar_pdf(cabecalho, st.session_state.avaliacoes, PDF_FILE)
    with open(PDF_FILE, "rb") as f:
        st.download_button("⬇️ Baixar PDF", f, file_name="avaliacao.pdf")
