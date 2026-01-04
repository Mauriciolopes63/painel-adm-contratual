import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import green, yellow, orange, red, grey, black

# =====================================================
# CONFIG
# =====================================================
st.set_page_config("Painel Administração Contratual", layout="wide")

AVALIACOES_FILE = "avaliacoes.json"

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
# STATUS DA DISCIPLINA
# =====================================================
def calcular_status(respostas):
    prioridade = ["Crítico", "Ruim", "Médio", "Bom"]
    for p in prioridade:
        if p in respostas.values():
            return p
    return "NA"

# =====================================================
# PDF
# =====================================================
def gerar_pdf(cab, avaliacao, nome_pdf):
    c = canvas.Canvas(nome_pdf, pagesize=A4)
    largura, altura = A4
    y = altura - 40
    pagina = 1

    def nova_pagina():
        nonlocal y, pagina
        c.setFont("Helvetica", 9)
        c.drawRightString(largura - 40, 20, f"Página {pagina}")
        c.showPage()
        pagina += 1
        y = altura - 40

    # Cabeçalho
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
    c.drawString(40, y, f"Data: {cab['data']} {cab['hora']}")
    y -= 30

    # Resumo
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Resumo Geral")
    y -= 20

    for fase, grupos in avaliacao.items():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, f"> {fase}")
        y -= 16

        for grupo, disciplinas in grupos.items():
            c.setFont("Helvetica-Bold", 10)
            c.drawString(60, y, f"> {grupo}")
            y -= 14

            for cod, d in disciplinas.items():
                status = calcular_status(d["respostas"])
                c.setFillColor(STATUS_CORES[status])
                c.rect(80, y - 6, 10, 10, fill=1)
                c.setFillColor(black)
                c.drawString(100, y, f"{cod} – {d['descricao']}")
                y -= 14

                if y < 60:
                    nova_pagina()

    nova_pagina()

    # Justificativas
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Justificativas")
    y -= 20

    for fase, grupos in avaliacao.items():
        for grupo, disciplinas in grupos.items():
            for cod, d in disciplinas.items():
                justificativas = [j for j in d["justificativas"].values() if j.strip()]
                if not justificativas:
                    continue

                status = calcular_status(d["respostas"])
                c.setFillColor(STATUS_CORES[status])
                c.rect(40, y - 6, 10, 10, fill=1)
                c.setFillColor(black)

                c.setFont("Helvetica-Bold", 10)
                c.drawString(55, y, f"{fase} > {grupo} > {cod} – {d['descricao']}")
                y -= 14

                c.setFont("Helvetica", 10)
                for j in justificativas:
                    c.drawString(60, y, f"- {j}")
                    y -= 12
                    if y < 60:
                        nova_pagina()

    c.setFont("Helvetica", 9)
    c.drawRightString(largura - 40, 20, f"Página {pagina}")
    c.save()

# =====================================================
# ESTADO
# =====================================================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {}

# =====================================================
# INTERFACE
# =====================================================
st.title("Painel Administração Contratual")

modo = st.radio("Modo", ["Nova Avaliação", "Abrir Avaliação Existente"], horizontal=True)

# Cabeçalho
st.subheader("Cabeçalho")
cab_projeto = st.text_input("Projeto")
cab_cliente = st.text_input("Cliente")
cab_resp = st.text_input("Responsável")

cab_data = st.date_input("Data", datetime.now().date())
cab_hora = st.time_input("Hora", (datetime.utcnow() - timedelta(hours=3)).time())

# Abrir avaliação
if modo == "Abrir Avaliação Existente":
    chaves = list(st.session_state.avaliacoes_por_data.keys())
    if not chaves:
        st.info("Nenhuma avaliação salva.")
        st.stop()
    chave = st.selectbox("Selecione", chaves)
    st.session_state.avaliacao_atual = json.loads(
        json.dumps(st.session_state.avaliacoes_por_data[chave])
    )

# Upload Excel
uploaded = st.file_uploader("Upload do Excel", type="xlsx")
if not uploaded:
    st.stop()

xls = pd.ExcelFile(uploaded)

if modo == "Nova Avaliação":
    st.session_state.avaliacao_atual = {}

# Inicialização
for aba in xls.sheet_names:
    df = xls.parse(aba)
    codigo = df.iloc[0]["Codigo"]
    descricao = df.iloc[0]["Descricao"]

    for _, r in df.iterrows():
        pergunta = r["Pergunta"]
        if pd.isna(pergunta) or str(pergunta).strip() == "":
            continue

        fase = r["Fase"]
        grupo = r["Grupo"]

        st.session_state.avaliacao_atual.setdefault(fase, {})
        st.session_state.avaliacao_atual[fase].setdefault(grupo, {})
        st.session_state.avaliacao_atual[fase][grupo].setdefault(
            codigo,
            {"descricao": descricao, "respostas": {}, "justificativas": {}}
        )

        st.session_state.avaliacao_atual[fase][grupo][codigo]["respostas"].setdefault(pergunta, "NA")
        st.session_state.avaliacao_atual[fase][grupo][codigo]["justificativas"].setdefault(pergunta, "")

# Tela de perguntas
for fase, grupos in st.session_state.avaliacao_atual.items():
    with st.expander(f"> {fase}", True):
        for grupo, disciplinas in grupos.items():
            with st.expander(f"> {grupo}", True):
                for cod, d in disciplinas.items():
                    status = calcular_status(d["respostas"])
                    with st.expander(f"{STATUS_EMOJI[status]} {cod} – {d['descricao']}"):
                        base = pd.concat([xls.parse(a) for a in xls.sheet_names])
                        base = base[base["Codigo"] == cod]

                        for tipo in ["Procedimento", "Acompanhamento"]:
                            bloco = base[base["Tipo"] == tipo]
                            if bloco.empty:
                                continue

                            st.markdown(f"**{tipo}**")
                            for _, r in bloco.iterrows():
                                pergunta = r["Pergunta"]
                                if pd.isna(pergunta) or str(pergunta).strip() == "":
                                    continue

                                key = f"{fase}|{grupo}|{cod}|{pergunta}"
                                resp = st.selectbox(
                                    pergunta,
                                    STATUS_OPCOES,
                                    index=STATUS_OPCOES.index(d["respostas"][pergunta]),
                                    key=key
                                )
                                d["respostas"][pergunta] = resp

                                if resp in ["Ruim", "Crítico"]:
                                    j = st.text_input(
                                        "Justificativa",
                                        value=d["justificativas"][pergunta],
                                        key=f"{key}_j"
                                    )
                                    d["justificativas"][pergunta] = j
                                else:
                                    d["justificativas"][pergunta] = ""

# Salvar / PDF
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{cab_data} {cab_hora.strftime('%H:%M')}"
    st.session_state.avaliacoes_por_data[chave] = st.session_state.avaliacao_atual
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success("Avaliação salva.")

if st.button("📄 Gerar PDF"):
    cab = {
        "projeto": cab_projeto,
        "cliente": cab_cliente,
        "responsavel": cab_resp,
        "data": str(cab_data),
        "hora": cab_hora.strftime("%H:%M")
    }
    gerar_pdf(cab, st.session_state.avaliacao_atual, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF", f, "avaliacao.pdf")
