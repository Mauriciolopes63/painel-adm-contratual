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

# =========================================================
# CONFIGURAÇÕES
# =========================================================
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

# =========================================================
# PERSISTÊNCIA
# =========================================================
def salvar_avaliacoes(dados):
    with open(AVALIACOES_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_avaliacoes():
    if os.path.exists(AVALIACOES_FILE):
        with open(AVALIACOES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# =========================================================
# FUNÇÕES DE NEGÓCIO
# =========================================================
def calcular_nota(df):
    df_validas = df[df["Resposta"] != "NA"].copy()
    if df_validas.empty:
        return None

    df_validas["valor"] = df_validas["Resposta"].map(VALORES)
    soma = (df_validas["valor"] * df_validas["Peso"]).sum()
    peso = df_validas["Peso"].sum()

    return soma / peso if peso > 0 else None

def cor_semaforo(nota):
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

# =========================================================
# PDF
# =========================================================
def gerar_pdf(cabecalho, avaliacoes, caminho):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(caminho, pagesize=A4)
    elementos = []

    elementos.append(Paragraph("<b>RELATÓRIO DE AVALIAÇÃO CONTRATUAL</b>", styles["Title"]))
    elementos.append(Spacer(1, 12))

    for k, v in cabecalho.items():
        elementos.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))

    elementos.append(PageBreak())

    # =======================
    # RESUMO
    # =======================
    elementos.append(Paragraph("<b>Resumo Geral</b>", styles["Heading1"]))
    elementos.append(Spacer(1, 12))

    tabela_resumo = [["Disciplina", "Status"]]

    for aba, dados in avaliacoes.items():
        df = pd.DataFrame(dados)
        codigo = df.iloc[0]["Codigo"]
        descricao = df.iloc[0]["Descricao"]
        nota = calcular_nota(df)
        cor = cor_semaforo(nota)

        tabela_resumo.append(
            [f"{codigo} – {descricao}", ""]
        )

    table = Table(tabela_resumo, colWidths=[400, 50])
    estilo = TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (1,1), (1,-1), cor)
    ])
    table.setStyle(estilo)

    elementos.append(table)
    elementos.append(PageBreak())

    # =======================
    # JUSTIFICATIVAS
    # =======================
    elementos.append(Paragraph("<b>Justificativas</b>", styles["Heading1"]))
    elementos.append(Spacer(1, 12))

    for aba, dados in avaliacoes.items():
        df = pd.DataFrame(dados)
        codigo = df.iloc[0]["Codigo"]
        descricao = df.iloc[0]["Descricao"]
        nota = calcular_nota(df)
        cor = cor_semaforo(nota)

        header = Table(
            [[f"{codigo} – {descricao}"]],
            colWidths=[500],
            style=[
                ("BACKGROUND", (0,0), (-1,-1), cor),
                ("TEXTCOLOR", (0,0), (-1,-1), colors.black),
                ("BOX", (0,0), (-1,-1), 1, colors.black),
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
                texto = f"- {row['Justificativa']}"
                elementos.append(Paragraph(texto, styles["Normal"]))

            elementos.append(Spacer(1, 8))

        elementos.append(Spacer(1, 20))

    doc.build(elementos)

# =========================================================
# APP
# =========================================================
st.title("Painel Administração Contratual")

if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

col1, col2 = st.columns(2)

with col1:
    if st.button("🆕 Nova Avaliação"):
        st.session_state.avaliacoes = {}

with col2:
    if st.button("📂 Abrir Avaliação Existente"):
        datas = list(st.session_state.avaliacoes_por_data.keys())
        if datas:
            data_sel = st.selectbox("Selecione", datas)
            st.session_state.avaliacoes = {
                aba: pd.DataFrame(dados)
                for aba, dados in st.session_state.avaliacoes_por_data[data_sel].items()
            }

st.markdown("### Informações da Avaliação")
data = st.date_input("Data", datetime.now().date())
hora = st.time_input("Hora", (datetime.utcnow() - timedelta(hours=3)).time())

uploaded_file = st.file_uploader("Carregar Excel", type=["xlsx"])
if not uploaded_file:
    st.stop()

xls = pd.ExcelFile(uploaded_file)

for aba in xls.sheet_names:
    base = xls.parse(aba)

    if aba not in st.session_state.avaliacoes:
        base["Resposta"] = "NA"
        base["Justificativa"] = ""
        st.session_state.avaliacoes[aba] = base

    df = st.session_state.avaliacoes[aba]

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
                        just = st.text_input(
                            "Justificativa",
                            value=row["Justificativa"],
                            key=f"{aba}_{i}_j"
                        )
                        df.at[i, "Justificativa"] = just

        st.session_state.avaliacoes[aba] = df

st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data} {hora.strftime('%H:%M')}"
    st.session_state.avaliacoes_por_data[chave] = {
        aba: df.to_dict(orient="records")
        for aba, df in st.session_state.avaliacoes.items()
    }
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success("Avaliação salva com sucesso")

if st.button("📄 Gerar PDF"):
    cab = {
        "Data": str(data),
        "Hora": hora.strftime("%H:%M")
    }
    gerar_pdf(cab, st.session_state.avaliacoes, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF", f, "avaliacao.pdf")
