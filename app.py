import streamlit as st
import pandas as pd
import json
import os
import copy
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from io import BytesIO

# ======================================================
# CONFIG
# ======================================================
st.set_page_config("Painel Administração Contratual", layout="wide")
ARQ_AVALIACOES = "avaliacoes.json"

OPCOES = ["Bom", "Médio", "Ruim", "Crítico", "NA"]

VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0,
    "NA": None
}

CORES = {
    "🟢": colors.green,
    "🟡": colors.yellow,
    "🟠": colors.orange,
    "🔴": colors.red,
    "⚪": colors.lightgrey
}

# ======================================================
# PERSISTÊNCIA
# ======================================================
def carregar():
    if os.path.exists(ARQ_AVALIACOES):
        with open(ARQ_AVALIACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar(dados):
    with open(ARQ_AVALIACOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# ======================================================
# CÁLCULOS
# ======================================================
def media(df):
    dfv = df[df["Resposta"] != "NA"].copy()
    if dfv.empty:
        return None
    dfv["valor"] = dfv["Resposta"].map(VALORES)
    return (dfv["valor"] * dfv["Peso"]).sum() / dfv["Peso"].sum()

def semaforo(n):
    if n is None: return "⚪"
    if n <= 0.25: return "🟢"
    if n <= 0.50: return "🟡"
    if n < 0.75:  return "🟠"
    return "🔴"

# ======================================================
# PDF
# ======================================================
def gerar_pdf(cab, estrutura):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    pag = 1

    def rodape():
        c.setFont("Helvetica", 8)
        c.drawRightString(w - 40, 20, f"Página {pag}")

    # CAPA
    y = h - 60
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "PAINEL DE ADMINISTRAÇÃO CONTRATUAL")
    y -= 40
    c.setFont("Helvetica", 11)
    for k, v in cab.items():
        c.drawString(40, y, f"{k}: {v}")
        y -= 20
    rodape()
    c.showPage()
    pag += 1

    # RESUMO
    y = h - 50
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Resumo Geral")
    y -= 30

    for fase, grupos in estrutura.items():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, fase)
        y -= 20

        for grupo, discs in grupos.items():
            c.setFont("Helvetica-Bold", 10)
            c.drawString(60, y, grupo)
            y -= 20

            for d in discs:
                c.setFillColor(CORES[d["semaforo"]])
                c.rect(80, y - 10, 10, 10, fill=1)
                c.setFillColor(colors.black)
                c.drawString(100, y - 10, f"{d['codigo']} – {d['descricao']}")
                y -= 15

                if y < 60:
                    rodape()
                    c.showPage()
                    pag += 1
                    y = h - 50

    rodape()
    c.showPage()
    pag += 1

    # JUSTIFICATIVAS
    y = h - 50
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Justificativas")
    y -= 30

    for fase, grupos in estrutura.items():
        for grupo, discs in grupos.items():
            for d in discs:
                if not d["justificativas"]:
                    continue

                c.setFillColor(CORES[d["semaforo"]])
                c.rect(40, y - 10, 10, 10, fill=1)
                c.setFillColor(colors.black)
                c.setFont("Helvetica-Bold", 10)
                c.drawString(60, y - 10, f"{d['codigo']} – {d['descricao']}")
                y -= 20

                for tipo, textos in d["justificativas"].items():
                    if textos:
                        c.setFont("Helvetica-Bold", 9)
                        c.drawString(70, y, tipo)
                        y -= 14
                        c.setFont("Helvetica", 9)
                        for t in textos:
                            c.drawString(80, y, f"- {t}")
                            y -= 12

                y -= 10
                if y < 60:
                    rodape()
                    c.showPage()
                    pag += 1
                    y = h - 50

    rodape()
    c.save()
    buf.seek(0)
    return buf

# ======================================================
# ESTADO
# ======================================================
if "historico" not in st.session_state:
    st.session_state.historico = carregar()

