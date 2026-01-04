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
# CONFIGURAÇÕES
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
# FUNÇÕES AUXILIARES
# =====================================================
def carregar_avaliacoes():
    if os.path.exists(ARQUIVO_AVALIACOES):
        with open(ARQUIVO_AVALIACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_avaliacoes(dados):
    with open(ARQUIVO_AVALIACOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

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

    # Cabeçalho
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Painel de Administração Contratual")
    y -= 20

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

            for cod, dados in disciplinas.items():
                status = calcular_status(dados["respostas"])
                c.setFillColor(STATUS_CORES[status])
                c.rect(80, y - 4, 8, 8, fill=1)
                c.setFillColor(black)
                c.drawString(95, y, f"{cod} - {dados['descricao']}")
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

    # Justificativas
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Justificativas")
    y -= 20

    for fase, grupos in avaliacao.items():
        for grupo, disciplinas in grupos.items():
            for cod, dados in disciplinas.items():
                if not dados["justificativas"]:
                    continue

                status = calcular_status(dados["respostas"])
                c.setFillColor(STATUS_CORES[status])
                c.rect(40, y - 4, 8, 8, fill=1)
                c.setFillColor(black)
                c.setFont("Helvetica-Bold", 10)
                c.drawString(55, y, f"{fase} > {grupo} > {cod}")
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
cab_responsavel = st.text_input("Responsável")
cab_data = st.date_input("Data", datetime.now().date())
cab_hora = st.time_input("Hora", (datetime.utcnow() - timedelta(hours=3)).time())

# =====================================================
# ABRIR AVALIAÇÃO EXISTENTE (CORRIGIDO)
# =====================================================
if modo == "Abrir Avaliação Existente":
    chaves = list(st.session_state.avaliacoes_por_data.keys())
    if not chaves:
        st.info("Nenhuma avaliação salva.")
        st.stop()

    chave_sel = st.selectbox("Selecione a avaliação", chaves)

    # 🔴 CLONE PROFUNDO — NÃO SOBRESCREVE OUTRAS
    st.session_state.avaliacao_atual = deepcopy(
        st.session_state.avaliacoes_por_data[chave_sel]
    )

# =====================================================
# UPLOAD EXCEL
# =====================================================
arquivo = st.file_uploader("Upload do Excel", type="xlsx")
if not arquivo:
    st.stop()

xls = pd.ExcelFile(arquivo)

# =====================================================
# LEITURA DO EXCEL
# =====================================================
for aba in xls.sheet_names:
    df = xls.parse(aba)

    codigo = str(df.iloc[0]["Codigo"])
    descricao = str(df.iloc[0]["Descricao"])

    for _, r in df.iterrows():
        fase = str(r["Fase"])
        grupo = str(r["Grupo"])

        st.session_state.avaliacao_atual.setdefault(fase, {})
        st.session_state.avaliacao_atual[fase].setdefault(grupo, {})
        st.session_state.avaliacao_atual[fase][grupo].setdefault(
            codigo,
            {"descricao": descricao, "respostas": [], "justificativas": []}
        )

# =====================================================
# TELAS DE PERGUNTAS
# =====================================================
for fase, grupos in st.session_state.avaliacao_atual.items():
    with st.expander(f"> {fase}", expanded=True):
        for grupo, disciplinas in grupos.items():
            with st.expander(f"> {grupo}", expanded=True):
                for cod, dados in disciplinas.items():
                    status = calcular_status(dados["respostas"])
                    with st.expander(f"{STATUS_EMOJI[status]} {cod} - {dados['descricao']}"):
                        for aba in xls.sheet_names:
                            base = xls.parse(aba)
                            base = base[base["Codigo"].astype(str) == cod]

                            for tipo in ["Procedimento", "Acompanhamento"]:
                                bloco = base[base["Tipo"] == tipo]
                                if bloco.empty:
                                    continue

                                st.markdown(f"**{tipo}**")
                                for i, r in bloco.iterrows():
                                    chave = f"{fase}_{grupo}_{cod}_{i}"
                                    resp = st.selectbox(
                                        r["Pergunta"],
                                        STATUS_OPCOES,
                                        key=chave
                                    )

                                    if resp != "NA":
                                        dados["respostas"].append(resp)

                                    if resp in ["Ruim", "Crítico"]:
                                        j = st.text_input(
                                            "Justificativa",
                                            key=f"{chave}_j"
                                        )
                                        if j:
                                            dados["justificativas"].append(j)

# =====================================================
# SALVAR / PDF
# =====================================================
if st.button("💾 Salvar Avaliação"):
    chave = f"{cab_data} {cab_hora.strftime('%H:%M')}"
    st.session_state.avaliacoes_por_data[chave] = deepcopy(
        st.session_state.avaliacao_atual
    )
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success("Avaliação salva corretamente.")

if st.button("📄 Gerar PDF"):
    cab = {
        "projeto": cab_projeto,
        "cliente": cab_cliente,
        "responsavel": cab_responsavel,
        "data": str(cab_data),
        "hora": cab_hora.strftime("%H:%M")
    }

    gerar_pdf(cab, st.session_state.avaliacao_atual, "avaliacao.pdf")

    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF", f, "avaliacao.pdf")
