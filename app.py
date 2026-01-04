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
    "Médio": 0.33,
    "Ruim": 0.66,
    "Crítico": 1.0,
    "NA": None
}

def calcular_nota(df):
    validos = df[df["Resposta"] != "NA"].copy()
    if validos.empty:
        return None
    validos["valor"] = validos["Resposta"].map(VALORES)
    return (validos["valor"] * validos["Peso"]).sum() / validos["Peso"].sum()

def semaforo(nota):
    if nota is None:
        return ("⚪", colors.lightgrey)
    if nota <= 0.25:
        return ("🟢", colors.green)
    if nota <= 0.50:
        return ("🟡", colors.yellow)
    if nota < 0.75:
        return ("🟠", colors.orange)
    return ("🔴", colors.red)

# ===============================
# ESTADO
# ===============================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {}

if "modo" not in st.session_state:
    st.session_state.modo = None

# ===============================
# TÍTULO
# ===============================
st.title("Painel Administração Contratual")

# ===============================
# MENU INICIAL
# ===============================
col1, col2 = st.columns(2)
with col1:
    if st.button("🆕 Nova Avaliação", use_container_width=True):
        st.session_state.modo = "nova"
with col2:
    if st.button("📂 Abrir Avaliação Existente", use_container_width=True):
        st.session_state.modo = "abrir"

if st.session_state.modo is None:
    st.stop()

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
        dados = st.session_state.avaliacoes_por_data[chave]
        st.session_state.avaliacao_atual = {
            "cabecalho": dados["cabecalho"],
            "disciplinas": {
                k: pd.DataFrame(v) for k, v in dados["disciplinas"].items()
            }
        }
        st.success("Avaliação carregada.")

# ===============================
# CABEÇALHO
# ===============================
st.subheader("Cabeçalho da Avaliação")

cab = st.session_state.avaliacao_atual.get("cabecalho", {})

nome_projeto = st.text_input("Nome do Projeto", cab.get("projeto", ""))
cliente = st.text_input("Cliente", cab.get("cliente", ""))
responsavel = st.text_input("Responsável", cab.get("responsavel", ""))

data_av = st.date_input("Data", cab.get("data", datetime.now().date()))
hora_av = st.time_input(
    "Hora",
    cab.get("hora", (datetime.utcnow() - timedelta(hours=3)).time())
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
st.subheader("Avaliação")

disciplinas = {}

for aba in xls.sheet_names:
    df = xls.parse(aba)

    if aba not in st.session_state.avaliacao_atual.get("disciplinas", {}):
        df["Resposta"] = "NA"
        df["Justificativa"] = ""
    else:
        df = st.session_state.avaliacao_atual["disciplinas"][aba]

    disciplinas[aba] = df

    codigo = df.iloc[0]["Codigo"]
    descricao = df.iloc[0]["Descricao"]

    nota = calcular_nota(df)
    icon, _ = semaforo(nota)

    with st.expander(f"{icon} {codigo} – {descricao}", expanded=False):

        for tipo in ["Procedimento", "Acompanhamento"]:
            bloco = df[df["Tipo"] == tipo]
            if bloco.empty:
                continue

            st.markdown(f"**{tipo}**")

            for i, row in bloco.iterrows():
                resposta = st.selectbox(
                    row["Pergunta"],
                    ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                    index=["Bom", "Médio", "Ruim", "Crítico", "NA"].index(row["Resposta"]),
                    key=f"{aba}_{i}"
                )

                justificativa = row["Justificativa"]
                if resposta in ["Ruim", "Crítico"]:
                    justificativa = st.text_input(
                        "Justificativa",
                        value=justificativa,
                        key=f"{aba}_{i}_j"
                    )

                df.at[i, "Resposta"] = resposta
                df.at[i, "Justificativa"] = justificativa

# ===============================
# SALVAR
# ===============================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data_av} {hora_av.strftime('%H:%M')}"

    st.session_state.avaliacoes_por_data[chave] = {
        "cabecalho": {
            "projeto": nome_projeto,
            "cliente": cliente,
            "responsavel": responsavel,
            "data": str(data_av),
            "hora": hora_av.strftime("%H:%M")
        },
        "disciplinas": {
            k: v.to_dict(orient="records") for k, v in disciplinas.items()
        }
    }

    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success("Avaliação salva com sucesso.")

# ===============================
# PDF
# ===============================
def gerar_pdf(chave, dados):
    pdf_path = "avaliacao.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    cab = dados["cabecalho"]
    story.append(Paragraph(f"<b>{cab['projeto']}</b>", styles["Title"]))
    story.append(Paragraph(f"Cliente: {cab['cliente']}", styles["Normal"]))
    story.append(Paragraph(f"Responsável: {cab['responsavel']}", styles["Normal"]))
    story.append(Paragraph(f"Avaliação: {chave}", styles["Normal"]))
    story.append(Spacer(1, 20))

    # Resumo
    story.append(Paragraph("Resumo", styles["Heading2"]))
    table_data = [["Disciplina", "Status"]]

    for aba, df in dados["disciplinas"].items():
        df = pd.DataFrame(df)
        codigo = df.iloc[0]["Codigo"]
        descricao = df.iloc[0]["Descricao"]
        nota = calcular_nota(df)
        _, cor = semaforo(nota)

        table_data.append([
            f"{codigo} – {descricao}",
            ""
        ])

    t = Table(table_data, colWidths=[400, 50])
    t.setStyle(TableStyle([
        ("BACKGROUND", (1, 1), (-1, -1), cor),
        ("BOX", (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(t)
    story.append(PageBreak())

    # Justificativas
    story.append(Paragraph("Justificativas", styles["Heading2"]))

    for aba, df in dados["disciplinas"].items():
        df = pd.DataFrame(df)
        justificadas = df[df["Justificativa"] != ""]
        if justificadas.empty:
            continue

        codigo = df.iloc[0]["Codigo"]
        descricao = df.iloc[0]["Descricao"]
        nota = calcular_nota(df)
        icon, _ = semaforo(nota)

        story.append(Spacer(1, 10))
        story.append(Paragraph(f"{icon} {codigo} – {descricao}", styles["Heading3"]))

        for tipo in ["Procedimento", "Acompanhamento"]:
            bloco = justificadas[justificadas["Tipo"] == tipo]
            if bloco.empty:
                continue

            story.append(Paragraph(tipo, styles["Italic"]))
            for _, row in bloco.iterrows():
                story.append(Paragraph(f"- {row['Justificativa']}", styles["Normal"]))

    doc.build(story)
    return pdf_path

# ===============================
# BOTÃO PDF
# ===============================
if st.button("📄 Gerar PDF"):
    chave = f"{data_av} {hora_av.strftime('%H:%M')}"
    pdf = gerar_pdf(chave, st.session_state.avaliacoes_por_data[chave])

    with open(pdf, "rb") as f:
        st.download_button(
            "⬇️ Download do PDF",
            f,
            file_name="avaliacao.pdf"
        )
