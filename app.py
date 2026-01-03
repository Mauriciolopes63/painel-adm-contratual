import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

# =====================================================
# CONFIG
# =====================================================
st.set_page_config("Painel Administração Contratual", layout="wide")

AVALIACOES_FILE = "avaliacoes.json"
OPCOES = ["Bom", "Médio", "Ruim", "Crítico", "NA"]

VALORES = {
    "Bom": 0.0,
    "Médio": 0.33,
    "Ruim": 0.66,
    "Crítico": 1.0,
    "NA": None
}

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
def calcular_nota(df):
    df_validas = df[df["Resposta"] != "NA"].copy()
    if df_validas.empty:
        return None

    df_validas["valor"] = df_validas["Resposta"].map(VALORES)
    soma = (df_validas["valor"] * df_validas["Peso"]).sum()
    peso = df_validas["Peso"].sum()

    return soma / peso if peso > 0 else None

def cor_semaforo_pdf(nota):
    if nota is None:
        return colors.lightgrey
    if nota <= 0.25:
        return colors.green
    elif nota <= 0.50:
        return colors.yellow
    elif nota < 0.75:
        return colors.orange
    else:
        return colors.red

# =====================================================
# PDF
# =====================================================
def gerar_pdf(avaliacao, caminho):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(caminho, pagesize=A4)
    elementos = []

    cab = avaliacao["cabecalho"]
    dados = avaliacao["dados"]

    # ---------- CAPA ----------
    elementos.append(Paragraph("<b>RELATÓRIO DE AVALIAÇÃO CONTRATUAL</b>", styles["Title"]))
    elementos.append(Spacer(1, 16))

    for k, v in cab.items():
        elementos.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))

    elementos.append(PageBreak())

    # ---------- RESUMO ----------
    elementos.append(Paragraph("<b>Resumo Geral</b>", styles["Heading1"]))
    elementos.append(Spacer(1, 12))

    tabela = [["Disciplina", "Status"]]
    estilos = [
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("ALIGN", (1,1), (1,-1), "CENTER")
    ]

    linha = 1
    for aba, registros in dados.items():
        df = pd.DataFrame(registros)
        codigo = df.iloc[0]["Codigo"]
        descricao = df.iloc[0]["Descricao"]
        nota = calcular_nota(df)
        cor = cor_semaforo_pdf(nota)

        tabela.append([f"{codigo} – {descricao}", ""])
        estilos.append(("BACKGROUND", (1, linha), (1, linha), cor))
        linha += 1

    table = Table(tabela, colWidths=[430, 60])
    table.setStyle(TableStyle(estilos))
    elementos.append(table)

    elementos.append(PageBreak())

    # ---------- JUSTIFICATIVAS ----------
    elementos.append(Paragraph("<b>Justificativas</b>", styles["Heading1"]))
    elementos.append(Spacer(1, 12))

    for aba, registros in dados.items():
        df = pd.DataFrame(registros)
        codigo = df.iloc[0]["Codigo"]
        descricao = df.iloc[0]["Descricao"]
        nota = calcular_nota(df)
        cor = cor_semaforo_pdf(nota)

        header = Table(
            [[f"{codigo} – {descricao}"]],
            colWidths=[500],
            style=[
                ("BACKGROUND", (0,0), (-1,-1), cor),
                ("BOX", (0,0), (-1,-1), 1, colors.black)
            ]
        )
        elementos.append(header)
        elementos.append(Spacer(1, 10))

        for tipo in ["Procedimento", "Acompanhamento"]:
            subset = df[(df["Tipo"] == tipo) & (df["Resposta"].isin(["Ruim", "Crítico"]))]
            if subset.empty:
                continue

            elementos.append(Paragraph(f"<b>{tipo}</b>", styles["Heading3"]))
            for _, row in subset.iterrows():
                elementos.append(Paragraph(f"- {row['Justificativa']}", styles["Normal"]))
            elementos.append(Spacer(1, 8))

        elementos.append(Spacer(1, 20))

    doc.build(elementos)

# =====================================================
# APP
# =====================================================
st.title("Painel Administração Contratual")

if "avaliacoes_salvas" not in st.session_state:
    st.session_state.avaliacoes_salvas = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {"cabecalho": {}, "dados": {}}

# ---------- BOTÕES ----------
col1, col2 = st.columns(2)

with col1:
    if st.button("🆕 Nova Avaliação"):
        st.session_state.avaliacao_atual = {"cabecalho": {}, "dados": {}}

with col2:
    if st.button("📂 Abrir Avaliação Existente"):
        if st.session_state.avaliacoes_salvas:
            chave = st.selectbox(
                "Selecione a avaliação",
                list(st.session_state.avaliacoes_salvas.keys())
            )
            st.session_state.avaliacao_atual = json.loads(
                json.dumps(st.session_state.avaliacoes_salvas[chave])
            )

# ---------- CABEÇALHO ----------
st.markdown("### Cabeçalho da Avaliação")

cab = st.session_state.avaliacao_atual["cabecalho"]

cab["Projeto"] = st.text_input("Nome do Projeto", cab.get("Projeto", ""))
cab["Cliente"] = st.text_input("Cliente", cab.get("Cliente", ""))
cab["Responsável"] = st.text_input("Responsável", cab.get("Responsável", ""))
cab["Data"] = str(st.date_input("Data", datetime.now().date()))
cab["Hora"] = st.time_input(
    "Hora",
    datetime.strptime(cab.get("Hora", "09:00"), "%H:%M").time()
).strftime("%H:%M")

# ---------- EXCEL ----------
uploaded_file = st.file_uploader("Upload do Excel", type=["xlsx"])
if not uploaded_file:
    st.stop()

xls = pd.ExcelFile(uploaded_file)

for aba in xls.sheet_names:
    if aba not in st.session_state.avaliacao_atual["dados"]:
        df = xls.parse(aba)
        df["Resposta"] = "NA"
        df["Justificativa"] = ""
        st.session_state.avaliacao_atual["dados"][aba] = df.to_dict(orient="records")

    df = pd.DataFrame(st.session_state.avaliacao_atual["dados"][aba])

    with st.expander(aba):
        for tipo in ["Procedimento", "Acompanhamento"]:
            with st.expander(tipo):
                for i, row in df[df["Tipo"] == tipo].iterrows():
                    resp = st.selectbox(
                        row["Pergunta"],
                        OPCOES,
                        index=OPCOES.index(row["Resposta"]),
                        key=f"{aba}_{i}"
                    )
                    df.at[i, "Resposta"] = resp

                    if resp in ["Ruim", "Crítico"]:
                        df.at[i, "Justificativa"] = st.text_input(
                            "Justificativa",
                            row["Justificativa"],
                            key=f"{aba}_{i}_j"
                        )

    st.session_state.avaliacao_atual["dados"][aba] = df.to_dict(orient="records")

# ---------- SALVAR ----------
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{cab['Data']} {cab['Hora']}"
    st.session_state.avaliacoes_salvas[chave] = json.loads(
        json.dumps(st.session_state.avaliacao_atual)
    )
    salvar_avaliacoes(st.session_state.avaliacoes_salvas)
    st.success("Avaliação salva corretamente")

if st.button("📄 Gerar PDF"):
    gerar_pdf(st.session_state.avaliacao_atual, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF", f, "avaliacao.pdf")