if "atual" not in st.session_state:
    st.session_state.atual = {}

# ======================================================
# CABEÇALHO
# ======================================================
st.title("Painel Administração Contratual")

c1, c2, c3 = st.columns(3)
projeto = c1.text_input("Projeto")
cliente = c2.text_input("Cliente")
responsavel = c3.text_input("Responsável")

data = st.date_input("Data", datetime.now().date())
hora = st.time_input("Hora", (datetime.utcnow() - timedelta(hours=3)).time())

# ======================================================
# AÇÕES
# ======================================================
a, b = st.columns(2)
if a.button("🆕 Nova Avaliação", use_container_width=True):
    st.session_state.atual = {}

if b.button("📂 Abrir Avaliação Existente", use_container_width=True):
    if st.session_state.historico:
        chave = st.selectbox("Selecione", list(st.session_state.historico.keys()))
        st.session_state.atual = copy.deepcopy(st.session_state.historico[chave])

# ======================================================
# UPLOAD
# ======================================================
arquivo = st.file_uploader("Upload do Excel", type=["xlsx"])
if not arquivo:
    st.stop()

xls = pd.ExcelFile(arquivo)
estrutura_pdf = {}

# ======================================================
# PERGUNTAS
# ======================================================
for aba in xls.sheet_names:
    df = xls.parse(aba)

    if aba in st.session_state.atual:
        df = pd.DataFrame(st.session_state.atual[aba]["dados"])
    else:
        df["Resposta"] = "NA"
        df["Justificativa"] = ""

    fase = df.iloc[0]["Fase"]
    grupo = df.iloc[0]["Grupo"]
    codigo = df.iloc[0]["Codigo"]
    descricao = df.iloc[0]["Descricao"]

    nota = media(df)
    cor = semaforo(nota)

    estrutura_pdf.setdefault(fase, {}).setdefault(grupo, []).append({
        "codigo": codigo,
        "descricao": descricao,
        "semaforo": cor,
        "justificativas": {
            "Procedimento": df[(df["Tipo"]=="Procedimento") & (df["Justificativa"]!="")]["Justificativa"].tolist(),
            "Acompanhamento": df[(df["Tipo"]=="Acompanhamento") & (df["Justificativa"]!="")]["Justificativa"].tolist()
        }
    })

    with st.expander(f"{cor} {codigo} – {descricao}", expanded=False):

        for tipo in ["Procedimento", "Acompanhamento"]:
            sub = df[df["Tipo"] == tipo]
            if sub.empty:
                continue

            st.markdown(f"**{tipo}**")
            for i, r in sub.iterrows():
                pergunta = str(r["Pergunta"]) if pd.notna(r["Pergunta"]) else ""
                resp = st.selectbox(
                    pergunta,
                    OPCOES,
                    index=OPCOES.index(r["Resposta"]),
                    key=f"{aba}_{i}"
                )
                df.at[i, "Resposta"] = resp

                if resp in ["Ruim", "Crítico"]:
                    df.at[i, "Justificativa"] = st.text_input(
                        "Justificativa",
                        value=r["Justificativa"],
                        key=f"{aba}_{i}_j"
                    )

    st.session_state.atual[aba] = {"dados": df.to_dict("records")}

# ======================================================
# SALVAR / PDF
# ======================================================
if st.button("💾 Salvar Avaliação"):
    chave = f"{data} {hora.strftime('%H:%M')}"
    st.session_state.historico[chave] = copy.deepcopy(st.session_state.atual)
    salvar(st.session_state.historico)
    st.success("Avaliação salva.")

if st.button("📄 Gerar PDF"):
    cab = {
        "Projeto": projeto,
        "Cliente": cliente,
        "Responsável": responsavel,
        "Data": f"{data} {hora.strftime('%H:%M')}"
    }
    pdf = gerar_pdf(cab, estrutura_pdf)
    st.download_button("⬇️ Download PDF", pdf, "avaliacao.pdf", "application/pdf")
