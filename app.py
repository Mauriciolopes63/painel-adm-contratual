import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# ======================================================
# CONFIG
# ======================================================
st.set_page_config("Painel Administração Contratual", layout="wide")
ARQ_AVALIACOES = "avaliacoes.json"

# ======================================================
# PERSISTÊNCIA
# ======================================================
def salvar_avaliacoes(dados):
    with open(ARQ_AVALIACOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_avaliacoes():
    if os.path.exists(ARQ_AVALIACOES):
        with open(ARQ_AVALIACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ======================================================
# SEMÁFORO
# ======================================================
VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0,
    "NA": None
}

def calcular_nota(df):
    df = df[df["Resposta"] != "NA"].copy()
    if df.empty:
        return None
    df["valor"] = df["Resposta"].map(VALORES)
    return (df["valor"] * df["Peso"]).sum() / df["Peso"].sum()

def cor_semaforo(nota):
    if nota is None:
        return colors.grey
    if nota <= 0.25:
        return colors.green
    elif nota <= 0.50:
        return colors.yellow
    elif nota < 0.75:
        return colors.orange
    else:
        return colors.red

# ======================================================
# PDF
# ======================================================
def gerar_pdf(cabecalho, avaliacoes, caminho):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(caminho, pagesize=A4)
    elementos = []

    # ---------- CABEÇALHO ----------
    elementos.append(Paragraph("<b>RELATÓRIO EXECUTIVO – AVALIAÇÃO CONTRATUAL</b>", styles["Title"]))
    elementos.append(Spacer(1, 12))

    for k, v in cabecalho.items():
        elementos.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))

    elementos.append(Spacer(1, 20))

    # ---------- RESUMO EXECUTIVO ----------
    tabela = [["", "Código", "Descrição"]]

    for aba, dados in avaliacoes.items():
        df = pd.DataFrame(dados)
        nota = calcular_nota(df)
        tabela.append(["", df.iloc[0]["Codigo"], df.iloc[0]["Descricao"]])

    t = Table(tabela, colWidths=[20, 80, 380])
    estilo = [("GRID", (1,0), (-1,-1), 0.5, colors.grey)]

    for i, (aba, dados) in enumerate(avaliacoes.items(), start=1):
        df = pd.DataFrame(dados)
        nota = calcular_nota(df)
        estilo.append(("BACKGROUND", (0,i), (0,i), cor_semaforo(nota)))

    t.setStyle(estilo)
    elementos.append(t)

    elementos.append(Spacer(1, 30))
    elementos.append(Paragraph("<b>JUSTIFICATIVAS</b>", styles["Heading2"]))
    elementos.append(Spacer(1, 12))

    # ---------- JUSTIFICATIVAS (SEQUENCIAL) ----------
    for aba, dados in avaliacoes.items():
        df = pd.DataFrame(dados)
        nota = calcular_nota(df)

        header = Table(
            [["", f"{df.iloc[0]['Codigo']} – {df.iloc[0]['Descricao']}"]],
            colWidths=[20, 460]
        )
        header.setStyle([
            ("BACKGROUND", (0,0), (0,0), cor_semaforo(nota)),
            ("BOX", (0,0), (-1,-1), 0.5, colors.black)
        ])
        elementos.append(header)
        elementos.append(Spacer(1, 8))

        justs = df[
            (df["Resposta"].isin(["Ruim", "Crítico"])) &
            (df["Justificativa"].str.strip() != "")
        ]

        for _, r in justs.iterrows():
            elementos.append(Paragraph(
                f"<b>{r['Tipo']}:</b> {r['Justificativa']}",
                styles["Normal"]
            ))
            elementos.append(Spacer(1, 6))

        elementos.append(Spacer(1, 12))

    doc.build(elementos)

# ======================================================
# ESTADO
# ======================================================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

if "modo_app" not in st.session_state:
    st.session_state.modo_app = None

# ======================================================
# UI – CABEÇALHO
# ======================================================
st.title("Painel Administração Contratual")

col1, col2, col3 = st.columns(3)
projeto = col1.text_input("Projeto")
cliente = col2.text_input("Cliente")
responsavel = col3.text_input("Responsável")

data_av = st.date_input("Data", datetime.now().date())
hora_av = st.time_input("Hora", (datetime.utcnow() - timedelta(hours=3)).time())

# ======================================================
# AÇÕES
# ======================================================
colA, colB = st.columns(2)
if colA.button("🆕 Nova Avaliação", use_container_width=True):
    st.session_state.modo_app = "nova"

if colB.button("📂 Abrir Avaliação Existente", use_container_width=True):
    st.session_state.modo_app = "abrir"

# ======================================================
# ABRIR AVALIAÇÃO
# ======================================================
if st.session_state.modo_app == "abrir":
    if not st.session_state.avaliacoes_por_data:
        st.info("Nenhuma avaliação salva.")
        st.stop()

    chave = st.selectbox(
        "Selecione a avaliação",
        sorted(st.session_state.avaliacoes_por_data.keys(), reverse=True)
    )

    if st.button("Abrir Avaliação"):
        st.session_state.avaliacoes = {
            aba: pd.DataFrame(dados)
            for aba, dados in st.session_state.avaliacoes_por_data[chave].items()
        }
        st.success("Avaliação carregada.")

# ======================================================
# UPLOAD
# ======================================================
uploaded = st.file_uploader("Upload do Excel", type=["xlsx"])
if not uploaded:
    st.stop()

xls = pd.ExcelFile(uploaded)

# ======================================================
# CANVAS
# ======================================================
st.subheader("Canvas da Avaliação")

for aba in xls.sheet_names:
    base = xls.parse(aba)

    if aba not in st.session_state.avaliacoes:
        base["Resposta"] = "NA"
        base["Justificativa"] = ""
        st.session_state.avaliacoes[aba] = base
    else:
        base = st.session_state.avaliacoes[aba]

    with st.expander(f"{base.iloc[0]['Codigo']} – {base.iloc[0]['Descricao']}"):
        for tipo in base["Tipo"].unique():
            st.markdown(f"**{tipo}**")
            bloco = base[base["Tipo"] == tipo]

            for i, r in bloco.iterrows():
                resp = st.selectbox(
                    r["Pergunta"],
                    ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                    index=["Bom","Médio","Ruim","Crítico","NA"].index(r["Resposta"]),
                    key=f"{aba}_{i}"
                )
                base.at[i, "Resposta"] = resp

                if resp in ["Ruim", "Crítico"]:
                    base.at[i, "Justificativa"] = st.text_input(
                        "Justificativa",
                        value=r["Justificativa"],
                        key=f"{aba}_{i}_j"
                    )

    st.session_state.avaliacoes[aba] = base

# ======================================================
# SALVAR / PDF
# ======================================================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    st.session_state.avaliacoes_por_data[chave] = {
        aba: df.to_dict(orient="records")
        for aba, df in st.session_state.avaliacoes.items()
    }
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success("Avaliação salva com sucesso.")

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
