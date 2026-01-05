import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import green, yellow, orange, red, grey, black
from reportlab.lib.utils import ImageReader

# =====================================================
# CONFIGURAÇÃO
# =====================================================
st.set_page_config("Painel Administração Contratual", layout="wide")

ARQ_AVALIACOES = "avaliacoes.json"
LOGO_M2L = "logo_m2l.png"

STATUS_OPCOES = ["NA", "Bom", "Médio", "Ruim", "Crítico"]

STATUS_EMOJI = {
    "Bom": "🟢",
    "Médio": "🟡",
    "Ruim": "🟠",
    "Crítico": "🔴",
    "NA": "⚪"
}

STATUS_CORES = {
    "Bom": green,
    "Médio": yellow,
    "Ruim": orange,
    "Crítico": red,
    "NA": grey
}

# =====================================================
# PERSISTÊNCIA
# =====================================================
def carregar_avaliacoes():
    if os.path.exists(ARQ_AVALIACOES):
        with open(ARQ_AVALIACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_avaliacoes(dados):
    with open(ARQ_AVALIACOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# =====================================================
# CÁLCULO DE SEMÁFORO
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
def gerar_pdf(cab, avaliacao, nome_pdf, logo_cliente=None):
    c = canvas.Canvas(nome_pdf, pagesize=A4)
    largura, altura = A4
    y = altura - 40
    pagina = 1

    def rodape():
        c.setFont("Helvetica", 9)
        c.drawRightString(largura - 40, 20, f"Página {pagina}")

    # LOGOS
    if os.path.exists(LOGO_M2L):
        c.drawImage(ImageReader(LOGO_M2L), 40, altura - 90, width=120, preserveAspectRatio=True)

    if logo_cliente:
        c.drawImage(ImageReader(logo_cliente), largura - 160, altura - 90, width=120, preserveAspectRatio=True)

    # CABEÇALHO
    y -= 70
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
    c.drawString(40, y, "Resumo por Disciplina")
    y -= 20

    for fase, grupos in avaliacao.items():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, f"Fase: {fase}")
        y -= 16

        for grupo, disciplinas in grupos.items():
            c.setFont("Helvetica-Bold", 10)
            c.drawString(60, y, f"Grupo: {grupo}")
            y -= 14

            for disc, dados in disciplinas.items():
                status = calcular_status(dados["respostas"])
                c.setFillColor(STATUS_CORES[status])
                c.rect(80, y - 4, 8, 8, fill=1)
                c.setFillColor(black)
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

                status = calcular_status(dados["respostas"])
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

# CABEÇALHO
st.subheader("Cabeçalho")
projeto = st.text_input("Nome do Projeto")
cliente = st.text_input("Cliente")
responsavel = st.text_input("Responsável")
logo_cliente = st.file_uploader("Logo do Cliente (opcional)", type=["png", "jpg", "jpeg"])

data = st.date_input("Data", datetime.now().date())
hora = st.time_input("Hora", (datetime.utcnow() - timedelta(hours=3)).time())

# =====================================================
# ABRIR AVALIAÇÃO
# =====================================================
if modo == "Abrir Avaliação Existente":
    chaves = list(st.session_state.avaliacoes_por_data.keys())
    if not chaves:
        st.info("Nenhuma avaliação salva.")
        st.stop()

    chave_sel = st.selectbox("Selecione a avaliação", chaves)
    st.session_state.avaliacao_atual = json.loads(
        json.dumps(st.session_state.avaliacoes_por_data[chave_sel])
    )

# =====================================================
# UPLOAD EXCEL
# =====================================================
uploaded = st.file_uploader("Upload do Excel", type="xlsx")
if not uploaded:
    st.stop()

xls = pd.ExcelFile(uploaded)

# =====================================================
# LEITURA EXCEL
# =====================================================
for aba in xls.sheet_names:
    df = xls.parse(aba)

    codigo = df.iloc[0]["Codigo"]
    descricao = df.iloc[0]["Descricao"]

    for _, r in df.iterrows():
        fase = r["Fase"]
        grupo = r["Grupo"]
        tipo = r["Tipo"]

        st.session_state.avaliacao_atual.setdefault(fase, {})
        st.session_state.avaliacao_atual[fase].setdefault(grupo, {})
        st.session_state.avaliacao_atual[fase][grupo].setdefault(codigo, {
            "descricao": descricao,
            "respostas": [],
            "justificativas": []
        })

# =====================================================
# TELA DE PERGUNTAS
# =====================================================
for fase, grupos in st.session_state.avaliacao_atual.items():
    with st.expander(f"▶ Fase: {fase}", expanded=True):
        for grupo, disciplinas in grupos.items():
            with st.expander(f"▶ Grupo: {grupo}", expanded=True):
                for disc, dados in disciplinas.items():
                    status = calcular_status(dados["respostas"])
                    with st.expander(f"{STATUS_EMOJI[status]} {disc} – {dados['descricao']}"):
                        base = pd.concat(
                            [xls.parse(a) for a in xls.sheet_names]
                        )
                        base = base[base["Codigo"] == disc]

                        for tipo in ["Procedimento", "Acompanhamento"]:
                            bloco = base[base["Tipo"] == tipo]
                            if bloco.empty:
                                continue

                            st.markdown(f"**{tipo}**")
                            for i, r in bloco.iterrows():
                                chave = f"{disc}_{i}"
                                resp = st.selectbox(
                                    r["Pergunta"],
                                    STATUS_OPCOES,
                                    index=0,
                                    key=chave
                                )

                                if resp != "NA":
                                    dados["respostas"].append(resp)

                                if resp in ["Ruim", "Crítico"]:
                                    j = st.text_input("Justificativa", key=f"{chave}_j")
                                    if j and j not in dados["justificativas"]:
                                        dados["justificativas"].append(j)

# =====================================================
# SALVAR / PDF
# =====================================================
if st.button("💾 Salvar Avaliação"):
    chave = f"{data} {hora.strftime('%H:%M')}"
    st.session_state.avaliacoes_por_data[chave] = json.loads(
        json.dumps(st.session_state.avaliacao_atual)
    )
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success("Avaliação salva com sucesso")

if st.button("📄 Gerar PDF"):
    cab = {
        "projeto": projeto,
        "cliente": cliente,
        "responsavel": responsavel,
        "data": str(data),
        "hora": hora.strftime("%H:%M")
    }
    gerar_pdf(cab, st.session_state.avaliacao_atual, "avaliacao.pdf", logo_cliente)
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF", f, "avaliacao.pdf")
