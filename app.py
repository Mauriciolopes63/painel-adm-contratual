import streamlit as st
import pandas as pd
import json
import os
import copy
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
# STATUS / SEMÁFORO
# =====================================================
def calcular_status(respostas_dict):
    prioridade = ["Crítico", "Ruim", "Médio", "Bom"]
    for p in prioridade:
        if p in respostas_dict.values():
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

    # CABEÇALHO
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

    # RESUMO
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

            for cod, disc in disciplinas.items():
                status = calcular_status(disc["respostas"])
                c.setFillColor(STATUS_CORES[status])
                c.rect(80, y - 4, 8, 8, fill=1)
                c.setFillColor(black)
                c.drawString(95, y, f"{cod} – {disc['descricao']}")
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
            for cod, disc in disciplinas.items():
                if not disc["justificativas"]:
                    continue

                status = calcular_status(disc["respostas"])
                c.setFillColor(STATUS_CORES[status])
                c.rect(40, y - 4, 8, 8, fill=1)
                c.setFillColor(black)

                c.setFont("Helvetica-Bold", 10)
                c.drawString(55, y, f"{fase} > {grupo} > {cod} – {disc['descricao']}")
                y -= 14

                c.setFont("Helvetica", 10)
                for j in disc["justificativas"]:
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
# ESTADO GLOBAL
# =====================================================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {}

# =====================================================
# INTERFACE
# =====================================================
st.title("Painel Administração Contratual")

modo = st.radio(
    "Modo",
    ["Nova Avaliação", "Abrir Avaliação Existente"],
    horizontal=True
)

# =====================================================
# CABEÇALHO
# =====================================================
st.subheader("Cabeçalho da Avaliação")

projeto = st.text_input("Nome do Projeto")
cliente = st.text_input("Cliente")
responsavel = st.text_input("Responsável")

data = st.date_input("Data", datetime.now().date())
hora = st.time_input("Hora", (datetime.utcnow() - timedelta(hours=3)).time())

# =====================================================
# ABRIR AVALIAÇÃO (CORRIGIDO DEFINITIVAMENTE)
# =====================================================
if modo == "Abrir Avaliação Existente":
    chaves = list(st.session_state.avaliacoes_por_data.keys())

    if not chaves:
        st.info("Nenhuma avaliação salva.")
        st.stop()

    chave = st.selectbox("Selecione a avaliação", chaves)

    # 🔥 CORREÇÃO DEFINITIVA
    st.session_state.avaliacao_atual = copy.deepcopy(
        st.session_state.avaliacoes_por_data[chave]
    )

# =====================================================
# UPLOAD EXCEL
# =====================================================
uploaded = st.file_uploader("Upload do Excel do Projeto", type="xlsx")
if not uploaded:
    st.stop()

xls = pd.ExcelFile(uploaded)

# =====================================================
# INICIALIZAÇÃO (SÓ SE NOVA)
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

            st.session_state.avaliacao_atual.setdefault(fase, {})
            st.session_state.avaliacao_atual[fase].setdefault(grupo, {})
            st.session_state.avaliacao_atual[fase][grupo].setdefault(codigo, {
                "descricao": descricao,
                "respostas": {},
                "justificativas": []
            })

# =====================================================
# TELAS DE PERGUNTAS
# =====================================================
st.subheader("Avaliação")

for fase, grupos in st.session_state.avaliacao_atual.items():
    with st.expander(f"> {fase}", expanded=True):

        for grupo, disciplinas in grupos.items():
            with st.expander(f"> {grupo}", expanded=True):

                for cod, disc in disciplinas.items():
                    status = calcular_status(disc["respostas"])

                    with st.expander(
                        f"{STATUS_EMOJI[status]} {cod} – {disc['descricao']}",
                        expanded=False
                    ):
                        for aba in xls.sheet_names:
                            base = xls.parse(aba)
                            base = base[base["Codigo"] == cod]

                            for tipo in ["Procedimento", "Acompanhamento"]:
                                bloco = base[base["Tipo"] == tipo]
                                if bloco.empty:
                                    continue

                                st.markdown(f"**{tipo}**")

                                for i, r in bloco.iterrows():
                                    key = f"{fase}_{grupo}_{cod}_{i}"

                                    resp = st.selectbox(
                                        r["Pergunta"],
                                        STATUS_OPCOES,
                                        index=STATUS_OPCOES.index(
                                            disc["respostas"].get(r["Pergunta"], "NA")
                                        ),
                                        key=key
                                    )

                                    disc["respostas"][r["Pergunta"]] = resp

                                    if resp in ["Ruim", "Crítico"]:
                                        j = st.text_input(
                                            "Justificativa",
                                            key=f"{key}_j"
                                        )
                                        if j and j not in disc["justificativas"]:
                                            disc["justificativas"].append(j)

# =====================================================
# SALVAR / PDF
# =====================================================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data} {hora.strftime('%H:%M')}"
    st.session_state.avaliacoes_por_data[chave] = copy.deepcopy(
        st.session_state.avaliacao_atual
    )
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success("Avaliação salva com sucesso.")

if st.button("📄 Gerar PDF"):
    cab = {
        "projeto": projeto,
        "cliente": cliente,
        "responsavel": responsavel,
        "data": str(data),
        "hora": hora.strftime("%H:%M")
    }

    gerar_pdf(cab, st.session_state.avaliacao_atual, "avaliacao.pdf")

    with open("avaliacao.pdf", "rb") as f:
        st.download_button(
            "⬇️ Download PDF",
            f,
            "avaliacao.pdf"
        )
