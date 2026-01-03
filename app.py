import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# =========================================================
# CONFIG
# =========================================================
st.set_page_config("Painel Administração Contratual", layout="wide")
AVALIACOES_FILE = "avaliacoes.json"

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
# SEMÁFORO (CÁLCULO)
# =========================================================
VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0,
    "NA": None
}

def calcular_nota(df):
    dfv = df[df["Resposta"] != "NA"].copy()
    if dfv.empty:
        return None
    dfv["valor"] = dfv["Resposta"].map(VALORES)
    return (dfv["valor"] * dfv["Peso"]).sum() / dfv["Peso"].sum()

def cor_pdf(nota):
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

def cor_app(nota):
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

# =========================================================
# PDF
# =========================================================
def gerar_pdf(cabecalho, avaliacoes, caminho):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(caminho, pagesize=A4)
    elementos = []

    # -------- Capa / Cabeçalho
    elementos.append(Paragraph("<b>RELATÓRIO DE AVALIAÇÃO CONTRATUAL</b>", styles["Title"]))
    elementos.append(Spacer(1, 12))

    for k, v in cabecalho.items():
        elementos.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))

    elementos.append(Spacer(1, 20))

    # -------- Resumo dos semáforos
    elementos.append(Paragraph("<b>Resumo por Disciplina</b>", styles["Heading2"]))
    elementos.append(Spacer(1, 10))

    tabela_resumo = []
    estilos = []

    for idx, (disc, dados) in enumerate(avaliacoes.items()):
        df = pd.DataFrame(dados)
        codigo = df.iloc[0]["Codigo"]
        descricao = df.iloc[0]["Descricao"]
        nota = calcular_nota(df)

        tabela_resumo.append(["", f"{codigo} – {descricao}"])
        estilos.append((
            "BACKGROUND", (0, idx), (0, idx), cor_pdf(nota)
        ))

    t = Table(tabela_resumo, colWidths=[15, 450])
    t.setStyle(TableStyle(
        estilos + [
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]
    ))
    elementos.append(t)

    elementos.append(Spacer(1, 30))

    # -------- Justificativas (sequenciais)
    elementos.append(Paragraph("<b>Justificativas</b>", styles["Heading2"]))
    elementos.append(Spacer(1, 10))

    for disc, dados in avaliacoes.items():
        df = pd.DataFrame(dados)
        just = df[
            (df["Resposta"].isin(["Ruim", "Crítico"])) &
            (df["Justificativa"].str.strip() != "")
        ]
        if just.empty:
            continue

        codigo = df.iloc[0]["Codigo"]
        descricao = df.iloc[0]["Descricao"]
        nota = calcular_nota(df)

        tabela_disc = [
            ["", f"{codigo} – {descricao}"]
        ]
        tdisc = Table(tabela_disc, colWidths=[15, 450])
        tdisc.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (0,0), cor_pdf(nota)),
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        elementos.append(tdisc)
        elementos.append(Spacer(1, 8))

        for _, r in just.iterrows():
            elementos.append(
                Paragraph(f"<b>{r['Tipo']}:</b> {r['Justificativa']}", styles["Normal"])
            )
            elementos.append(Spacer(1, 6))

        elementos.append(Spacer(1, 15))

    doc.build(elementos)

# =========================================================
# ESTADO
# =========================================================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

# =========================================================
# INTERFACE – CABEÇALHO
# =========================================================
st.title("Painel Administração Contratual")

st.markdown("### Dados da Avaliação")
c1, c2, c3 = st.columns(3)

with c1:
    projeto = st.text_input("Projeto")
with c2:
    cliente = st.text_input("Cliente")
with c3:
    responsavel = st.text_input("Responsável")

data_av = st.date_input("Data da Avaliação", datetime.now().date())
hora_av = st.time_input(
    "Hora da Avaliação",
    (datetime.utcnow() - timedelta(hours=3)).time()
)

# =========================================================
# AÇÕES
# =========================================================
a1, a2 = st.columns(2)

with a1:
    if st.button("🆕 Nova Avaliação", use_container_width=True):
        st.session_state.avaliacoes = {}

with a2:
    if st.button("📂 Abrir Avaliação Existente", use_container_width=True):
        if not st.session_state.avaliacoes_por_data:
            st.info("Ainda não existem avaliações salvas.")
        else:
            chave = st.selectbox(
                "Selecione a avaliação",
                sorted(st.session_state.avaliacoes_por_data.keys(), reverse=True)
            )
            dados = st.session_state.avaliacoes_por_data[chave]
            st.session_state.avaliacoes = {
                k: pd.DataFrame(v) for k, v in dados.items()
            }
            st.success(f"Avaliação {chave} carregada.")

# =========================================================
# UPLOAD EXCEL (OBRIGATÓRIO)
# =========================================================
uploaded_file = st.file_uploader("Upload do Excel do Projeto", type=["xlsx"])
if not uploaded_file:
    st.stop()

xls = pd.ExcelFile(uploaded_file)

# =========================================================
# CANVAS
# =========================================================
st.subheader("Canvas da Avaliação")

for aba in xls.sheet_names:
    base = xls.parse(aba)

    if aba not in st.session_state.avaliacoes:
        base["Resposta"] = "NA"
        base["Justificativa"] = ""
        st.session_state.avaliacoes[aba] = base
    else:
        base = st.session_state.avaliacoes[aba]

    codigo = base.iloc[0]["Codigo"]
    descricao = base.iloc[0]["Descricao"]

    nota = calcular_nota(base)
    cor = cor_app(nota)

    with st.expander(f"{cor} {codigo} – {descricao}", expanded=False):

        for tipo in base["Tipo"].unique():
            st.markdown(f"**{tipo}**")
            bloco = base[base["Tipo"] == tipo]

            for i, row in bloco.iterrows():
                resp = st.selectbox(
                    row["Pergunta"],
                    ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                    index=["Bom","Médio","Ruim","Crítico","NA"].index(row["Resposta"]),
                    key=f"{aba}_{i}"
                )
                base.at[i, "Resposta"] = resp

                if resp in ["Ruim", "Crítico"]:
                    just = st.text_input(
                        "Justificativa",
                        value=row["Justificativa"],
                        key=f"{aba}_{i}_j"
                    )
                    base.at[i, "Justificativa"] = just

        st.session_state.avaliacoes[aba] = base

# =========================================================
# SALVAR / PDF
# =========================================================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data_av.strftime('%Y-%m-%d')} {hora_av.strftime('%H:%M')}"
    st.session_state.avaliacoes_por_data[chave] = {
        aba: df.to_dict(orient="records")
        for aba, df in st.session_state.avaliacoes.items()
    }
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success(f"Avaliação salva em {chave}")

if st.button("📄 Gerar PDF"):
    cab = {
        "Projeto": projeto,
        "Cliente": cliente,
        "Responsável": responsavel,
        "Data": f"{data_av} {hora_av.strftime('%H:%M')}"
    }
    gerar_pdf(cab, st.session_state.avaliacoes, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF", f, file_name="avaliacao.pdf")
