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
# CONFIG
# ===============================
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

CORES = {
    "Bom": colors.green,
    "Médio": colors.yellow,
    "Ruim": colors.orange,
    "Crítico": colors.red,
    "NA": colors.grey
}

# ===============================
# PERSISTÊNCIA
# ===============================
def carregar_avaliacoes():
    if os.path.exists(AVALIACOES_FILE):
        with open(AVALIACOES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_avaliacoes(dados):
    with open(AVALIACOES_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# ===============================
# FUNÇÕES
# ===============================
def calcular_status(df):
    dfv = df[df["Resposta"] != "NA"].copy()
    if dfv.empty:
        return "NA"
    dfv["valor"] = dfv["Resposta"].map(VALORES)
    nota = (dfv["valor"] * dfv["Peso"]).sum() / dfv["Peso"].sum()
    if nota <= 0.25:
        return "Bom"
    elif nota <= 0.5:
        return "Médio"
    elif nota < 0.75:
        return "Ruim"
    return "Crítico"

# ===============================
# ESTADO
# ===============================
if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = None

# ===============================
# TÍTULO
# ===============================
st.title("Painel Administração Contratual")

# ===============================
# MENU
# ===============================
col1, col2 = st.columns(2)
with col1:
    nova = st.button("🆕 Nova Avaliação", use_container_width=True)
with col2:
    abrir = st.button("📂 Abrir Avaliação Existente", use_container_width=True)

# ===============================
# NOVA AVALIAÇÃO
# ===============================
if nova:
    st.session_state.avaliacao_atual = {
        "cabecalho": {},
        "dados": {}
    }

# ===============================
# ABRIR AVALIAÇÃO
# ===============================
if abrir:
    if not st.session_state.avaliacoes:
        st.info("Nenhuma avaliação salva.")
        st.stop()

    chave = st.selectbox(
        "Selecione a avaliação",
        list(st.session_state.avaliacoes.keys())
    )

    if st.button("Abrir"):
        st.session_state.avaliacao_atual = json.loads(
            json.dumps(st.session_state.avaliacoes[chave])
        )

# ===============================
# SE NÃO EXISTE AVALIAÇÃO ATUAL
# ===============================
if st.session_state.avaliacao_atual is None:
    st.stop()

# ===============================
# CABEÇALHO
# ===============================
st.subheader("Cabeçalho")

cab = st.session_state.avaliacao_atual["cabecalho"]

cab["Projeto"] = st.text_input("Nome do Projeto", cab.get("Projeto", ""))
cab["Cliente"] = st.text_input("Cliente", cab.get("Cliente", ""))
cab["Responsavel"] = st.text_input("Responsável", cab.get("Responsavel", ""))
cab["Data"] = st.date_input("Data", datetime.now().date())
cab["Hora"] = st.time_input("Hora", (datetime.utcnow() - timedelta(hours=3)).time())

# ===============================
# UPLOAD EXCEL
# ===============================
uploaded = st.file_uploader("Upload do Excel", type=["xlsx"])

if not uploaded:
    st.stop()

xls = pd.ExcelFile(uploaded)

# ===============================
# CANVAS
# ===============================
st.subheader("Avaliação")

for aba in xls.sheet_names:
    base = xls.parse(aba)

    if aba not in st.session_state.avaliacao_atual["dados"]:
        base["Resposta"] = "NA"
        base["Justificativa"] = ""
        st.session_state.avaliacao_atual["dados"][aba] = base
    else:
        base = st.session_state.avaliacao_atual["dados"][aba]

    fase = base.iloc[0]["Fase"]
    grupo = base.iloc[0]["Grupo"]
    codigo = base.iloc[0]["Codigo"]
    descricao = base.iloc[0]["Descricao"]

    status = calcular_status(base)

    with st.expander(f"{fase} ▸ {grupo} ▸ {codigo} – {descricao} ({status})"):
        for tipo in ["Procedimento", "Acompanhamento"]:
            st.markdown(f"**{tipo}**")
            bloco = base[base["Tipo"] == tipo]

            for i, r in bloco.iterrows():
                resp = st.selectbox(
                    r["Pergunta"],
                    OPCOES,
                    index=OPCOES.index(r["Resposta"]),
                    key=f"{aba}_{i}"
                )
                base.at[i, "Resposta"] = resp

                if resp in ["Ruim", "Crítico"]:
                    just = st.text_input(
                        "Justificativa",
                        r["Justificativa"],
                        key=f"{aba}_{i}_j"
                    )
                    base.at[i, "Justificativa"] = just
                else:
                    base.at[i, "Justificativa"] = ""

    st.session_state.avaliacao_atual["dados"][aba] = base

# ===============================
# SALVAR
# ===============================
if st.button("💾 Salvar Avaliação"):
    chave = f"{cab['Data']} {cab['Hora'].strftime('%H:%M')}"
    st.session_state.avaliacoes[chave] = json.loads(
        json.dumps(st.session_state.avaliacao_atual)
    )
    salvar_avaliacoes(st.session_state.avaliacoes)
    st.success("Avaliação salva com sucesso.")

# ===============================
# GERAR PDF
# ===============================
def gerar_pdf(avaliacao, nome):
    doc = SimpleDocTemplate(nome, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    cab = avaliacao["cabecalho"]

    story.append(Paragraph("<b>Resumo Geral</b>", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Projeto: {cab['Projeto']}", styles["Normal"]))
    story.append(Paragraph(f"Cliente: {cab['Cliente']}", styles["Normal"]))
    story.append(Paragraph(f"Responsável: {cab['Responsavel']}", styles["Normal"]))
    story.append(Paragraph(f"Data: {cab['Data']} {cab['Hora']}", styles["Normal"]))
    story.append(Spacer(1, 12))

    dados = []
    for aba, df in avaliacao["dados"].items():
        status = calcular_status(df)
        dados.append([
            df.iloc[0]["Fase"],
            df.iloc[0]["Grupo"],
            f"{df.iloc[0]['Codigo']} – {df.iloc[0]['Descricao']}",
            status
        ])

    tabela = Table([["Fase", "Grupo", "Disciplina", "Status"]] + dados)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 1, colors.black)
    ]))
    story.append(tabela)
    story.append(PageBreak())

    story.append(Paragraph("<b>Justificativas</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    for aba, df in avaliacao["dados"].items():
        justs = df[df["Justificativa"] != ""]
        if justs.empty:
            continue

        status = calcular_status(df)
        story.append(
            Paragraph(
                f"<b>{df.iloc[0]['Fase']} ▸ {df.iloc[0]['Grupo']} ▸ {df.iloc[0]['Codigo']} – {df.iloc[0]['Descricao']} ({status})</b>",
                styles["Normal"]
            )
        )
        story.append(Spacer(1, 6))

        for _, r in justs.iterrows():
            story.append(Paragraph(f"- {r['Justificativa']}", styles["Normal"]))

        story.append(Spacer(1, 12))

    doc.build(story)

if st.button("📄 Gerar PDF"):
    gerar_pdf(st.session_state.avaliacao_atual, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF", f, "avaliacao.pdf")
