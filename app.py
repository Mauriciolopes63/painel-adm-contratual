import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from io import BytesIO
import copy

# ======================================================
# CONFIG
# ======================================================
st.set_page_config("Painel Administração Contratual", layout="wide")
AVALIACOES_FILE = "avaliacoes.json"

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
def carregar_avaliacoes():
    if os.path.exists(AVALIACOES_FILE):
        with open(AVALIACOES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_avaliacoes(dados):
    with open(AVALIACOES_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# ======================================================
# CÁLCULO
# ======================================================
def media_ponderada(df):
    dfv = df[df["Resposta"] != "NA"].copy()
    if dfv.empty:
        return None
    dfv["valor"] = dfv["Resposta"].map(VALORES)
    return (dfv["valor"] * dfv["Peso"]).sum() / dfv["Peso"].sum()

def semaforo(nota):
    if nota is None:
        return "⚪"
    if nota <= 0.25: return "🟢"
    if nota <= 0.50: return "🟡"
    if nota < 0.75:  return "🟠"
    return "🔴"

# ======================================================
# PDF
# ======================================================
def gerar_pdf(cabecalho, estrutura):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    pagina = 1

    def rodape():
        c.setFont("Helvetica", 8)
        c.drawRightString(w - 40, 20, f"Página {pagina}")

    # -------- CAPA --------
    y = h - 60
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "PAINEL DE ADMINISTRAÇÃO CONTRATUAL")
    y -= 40

    c.setFont("Helvetica", 11)
    for k, v in cabecalho.items():
        c.drawString(40, y, f"{k}: {v}")
        y -= 20

    rodape()
    c.showPage()
    pagina += 1

    # -------- RESUMO --------
    y = h - 50
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Resumo por Fase, Grupo e Disciplina")
    y -= 30

    for fase, grupos in estrutura.items():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, fase)
        y -= 20

        for grupo, disciplinas in grupos.items():
            c.setFont("Helvetica-Bold", 10)
            c.drawString(60, y, grupo)
            y -= 20

            for d in disciplinas:
                c.setFillColor(CORES[d["semaforo"]])
                c.rect(80, y - 10, 10, 10, fill=1)
                c.setFillColor(colors.black)
                c.drawString(100, y - 10, f"{d['codigo']} – {d['descricao']}")
                y -= 15

                if y < 60:
                    rodape()
                    c.showPage()
                    pagina += 1
                    y = h - 50

    rodape()
    c.showPage()
    pagina += 1

    # -------- JUSTIFICATIVAS --------
    y = h - 50
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Justificativas")
    y -= 30

    for fase, grupos in estrutura.items():
        for grupo, disciplinas in grupos.items():
            for d in disciplinas:
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
                        y -= 15
                        c.setFont("Helvetica", 9)
                        for t in textos:
                            c.drawString(80, y, f"- {t}")
                            y -= 12

                y -= 10
                if y < 60:
                    rodape()
                    c.showPage()
                    pagina += 1
                    y = h - 50

    rodape()
    c.save()
    buf.seek(0)
    return buf

# ======================================================
# ESTADO
# ======================================================
if "historico" not in st.session_state:
    st.session_state.historico = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {}

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
colA, colB = st.columns(2)
nova = colA.button("🆕 Nova Avaliação", use_container_width=True)
abrir = colB.button("📂 Abrir Avaliação Existente", use_container_width=True)

if nova:
    st.session_state.avaliacao_atual = {}

if abrir and st.session_state.historico:
    chave = st.selectbox("Selecione a avaliação", list(st.session_state.historico.keys()))
    st.session_state.avaliacao_atual = copy.deepcopy(st.session_state.historico[chave])

# ======================================================
# UPLOAD
# ======================================================
uploaded = st.file_uploader("Upload Excel", type=["xlsx"])
if not uploaded:
    st.stop()

xls = pd.ExcelFile(uploaded)

estrutura_pdf = {}

# ======================================================
# CANVAS
# ======================================================
for aba in xls.sheet_names:
    df = xls.parse(aba)

    if aba in st.session_state.avaliacao_atual:
        df = pd.DataFrame(st.session_state.avaliacao_atual[aba]["dados"])
    else:
        df["Resposta"] = "NA"
        df["Justificativa"] = ""

    fase = df.iloc[0]["Fase"]
    grupo = df.iloc[0]["Grupo"]
    codigo = df.iloc[0]["Codigo"]
    descricao = df.iloc[0]["Descricao"]

    proc = df[df["Tipo"] == "Procedimento"]
    acomp = df[df["Tipo"] == "Acompanhamento"]

    nota = media_ponderada(df)
    cor = semaforo(nota)

    estrutura_pdf.setdefault(fase, {}).setdefault(grupo, []).append({
        "codigo": codigo,
        "descricao": descricao,
        "semaforo": cor,
        "justificativas": {
            "Procedimento": proc[proc["Justificativa"] != ""]["Justificativa"].tolist(),
            "Acompanhamento": acomp[acomp["Justificativa"] != ""]["Justificativa"].tolist()
        }
    })

    with st.expander(f"{cor} {codigo} – {descricao}"):
        for i, r in df.iterrows():
            resp = st.selectbox(
                r["Pergunta"],
                ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                index=["Bom", "Médio", "Ruim", "Crítico", "NA"].index(r["Resposta"]),
                key=f"{aba}_{i}"
            )
            df.at[i, "Resposta"] = resp
            if resp in ["Ruim", "Crítico"]:
                df.at[i, "Justificativa"] = st.text_input(
                    "Justificativa",
                    value=r["Justificativa"],
                    key=f"{aba}_{i}_j"
                )

    st.session_state.avaliacao_atual[aba] = {
        "dados": df.to_dict(orient="records")
    }

# ======================================================
# SALVAR / PDF
# ======================================================
if st.button("💾 Salvar Avaliação"):
    chave = f"{data} {hora.strftime('%H:%M')}"
    st.session_state.historico[chave] = copy.deepcopy(st.session_state.avaliacao_atual)
    salvar_avaliacoes(st.session_state.historico)
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
