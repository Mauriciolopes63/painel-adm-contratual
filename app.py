import streamlit as st
import pandas as pd
import json
import os
import copy
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import green, yellow, red, grey, black

# =========================
# CONFIGURAÇÃO INICIAL
# =========================
st.set_page_config(page_title="Painel Administração Contratual", layout="wide")

ARQUIVO_AVALIACOES = "avaliacoes.json"

STATUS_OPCOES = ["NA", "Ruim", "Regular", "Bom"]
STATUS_CORES = {
    "Bom": green,
    "Regular": yellow,
    "Ruim": red,
    "NA": grey
}

# =========================
# FUNÇÕES AUXILIARES
# =========================
def carregar_avaliacoes():
    if os.path.exists(ARQUIVO_AVALIACOES):
        with open(ARQUIVO_AVALIACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_avaliacoes(avaliacoes):
    with open(ARQUIVO_AVALIACOES, "w", encoding="utf-8") as f:
        json.dump(avaliacoes, f, ensure_ascii=False, indent=2)

def cor_status_pdf(c):
    return STATUS_CORES.get(c, grey)

# =========================
# PDF
# =========================
def gerar_pdf(cab, avaliacao, nome_arquivo):
    c = canvas.Canvas(nome_arquivo, pagesize=A4)
    largura, altura = A4

    # -------- CAPA / RESUMO --------
    y = altura - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Painel de Administração Contratual")
    y -= 25

    c.setFont("Helvetica", 10)
    for k, v in cab.items():
        c.drawString(40, y, f"{k}: {v}")
        y -= 15

    y -= 20
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Resumo por Disciplina")
    y -= 20

    for fase, grupos in avaliacao.items():
        c.setFont("Helvetica-Bold", 10)
        c.drawString(40, y, f"> {fase}")
        y -= 15

        for grupo, disciplinas in grupos.items():
            c.setFont("Helvetica-Bold", 9)
            c.drawString(60, y, f"> {grupo}")
            y -= 15

            for disc, dados in disciplinas.items():
                status = dados["status"]
                c.setFillColor(cor_status_pdf(status))
                c.rect(80, y - 5, 10, 10, fill=1)
                c.setFillColor(black)
                c.drawString(100, y, f"{disc} - {dados['descricao']}")
                y -= 15

                if y < 80:
                    c.showPage()
                    y = altura - 50

    # -------- JUSTIFICATIVAS --------
    c.showPage()
    y = altura - 50
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Justificativas")
    y -= 25

    for fase, grupos in avaliacao.items():
        for grupo, disciplinas in grupos.items():
            for disc, dados in disciplinas.items():
                justificativas = dados["justificativas"]
                if not justificativas:
                    continue

                c.setFont("Helvetica-Bold", 10)
                c.drawString(40, y, f"{fase} > {grupo} > {disc}")
                y -= 15

                c.setFillColor(cor_status_pdf(dados["status"]))
                c.rect(40, y - 5, 10, 10, fill=1)
                c.setFillColor(black)
                c.drawString(55, y, dados["status"])
                y -= 15

                c.setFont("Helvetica", 9)
                for j in justificativas:
                    c.drawString(60, y, f"- {j}")
                    y -= 12
                    if y < 80:
                        c.showPage()
                        y = altura - 50

    c.save()

# =========================
# ESTADO
# =========================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {}

if "data_avaliacao_atual" not in st.session_state:
    st.session_state.data_avaliacao_atual = None

# =========================
# CABEÇALHO
# =========================
st.title("Painel Administração Contratual")

with st.expander("Cabeçalho da Avaliação", expanded=True):
    cabecalho = {
        "Cliente": st.text_input("Cliente"),
        "Empreendimento": st.text_input("Empreendimento"),
        "Contrato": st.text_input("Contrato"),
        "Responsável": st.text_input("Responsável"),
        "Data": st.date_input("Data").strftime("%d/%m/%Y"),
        "Hora": datetime.now().strftime("%H:%M")
    }

# =========================
# MENU
# =========================
col1, col2 = st.columns(2)

with col1:
    nova = st.button("Nova Avaliação")

with col2:
    abrir = st.button("Abrir Avaliação Existente")

# =========================
# ABRIR AVALIAÇÃO
# =========================
if abrir and st.session_state.avaliacoes_por_data:
    chave = st.selectbox(
        "Selecione a avaliação",
        list(st.session_state.avaliacoes_por_data.keys())
    )

    if st.button("Carregar Avaliação"):
        st.session_state.avaliacao_atual = copy.deepcopy(
            st.session_state.avaliacoes_por_data[chave]
        )
        st.session_state.data_avaliacao_atual = chave
        st.success("Avaliação carregada corretamente.")

# =========================
# NOVA AVALIAÇÃO
# =========================
if nova:
    st.session_state.avaliacao_atual = {}
    st.session_state.data_avaliacao_atual = None

# =========================
# UPLOAD EXCEL
# =========================
arquivo = st.file_uploader("Upload do Excel", type=["xlsx"])

if arquivo:
    xls = pd.ExcelFile(arquivo)

    for aba in xls.sheet_names:
        df = xls.parse(aba)

        fase = df.iloc[0]["Fase"]
        grupo = df.iloc[0]["Grupo"]
        codigo = df.iloc[0]["Codigo"]
        descricao = df.iloc[0]["Descricao"]

        st.session_state.avaliacao_atual.setdefault(fase, {}) \
            .setdefault(grupo, {}) \
            .setdefault(codigo, {
                "descricao": descricao,
                "status": "NA",
                "justificativas": []
            })

        st.markdown(f"### {fase} > {grupo} > {codigo} - {descricao}")

        for tipo in ["Procedimento", "Acompanhamento"]:
            with st.expander(tipo):
                for i, r in df[df["Tipo"] == tipo].iterrows():
                    chave = f"{fase}_{grupo}_{codigo}_{i}"
                    resp = st.selectbox(
                        r["Pergunta"],
                        STATUS_OPCOES,
                        index=0,
                        key=chave
                    )

                    if resp != "NA":
                        st.session_state.avaliacao_atual[fase][grupo][codigo]["status"] = resp
                        just = st.text_area(
                            "Justificativa (opcional)",
                            key=f"j_{chave}"
                        )
                        if just:
                            st.session_state.avaliacao_atual[fase][grupo][codigo]["justificativas"].append(just)

# =========================
# SALVAR
# =========================
if st.button("Salvar Avaliação"):
    data_chave = st.session_state.data_avaliacao_atual or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.avaliacoes_por_data[data_chave] = copy.deepcopy(st.session_state.avaliacao_atual)
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success("Avaliação salva corretamente.")

# =========================
# PDF
# =========================
if st.button("Gerar PDF"):
    gerar_pdf(cabecalho, st.session_state.avaliacao_atual, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("Download PDF", f, file_name="avaliacao.pdf")
