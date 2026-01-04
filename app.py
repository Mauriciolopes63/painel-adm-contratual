import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from copy import deepcopy

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import green, yellow, orange, red, grey, black

# =====================================================
# CONFIGURAÇÃO
# =====================================================
st.set_page_config("Painel Administração Contratual", layout="wide")

ARQUIVO_AVALIACOES = "avaliacoes.json"

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
    if os.path.exists(ARQUIVO_AVALIACOES):
        with open(ARQUIVO_AVALIACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_avaliacoes(dados):
    with open(ARQUIVO_AVALIACOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# =====================================================
# STATUS (SEMAFORO)
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
    y = altura - 40
    pagina = 1

    def nova_pagina():
        nonlocal y, pagina
        c.setFont("Helvetica", 9)
        c.drawRightString(largura - 40, 20, f"Página {pagina}")
        c.showPage()
        pagina += 1
        y = altura - 40

    # CABEÇALHO
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Painel de Administração Contratual")
    y -= 20

    c.setFont("Helvetica", 10)
    for k, v in cab.items():
        c.drawString(40, y, f"{k}: {v}")
        y -= 14

    y -= 10

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

            for cod, d in disciplinas.items():
                status = calcular_status([r["resposta"] for r in d["respostas"].values()])
                c.setFillColor(STATUS_CORES[status])
                c.rect(80, y - 4, 8, 8, fill=1)
                c.setFillColor(black)
                c.drawString(95, y, f"{cod} – {d['descricao']}")
                y -= 14

                if y < 60:
                    nova_pagina()

    nova_pagina()

    # JUSTIFICATIVAS
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Justificativas")
    y -= 20

    for fase, grupos in avaliacao.items():
        for grupo, disciplinas in grupos.items():
            for cod, d in disciplinas.items():
                itens = [
                    r for r in d["respostas"].values()
                    if r["justificativa"]
                ]
                if not itens:
                    continue

                status = calcular_status([r["resposta"] for r in itens])
                c.setFillColor(STATUS_CORES[status])
                c.rect(40, y - 4, 8, 8, fill=1)
                c.setFillColor(black)

                c.setFont("Helvetica-Bold", 10)
                c.drawString(55, y, f"{fase} > {grupo} > {cod} – {d['descricao']}")
                y -= 14

                c.setFont("Helvetica", 10)
                for r in itens:
                    c.drawString(60, y, f"- {r['justificativa']}")
                    y -= 12
                    if y < 60:
                        nova_pagina()

    c.save()

# =====================================================
# ESTADO
# =====================================================
if "avaliacoes_salvas" not in st.session_state:
    st.session_state.avaliacoes_salvas = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {}

# =====================================================
# INTERFACE
# =====================================================
st.title("Painel Administração Contratual")

modo = st.radio("Modo", ["Nova Avaliação", "Abrir Avaliação Existente"], horizontal=True)

# =====================================================
# CABEÇALHO
# =====================================================
st.subheader("Cabeçalho")

cab = {
    "Projeto": st.text_input("Projeto"),
    "Cliente": st.text_input("Cliente"),
    "Responsável": st.text_input("Responsável"),
    "Data": str(st.date_input("Data", datetime.now().date())),
    "Hora": st.time_input(
        "Hora",
        (datetime.utcnow() - timedelta(hours=3)).time()
    ).strftime("%H:%M")
}

# =====================================================
# ABRIR AVALIAÇÃO
# =====================================================
if modo == "Abrir Avaliação Existente":
    chaves = list(st.session_state.avaliacoes_salvas.keys())
    chave = st.selectbox("Selecione a avaliação", chaves)
    st.session_state.avaliacao_atual = deepcopy(
        st.session_state.avaliacoes_salvas[chave]
    )

# =====================================================
# UPLOAD
# =====================================================
arquivo = st.file_uploader("Upload do Excel", type="xlsx")
if not arquivo:
    st.stop()

xls = pd.ExcelFile(arquivo)

# =====================================================
# CRIA ESTRUTURA (SÓ NA NOVA)
# =====================================================
if modo == "Nova Avaliação":
    st.session_state.avaliacao_atual = {}

    for aba in xls.sheet_names:
        df = xls.parse(aba)

        codigo = df.iloc[0]["Codigo"]
        descricao = df.iloc[0]["Descricao"]

        for _, r in df.iterrows():
            fase = r["Fase"]
            grupo = r["Grupo"]
            pergunta = r["Pergunta"]

            st.session_state.avaliacao_atual \
                .setdefault(fase, {}) \
                .setdefault(grupo, {}) \
                .setdefault(codigo, {
                    "descricao": descricao,
                    "respostas": {}
                })

            st.session_state.avaliacao_atual[fase][grupo][codigo]["respostas"][pergunta] = {
                "resposta": "NA",
                "justificativa": ""
            }

# =====================================================
# TELA DE PERGUNTAS
# =====================================================
for fase, grupos in st.session_state.avaliacao_atual.items():
    with st.expander(f"▶ {fase}", expanded=True):
        for grupo, disciplinas in grupos.items():
            with st.expander(f"▶ {grupo}", expanded=True):
                for codigo, d in disciplinas.items():
                    respostas = [r["resposta"] for r in d["respostas"].values()]
                    status = calcular_status(respostas)

                    with st.expander(
                        f"{STATUS_EMOJI[status]} {codigo} – {d['descricao']}",
                        expanded=False
                    ):
                        for aba in xls.sheet_names:
                            base = xls.parse(aba)
                            base = base[base["Codigo"] == codigo]

                            for tipo in ["Procedimento", "Acompanhamento"]:
                                bloco = base[base["Tipo"] == tipo]
                                if bloco.empty:
                                    continue

                                st.markdown(f"**{tipo}**")

                                for _, r in bloco.iterrows():
                                    key = f"{codigo}_{r['Pergunta']}"

                                    resp = st.selectbox(
                                        r["Pergunta"],
                                        STATUS_OPCOES,
                                        index=STATUS_OPCOES.index(
                                            d["respostas"][r["Pergunta"]]["resposta"]
                                        ),
                                        key=key
                                    )

                                    d["respostas"][r["Pergunta"]]["resposta"] = resp

                                    if resp in ["Ruim", "Crítico"]:
                                        j = st.text_input(
                                            "Justificativa",
                                            value=d["respostas"][r["Pergunta"]]["justificativa"],
                                            key=f"{key}_j"
                                        )
                                        d["respostas"][r["Pergunta"]]["justificativa"] = j

# =====================================================
# AÇÕES
# =====================================================
if st.button("💾 Salvar Avaliação"):
    chave = f"{cab['Data']} {cab['Hora']}"
    st.session_state.avaliacoes_salvas[chave] = deepcopy(st.session_state.avaliacao_atual)
    salvar_avaliacoes(st.session_state.avaliacoes_salvas)
    st.success("Avaliação salva com sucesso.")

if st.button("📄 Gerar PDF"):
    gerar_pdf(cab, st.session_state.avaliacao_atual, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF", f, "avaliacao.pdf")
