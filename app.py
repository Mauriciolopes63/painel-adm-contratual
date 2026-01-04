import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# ===============================
# CONFIG
# ===============================
st.set_page_config("Painel Administração Contratual", layout="wide")

ARQ_AVALIACOES = "avaliacoes.json"

VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0,
    "NA": None
}

def cor_por_nota(n):
    if n is None:
        return ("⚪", colors.grey)
    if n <= 0.25:
        return ("🟢", colors.green)
    if n <= 0.50:
        return ("🟡", colors.yellow)
    if n < 0.75:
        return ("🟠", colors.orange)
    return ("🔴", colors.red)

# ===============================
# PERSISTÊNCIA
# ===============================
def carregar_avaliacoes():
    if os.path.exists(ARQ_AVALIACOES):
        with open(ARQ_AVALIACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_avaliacoes(dados):
    with open(ARQ_AVALIACOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# ===============================
# CÁLCULO
# ===============================
def calcular_media(df):
    dfv = df[df["Resposta"] != "NA"].copy()
    if dfv.empty:
        return None
    dfv["valor"] = dfv["Resposta"].map(VALORES)
    return (dfv["valor"] * dfv["Peso"]).sum() / dfv["Peso"].sum()

# ===============================
# PDF
# ===============================
def gerar_pdf(cab, resumo, justificativas, arquivo):
    doc = SimpleDocTemplate(arquivo, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Cabeçalho
    story.append(Paragraph("<b>Painel Administração Contratual</b>", styles["Title"]))
    for k, v in cab.items():
        story.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))
    story.append(Spacer(1, 20))

    # Resumo
    story.append(Paragraph("<b>Resumo por Disciplina</b>", styles["Heading2"]))
    tabela = [["Fase", "Grupo", "Disciplina", "Status"]]

    for r in resumo:
        tabela.append([
            r["fase"],
            r["grupo"],
            r["disciplina"],
            r["icone"]
        ])

    t = Table(tabela, colWidths=[90, 120, 180, 60])
    t.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
    ]))
    story.append(t)
    story.append(PageBreak())

    # Justificativas
    story.append(Paragraph("<b>Justificativas</b>", styles["Heading2"]))

    atual = None
    for j in justificativas:
        chave = (j["fase"], j["grupo"], j["disciplina"])
        if chave != atual:
            story.append(Spacer(1, 10))
            story.append(Paragraph(
                f"{j['icone']} <b>{j['fase']} / {j['grupo']} / {j['disciplina']}</b>",
                styles["Heading3"]
            ))
            atual = chave

        story.append(Paragraph(
            f"<b>{j['tipo']}</b>: {j['justificativa']}",
            styles["Normal"]
        ))

    doc.build(story)

# ===============================
# ESTADO
# ===============================
if "avaliacoes_salvas" not in st.session_state:
    st.session_state.avaliacoes_salvas = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {}

# ===============================
# UI
# ===============================
st.title("Painel Administração Contratual")

modo = st.radio("Modo:", ["Nova Avaliação", "Abrir Avaliação Existente"], horizontal=True)

st.markdown("### Cabeçalho")
projeto = st.text_input("Nome do Projeto")
cliente = st.text_input("Cliente")
responsavel = st.text_input("Responsável")

data = st.date_input("Data", datetime.now().date())
hora = st.time_input("Hora", (datetime.utcnow() - timedelta(hours=3)).time())
chave_data = f"{data} {hora.strftime('%H:%M')}"

if modo == "Abrir Avaliação Existente":
    if not st.session_state.avaliacoes_salvas:
        st.info("Nenhuma avaliação salva.")
        st.stop()

    sel = st.selectbox("Selecione a avaliação", list(st.session_state.avaliacoes_salvas.keys()))
    st.session_state.avaliacao_atual = {
        k: pd.DataFrame(v) for k, v in st.session_state.avaliacoes_salvas[sel]["respostas"].items()
    }

uploaded = st.file_uploader("Upload do Excel", type=["xlsx"])
if not uploaded:
    st.stop()

xls = pd.ExcelFile(uploaded)

resumo = []
justificativas = []

for aba in xls.sheet_names:
    base = xls.parse(aba)

    fase = base.iloc[0]["Fase"]
    grupo = base.iloc[0]["Grupo"]
    codigo = base.iloc[0]["Codigo"]
    desc = base.iloc[0]["Descricao"]
    disciplina = f"{codigo} – {desc}"

    if aba not in st.session_state.avaliacao_atual:
        base["Resposta"] = "NA"
        base["Justificativa"] = ""
    else:
        base = st.session_state.avaliacao_atual[aba]

    nota = calcular_media(base)
    icone, cor = cor_por_nota(nota)

    resumo.append({
        "fase": fase,
        "grupo": grupo,
        "disciplina": disciplina,
        "icone": icone
    })

    with st.expander(f"{icone} {disciplina}", expanded=False):

        for tipo in ["Procedimento", "Acompanhamento"]:
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
                    jus = st.text_input(
                        "Justificativa",
                        value=r["Justificativa"],
                        key=f"{aba}_{i}_j"
                    )
                    base.at[i, "Justificativa"] = jus
                    justificativas.append({
                        "fase": fase,
                        "grupo": grupo,
                        "disciplina": disciplina,
                        "tipo": tipo,
                        "icone": icone,
                        "justificativa": jus
                    })

    st.session_state.avaliacao_atual[aba] = base

st.divider()

if st.button("💾 Salvar Avaliação"):
    st.session_state.avaliacoes_salvas[chave_data] = {
        "cabecalho": {
            "Projeto": projeto,
            "Cliente": cliente,
            "Responsável": responsavel,
            "Data": chave_data
        },
        "respostas": {
            k: v.to_dict(orient="records")
            for k, v in st.session_state.avaliacao_atual.items()
        }
    }
    salvar_avaliacoes(st.session_state.avaliacoes_salvas)
    st.success("Avaliação salva com sucesso.")

if st.button("📄 Gerar PDF"):
    gerar_pdf(
        {
            "Projeto": projeto,
            "Cliente": cliente,
            "Responsável": responsavel,
            "Data": chave_data
        },
        resumo,
        justificativas,
        "avaliacao.pdf"
    )
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF", f, "avaliacao.pdf")
