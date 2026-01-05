import streamlit as st
import pandas as pd
import json
import os
import copy
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import green, yellow, orange, red, grey, black
from reportlab.lib.utils import ImageReader

# =====================================================
# CONFIG
# =====================================================
st.set_page_config("Painel Administração Contratual", layout="wide")

AVALIACOES_FILE = "avaliacoes.json"
LOGO_M2L = "assets/logo_m2l.png"

STATUS_OPCOES = ["NA", "Bom", "Médio", "Ruim", "Crítico"]

STATUS_CORES = {
    "Bom": green,
    "Médio": yellow,
    "Ruim": orange,
    "Crítico": red,
    "NA": grey
}

STATUS_EMOJI = {
    "Bom": "🟢",
    "Médio": "🟡",
    "Ruim": "🟠",
    "Crítico": "🔴",
    "NA": "⚪"
}

# =====================================================
# PERSISTÊNCIA
# =====================================================
def carregar_avaliacoes():
    if os.path.exists(AVALIACOES_FILE):
        with open(AVALIACOES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_avaliacoes(dados):
    with open(AVALIACOES_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# =====================================================
# STATUS
# =====================================================
def calcular_status(respostas):
    prioridade = ["Crítico", "Ruim", "Médio", "Bom"]
    for p in prioridade:
        if p in respostas:
            return p
    return "NA"

# =====================================================
# PDF
# =====================================================
def gerar_pdf(cab, avaliacao, nome_pdf):
    c = canvas.Canvas(nome_pdf, pagesize=A4)
    largura, altura = A4
    pagina = 1
    y = altura - 40

    def rodape():
        c.setFont("Helvetica", 9)
        c.drawRightString(largura - 40, 20, f"Página {pagina}")

    # LOGOS
    if os.path.exists(LOGO_M2L):
        c.drawImage(ImageReader(LOGO_M2L), 40, altura - 80, width=100, preserveAspectRatio=True)

    if cab.get("logo_cliente") and os.path.exists(cab["logo_cliente"]):
        c.drawImage(ImageReader(cab["logo_cliente"]), largura - 160, altura - 80, width=120, preserveAspectRatio=True)

    # CABEÇALHO
    y -= 60
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Painel de Administração Contratual")
    y -= 20

    c.setFont("Helvetica", 10)
    for k in ["Projeto", "Cliente", "Responsável", "Data"]:
        c.drawString(40, y, f"{k}: {cab[k.lower()]}")
        y -= 14

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Resumo por Disciplina")
    y -= 20

    # RESUMO
    for fase, grupos in avaliacao.items():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, f"> {fase}")
        y -= 16

        for grupo, disciplinas in grupos.items():
            c.setFont("Helvetica-Bold", 10)
            c.drawString(60, y, f"> {grupo}")
            y -= 14

            for cod, d in disciplinas.items():
                status = calcular_status(list(d["respostas"].values()))
                c.setFillColor(STATUS_CORES[status])
                c.rect(80, y - 4, 8, 8, fill=1)
                c.setFillColor(black)
                c.drawString(95, y, f"{cod} - {d['descricao']}")
                y -= 14

                if y < 60:
                    rodape()
                    c.showPage()
                    pagina += 1
                    y = altura - 40

    rodape()
    c.showPage()
    pagina += 1
    y = altura - 40

    # JUSTIFICATIVAS
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Justificativas")
    y -= 20

    for fase, grupos in avaliacao.items():
        for grupo, disciplinas in grupos.items():
            for cod, d in disciplinas.items():
                if not d["justificativas"]:
                    continue

                status = calcular_status(list(d["respostas"].values()))
                c.setFillColor(STATUS_CORES[status])
                c.rect(40, y - 4, 8, 8, fill=1)
                c.setFillColor(black)

                c.setFont("Helvetica-Bold", 10)
                c.drawString(55, y, f"{fase} > {grupo} > {cod} - {d['descricao']}")
                y -= 14

                c.setFont("Helvetica", 10)
                for j in d["justificativas"]:
                    c.drawString(60, y, f"- {j}")
                    y -= 12
                    if y < 60:
                        rodape()
                        c.showPage()
                        pagina += 1
                        y = altura - 40

    rodape()
    c.save()

# =====================================================
# SESSION STATE
# =====================================================
if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {}

# =====================================================
# UI
# =====================================================
st.title("Painel Administração Contratual")

modo = st.radio("Modo", ["Nova Avaliação", "Abrir Avaliação Existente"], horizontal=True)

# =====================================================
# CABEÇALHO
# =====================================================
st.subheader("Cabeçalho")

cab = {
    "projeto": st.text_input("Projeto"),
    "cliente": st.text_input("Cliente"),
    "responsável": st.text_input("Responsável"),
    "data": st.date_input("Data").strftime("%d/%m/%Y"),
}

logo_cliente = st.file_uploader("Logo do Cliente (opcional)", type=["png", "jpg"])
if logo_cliente:
    os.makedirs("assets", exist_ok=True)
    path = f"assets/logo_cliente_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    with open(path, "wb") as f:
        f.write(logo_cliente.getbuffer())
    cab["logo_cliente"] = path
else:
    cab["logo_cliente"] = None

# =====================================================
# ABRIR AVALIAÇÃO
# =====================================================
if modo == "Abrir Avaliação Existente":
    chaves = list(st.session_state.avaliacoes.keys())
    chave = st.selectbox("Avaliações salvas", chaves)
    st.session_state.avaliacao_atual = copy.deepcopy(st.session_state.avaliacoes[chave])
    st.stop()

# =====================================================
# UPLOAD EXCEL
# =====================================================
uploaded = st.file_uploader("Upload do Excel", type="xlsx")
if not uploaded:
    st.stop()

xls = pd.ExcelFile(uploaded)

# =====================================================
# MONTAGEM DA AVALIAÇÃO
# =====================================================
avaliacao = {}

for aba in xls.sheet_names:
    df = xls.parse(aba)

    codigo = df.iloc[0]["Codigo"]
    descricao = df.iloc[0]["Descricao"]

    for _, r in df.iterrows():
        fase = r["Fase"]
        grupo = r["Grupo"]
        tipo = r["Tipo"]
        pergunta = r["Pergunta"]

        avaliacao.setdefault(fase, {})
        avaliacao[fase].setdefault(grupo, {})
        avaliacao[fase][grupo].setdefault(codigo, {
            "descricao": descricao,
            "respostas": {},
            "justificativas": []
        })

        key = f"{fase}_{grupo}_{codigo}_{pergunta}"
        resp = st.selectbox(pergunta, STATUS_OPCOES, index=0, key=key)

        if resp != "NA":
            avaliacao[fase][grupo][codigo]["respostas"][pergunta] = resp

        if resp in ["Ruim", "Crítico"]:
            j = st.text_input("Justificativa", key=f"{key}_j")
            if j:
                if j not in avaliacao[fase][grupo][codigo]["justificativas"]:
                    avaliacao[fase][grupo][codigo]["justificativas"].append(j)

st.session_state.avaliacao_atual = avaliacao

# =====================================================
# AÇÕES
# =====================================================
if st.button("💾 Salvar Avaliação"):
    chave = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.avaliacoes[chave] = {
        "cabecalho": cab,
        "dados": copy.deepcopy(avaliacao)
    }
    salvar_avaliacoes(st.session_state.avaliacoes)
    st.success("Avaliação salva com sucesso")

if st.button("📄 Gerar PDF"):
    gerar_pdf(cab, avaliacao, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF", f, "avaliacao.pdf")
