import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet

# ===============================
# CONFIG
# ===============================
st.set_page_config("Painel Administração Contratual", layout="wide")

AVALIACOES_FILE = "avaliacoes.json"

VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0,
    "NA": None
}

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
# CÁLCULO
# ===============================
def calcular_media(df):
    base = df[df["Resposta"] != "NA"].copy()
    if base.empty:
        return None

    base["valor"] = base["Resposta"].map(VALORES)
    soma = (base["valor"] * base["Peso"]).sum()
    peso = base["Peso"].sum()

    return soma / peso if peso > 0 else None

def semaforo(nota):
    if nota is None:
        return "⚪"
    if nota <= 0.25:
        return "🟢"
    elif nota <= 0.50:
        return "🟡"
    elif nota < 0.75:
        return "🟠"
    return "🔴"

# ===============================
# PDF
# ===============================
def gerar_pdf(cabecalho, avaliacoes, arquivo="avaliacao.pdf"):
    doc = SimpleDocTemplate(arquivo, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Cabeçalho
    story.append(Paragraph("<b>Relatório de Avaliação Contratual</b>", styles["Title"]))
    for k, v in cabecalho.items():
        story.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))
    story.append(Spacer(1, 20))

    # Resumo
    story.append(Paragraph("<b>Resumo por Disciplina</b>", styles["Heading2"]))
    tabela = [["Disciplina", "Status"]]

    for aba, df in avaliacoes.items():
        nota = calcular_media(df)
        tabela.append([aba, semaforo(nota)])

    story.append(Table(tabela))
    story.append(Spacer(1, 20))

    # Justificativas
    story.append(Paragraph("<b>Justificativas</b>", styles["Heading2"]))

    for aba, df in avaliacoes.items():
        for _, row in df.iterrows():
            if row["Resposta"] in ["Ruim", "Crítico"] and row["Justificativa"]:
                story.append(
                    Paragraph(
                        f"<b>{aba}</b> – {row['Resposta']}: {row['Justificativa']}",
                        styles["Normal"]
                    )
                )
                story.append(Spacer(1, 6))

    doc.build(story)

# ===============================
# ESTADO
# ===============================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

if "avaliacao_aberta" not in st.session_state:
    st.session_state.avaliacao_aberta = None

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
    nome_projeto = st.text_input("Projeto")
with col2:
    cliente = st.text_input("Cliente")
with col3:
    responsavel = st.text_input("Responsável")

st.markdown("### Data da Avaliação")

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
    if st.button("🆕 Nova Avaliação"):
        st.session_state.avaliacoes = {}
        st.session_state.avaliacao_aberta = None

with colB:
    if st.button("📂 Abrir Avaliação Existente"):
        if not st.session_state.avaliacoes_por_data:
            st.warning("Nenhuma avaliação salva.")
        else:
            st.session_state.modo_abrir = True

# ===============================
# ABRIR AVALIAÇÃO
# ===============================
if st.session_state.get("modo_abrir"):
    datas = list(st.session_state.avaliacoes_por_data.keys())
    selecionada = st.selectbox("Selecione a avaliação", datas)

    if st.button("Abrir"):
        dados = st.session_state.avaliacoes_por_data[selecionada]
        st.session_state.avaliacoes = {
            aba: pd.DataFrame(registros)
            for aba, registros in dados.items()
        }
        st.session_state.avaliacao_aberta = selecionada
        st.success(f"Avaliação {selecionada} carregada.")
        st.session_state.modo_abrir = False

# ===============================
# UPLOAD EXCEL
# ===============================
uploaded = st.file_uploader("Carregar Excel do Projeto", type=["xlsx"])

if not uploaded:
    st.stop()

xls = pd.ExcelFile(uploaded)

# ===============================
# CANVAS
# ===============================
st.subheader("Canvas do Projeto")

for aba in xls.sheet_names:

    # 🔑 CORREÇÃO CRÍTICA
    if aba in st.session_state.avaliacoes:
        df = st.session_state.avaliacoes[aba]
    else:
        df = xls.parse(aba)
        df["Resposta"] = "NA"
        df["Justificativa"] = ""
        st.session_state.avaliacoes[aba] = df

    codigo = df.iloc[0]["Codigo"]
    descricao = df.iloc[0]["Descricao"]

    nota = calcular_media(df)
    status = semaforo(nota)

    with st.expander(f"{status} {codigo} – {descricao}"):

        for tipo in ["Procedimento", "Acompanhamento"]:
            sub = df[df["Tipo"] == tipo]

            if sub.empty:
                continue

            st.markdown(f"#### {tipo}")

            for i, row in sub.iterrows():
                resp = st.selectbox(
                    row["Pergunta"],
                    ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                    index=["Bom", "Médio", "Ruim", "Crítico", "NA"].index(row["Resposta"]),
                    key=f"{aba}_{i}"
                )

                just = row["Justificativa"]
                if resp in ["Ruim", "Crítico"]:
                    just = st.text_input(
                        "Justificativa",
                        value=just,
                        key=f"{aba}_{i}_j"
                    )

                df.at[i, "Resposta"] = resp
                df.at[i, "Justificativa"] = just

        st.session_state.avaliacoes[aba] = df

# ===============================
# SALVAR
# ===============================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data_avaliacao} {hora_avaliacao.strftime('%H:%M')}"

    st.session_state.avaliacoes_por_data[chave] = {
        aba: df.to_dict(orient="records")
        for aba, df in st.session_state.avaliacoes.items()
    }

    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success(f"Avaliação salva em {chave}")

# ===============================
# PDF
# ===============================
if st.session_state.avaliacoes:
    if st.button("📄 Gerar PDF"):
        cabecalho = {
            "Projeto": nome_projeto,
            "Cliente": cliente,
            "Responsável": responsavel,
            "Data": f"{data_avaliacao} {hora_avaliacao.strftime('%H:%M')}"
        }

        gerar_pdf(cabecalho, st.session_state.avaliacoes)
        st.success("PDF gerado com sucesso.")
