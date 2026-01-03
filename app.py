import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

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

# ===============================
# PDF
# ===============================
def gerar_pdf(cabecalho, avaliacoes, caminho):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(caminho, pagesize=A4)
    elementos = []

    elementos.append(Paragraph("<b>RELATÓRIO DE AVALIAÇÃO CONTRATUAL</b>", styles["Title"]))
    elementos.append(Spacer(1, 12))

    for k, v in cabecalho.items():
        elementos.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))

    elementos.append(Spacer(1, 20))

    for disciplina, dados in avaliacoes.items():
        df = pd.DataFrame(dados)

        codigo = df.iloc[0]["Codigo"]
        descricao = df.iloc[0]["Descricao"]

        nota = calcular_nota(df)
        cor = semaforo(nota)

        elementos.append(Paragraph(
            f"<b>{cor} {codigo} – {descricao}</b>",
            styles["Heading2"]
        ))
        elementos.append(Spacer(1, 8))

        justificativas = df[
            (df["Resposta"].isin(["Ruim", "Crítico"])) &
            (df["Justificativa"].str.strip() != "")
        ]

        if justificativas.empty:
            elementos.append(Paragraph("Nenhuma justificativa registrada.", styles["Normal"]))
        else:
            tabela = [["Tipo", "Justificativa"]]
            for _, r in justificativas.iterrows():
                tabela.append([r["Tipo"], r["Justificativa"]])

            elementos.append(Table(tabela, hAlign="LEFT"))

        elementos.append(Spacer(1, 15))

    doc.build(elementos)

# ===============================
# ESTADO
# ===============================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

# ===============================
# TÍTULO
# ===============================
st.title("Painel Administração Contratual")

# ===============================
# CABEÇALHO
# ===============================
st.markdown("### Dados do Empreendimento")

col1, col2, col3 = st.columns(3)

with col1:
    nome_projeto = st.text_input("Nome do Projeto")

with col2:
    nome_cliente = st.text_input("Cliente")

with col3:
    responsavel = st.text_input("Responsável")

data_avaliacao = st.date_input("Data", datetime.now().date())
hora_avaliacao = st.time_input(
    "Hora",
    (datetime.utcnow() - timedelta(hours=3)).time()
)

# ===============================
# AÇÕES
# ===============================
colA, colB = st.columns(2)

with colA:
    nova = st.button("🆕 Nova Avaliação", use_container_width=True)

with colB:
    abrir = st.button("📂 Abrir Avaliação Existente", use_container_width=True)

if abrir:
    if not st.session_state.avaliacoes_por_data:
        st.info("Ainda não existem avaliações salvas.")
    else:
        data_sel = st.selectbox(
            "Selecione a avaliação",
            sorted(st.session_state.avaliacoes_por_data.keys(), reverse=True)
        )
        if st.button("Abrir"):
            dados = st.session_state.avaliacoes_por_data[data_sel]
            st.session_state.avaliacoes = {
                k: pd.DataFrame(v) for k, v in dados.items()
            }
            st.success("Avaliação carregada.")

# ===============================
# UPLOAD
# ===============================
uploaded_file = st.file_uploader("Upload do Excel", type=["xlsx"])
if not uploaded_file:
    st.stop()

xls = pd.ExcelFile(uploaded_file)

# ===============================
# CANVAS
# ===============================
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
    cor = semaforo(nota)

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

# ===============================
# SALVAR / PDF
# ===============================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data_avaliacao} {hora_avaliacao.strftime('%H:%M')}"
    dados = {
        aba: df.to_dict(orient="records")
        for aba, df in st.session_state.avaliacoes.items()
    }
    st.session_state.avaliacoes_por_data[chave] = dados
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success("Avaliação salva com sucesso.")

if st.button("📄 Gerar PDF"):
    cab = {
        "Projeto": nome_projeto,
        "Cliente": nome_cliente,
        "Responsável": responsavel,
        "Data": f"{data_avaliacao} {hora_avaliacao.strftime('%H:%M')}"
    }
    gerar_pdf(cab, st.session_state.avaliacoes, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF", f, file_name="avaliacao.pdf")
