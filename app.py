import streamlit as st
import pandas as pd
import json
import os
import copy
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import green, yellow, orange, red, grey, black

# =========================
# CONFIG
# =========================
st.set_page_config("Painel Administração Contratual", layout="wide")

AVALIACOES_FILE = "avaliacoes.json"

STATUS_OPCOES = ["NA", "Bom", "Médio", "Ruim", "Crítico"]

STATUS_CORES = {
    "Bom": green,
    "Médio": yellow,
    "Ruim": orange,
    "Crítico": red,
    "NA": grey,
}

STATUS_EMOJI = {
    "Bom": "🟢",
    "Médio": "🟡",
    "Ruim": "🟠",
    "Crítico": "🔴",
    "NA": "⚪",
}

# =========================
# PERSISTÊNCIA
# =========================
def carregar_avaliacoes():
    if os.path.exists(AVALIACOES_FILE):
        with open(AVALIACOES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_avaliacoes(dados):
    with open(AVALIACOES_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# =========================
# STATUS
# =========================
def calcular_status(respostas):
    prioridade = ["Crítico", "Ruim", "Médio", "Bom"]
    for p in prioridade:
        if p in respostas:
            return p
    return "NA"

# =========================
# PDF
# =========================
def gerar_pdf(cab, avaliacao, nome_pdf):
    c = canvas.Canvas(nome_pdf, pagesize=A4)
    largura, altura = A4
    y = altura - 40
    pagina = 1

    def rodape():
        c.setFont("Helvetica", 9)
        c.drawRightString(largura - 40, 20, f"Página {pagina}")

    # CABEÇALHO
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Painel de Administração Contratual")
    y -= 25

    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Projeto: {cab['projeto']}")
    y -= 14
    c.drawString(40, y, f"Cliente: {cab['cliente']}")
    y -= 14
    c.drawString(40, y, f"Responsável: {cab['responsavel']}")
    y -= 14
    c.drawString(40, y, f"Data: {cab['data']}")
    y -= 30

    # RESUMO
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Resumo por Disciplina")
    y -= 20

    for fase, grupos in avaliacao.items():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, f"> {fase}")
        y -= 16

        for grupo, disciplinas in grupos.items():
            c.setFont("Helvetica-Bold", 10)
            c.drawString(60, y, f"> {grupo}")
            y -= 14

            for disc, dados in disciplinas.items():
                status = calcular_status(list(dados["respostas"].values()))

                c.setFillColor(STATUS_CORES[status])
                c.rect(80, y - 4, 8, 8, fill=1)

                c.setFillColor(black)
                c.setFont("Helvetica", 10)
                c.drawString(95, y, f"{disc} – {dados['descricao']}")
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
            for disc, dados in disciplinas.items():
                if not dados["justificativas"]:
                    continue

                status = calcular_status(list(dados["respostas"].values()))

                c.setFillColor(STATUS_CORES[status])
                c.rect(40, y - 4, 8, 8, fill=1)

                c.setFillColor(black)
                c.setFont("Helvetica-Bold", 10)
                c.drawString(55, y, f"{fase} > {grupo} > {disc} – {dados['descricao']}")
                y -= 14

                c.setFont("Helvetica", 10)
                for j in dados["justificativas"]:
                    c.drawString(60, y, f"- {j}")
                    y -= 12

                    if y < 60:
                        rodape()
                        c.showPage()
                        pagina += 1
                        y = altura - 40

    rodape()
    c.save()

# =========================
# STATE
# =========================
if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {}

# =========================
# UI
# =========================
st.title("Painel Administração Contratual")

modo = st.radio("Modo", ["Nova Avaliação", "Abrir Avaliação Existente"], horizontal=True)

# =========================
# CABEÇALHO
# =========================
st.subheader("Cabeçalho")

cab = {
    "projeto": st.text_input("Projeto"),
    "cliente": st.text_input("Cliente"),
    "responsavel": st.text_input("Responsável"),
    "data": st.date_input("Data").strftime("%d/%m/%Y"),
}

# =========================
# ABRIR AVALIAÇÃO EXISTENTE
# =========================
if modo == "Abrir Avaliação Existente":
    chaves = list(st.session_state.avaliacoes.keys())
    if not chaves:
        st.info("Nenhuma avaliação salva.")
        st.stop()

    chave = st.selectbox("Selecione", chaves)

    # 🔴 CORREÇÃO: deep copy REAL
    st.session_state.avaliacao_atual = copy.deepcopy(st.session_state.avaliacoes[chave]["dados"])

    st.success("Avaliação carregada com sucesso.")
else:
    st.session_state.avaliacao_atual = {}

# =========================
# UPLOAD EXCEL
# =========================
uploaded = st.file_uploader("Upload do Excel", type="xlsx")
if not uploaded:
    st.stop()

xls = pd.ExcelFile(uploaded)

# =========================
# MONTAGEM
# =========================
avaliacao = st.session_state.avaliacao_atual or {}

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

        bloco = avaliacao[fase][grupo][codigo]

# =========================
# TELA DE PERGUNTAS
# =========================
for fase, grupos in avaliacao.items():
    with st.expander(f"📌 {fase}", expanded=True):
        for grupo, disciplinas in grupos.items():
            with st.expander(f"📂 {grupo}", expanded=True):
                for codigo, dados in disciplinas.items():

                    status = calcular_status(list(dados["respostas"].values()))

                    with st.expander(f"{STATUS_EMOJI[status]} {codigo} – {dados['descricao']}"):
                        for tipo in ["Procedimento", "Acompanhamento"]:
                            st.markdown(f"### {tipo}")

                            df = xls.parse(codigo)
                            df = df[df["Tipo"] == tipo]

                            for _, r in df.iterrows():
                                key = f"{fase}_{grupo}_{codigo}_{r['Pergunta']}"

                                resp = st.selectbox(
                                    r["Pergunta"],
                                    STATUS_OPCOES,
                                    index=0,
                                    key=key
                                )

                                dados["respostas"][r["Pergunta"]] = resp

                                if resp in ["Ruim", "Crítico"]:
                                    j = st.text_input("Justificativa", key=f"{key}_j")
                                    if j and j not in dados["justificativas"]:
                                        dados["justificativas"].append(j)

st.session_state.avaliacao_atual = avaliacao

# =========================
# BOTÕES
# =========================
if st.button("💾 Salvar Avaliação"):
    chave = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.session_state.avaliacoes[chave] = {
        "cabecalho": cab,
        "dados": copy.deepcopy(avaliacao)
    }
    salvar_avaliacoes(st.session_state.avaliacoes)
    st.success("Avaliação salva com sucesso.")

if st.button("📄 Gerar PDF"):
    gerar_pdf(cab, avaliacao, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF", f, "avaliacao.pdf")
