import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import red, yellow, green, black
from reportlab.lib.units import cm

# =============================
# CONFIG
# =============================
st.set_page_config("Painel Administração Contratual", layout="wide")

ARQUIVO_AVALIACOES = "avaliacoes.json"

OPCOES = ["Bom", "Médio", "Ruim", "Crítico", "NA"]

MAPA_SEMAFORO = {
    "Bom": green,
    "Médio": yellow,
    "Ruim": red,
    "Crítico": red,
    "NA": black
}

# =============================
# PERSISTÊNCIA
# =============================
def carregar_avaliacoes():
    if os.path.exists(ARQUIVO_AVALIACOES):
        with open(ARQUIVO_AVALIACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_avaliacoes(dados):
    with open(ARQUIVO_AVALIACOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# =============================
# PDF
# =============================
def gerar_pdf(cabecalho, avaliacao, caminho):
    c = canvas.Canvas(caminho, pagesize=A4)
    largura, altura = A4

    def rodape(pagina):
        c.setFont("Helvetica", 8)
        c.drawRightString(largura - 1.5 * cm, 1 * cm, f"Página {pagina}")

    y = altura - 2 * cm
    pagina = 1

    # ===== CAPA / RESUMO =====
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, y, "Painel de Administração Contratual")
    y -= 1.2 * cm

    c.setFont("Helvetica", 10)
    for k, v in cabecalho.items():
        c.drawString(2 * cm, y, f"{k}: {v}")
        y -= 0.6 * cm

    y -= 0.5 * cm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Resumo por Fase / Grupo / Disciplina")
    y -= 1 * cm

    for fase, grupos in avaliacao.items():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(2 * cm, y, f"Fase: {fase}")
        y -= 0.7 * cm

        for grupo, disciplinas in grupos.items():
            c.setFont("Helvetica-Bold", 10)
            c.drawString(2.5 * cm, y, f"Grupo: {grupo}")
            y -= 0.6 * cm

            for disc, dados in disciplinas.items():
                cor = MAPA_SEMAFORO[dados["status"]]
                c.setFillColor(cor)
                c.rect(2.5 * cm, y - 0.3 * cm, 0.4 * cm, 0.4 * cm, fill=1)
                c.setFillColor(black)
                c.drawString(3.1 * cm, y, f"{disc} – {dados['descricao']}")
                y -= 0.5 * cm

                if y < 3 * cm:
                    rodape(pagina)
                    c.showPage()
                    pagina += 1
                    y = altura - 2 * cm

            y -= 0.4 * cm

    rodape(pagina)
    c.showPage()
    pagina += 1
    y = altura - 2 * cm

    # ===== JUSTIFICATIVAS =====
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Justificativas")
    y -= 1 * cm

    for fase, grupos in avaliacao.items():
        for grupo, disciplinas in grupos.items():
            for disc, dados in disciplinas.items():
                justificativas = [
                    r for r in dados["respostas"]
                    if r["Resposta"] in ["Ruim", "Crítico"] and r["Justificativa"]
                ]
                if not justificativas:
                    continue

                cor = MAPA_SEMAFORO[dados["status"]]
                c.setFillColor(cor)
                c.rect(2 * cm, y - 0.3 * cm, 0.4 * cm, 0.4 * cm, fill=1)
                c.setFillColor(black)

                c.setFont("Helvetica-Bold", 10)
                c.drawString(2.6 * cm, y, f"{fase} > {grupo} > {disc} – {dados['descricao']}")
                y -= 0.6 * cm

                c.setFont("Helvetica", 9)
                for r in justificativas:
                    c.drawString(3 * cm, y, f"- {r['Resposta']}: {r['Justificativa']}")
                    y -= 0.45 * cm
                    if y < 3 * cm:
                        rodape(pagina)
                        c.showPage()
                        pagina += 1
                        y = altura - 2 * cm

                y -= 0.4 * cm

    rodape(pagina)
    c.save()

# =============================
# ESTADO
# =============================
if "avaliacoes_salvas" not in st.session_state:
    st.session_state.avaliacoes_salvas = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {}

if "modo" not in st.session_state:
    st.session_state.modo = "nova"

# =============================
# TÍTULO
# =============================
st.title("Painel Administração Contratual")

# =============================
# CONTROLES
# =============================
col1, col2 = st.columns(2)

with col1:
    if st.button("🆕 Nova Avaliação"):
        st.session_state.modo = "nova"
        st.session_state.avaliacao_atual = {}

with col2:
    if st.button("📂 Abrir Avaliação Existente"):
        st.session_state.modo = "abrir"

# =============================
# ABRIR AVALIAÇÃO
# =============================
if st.session_state.modo == "abrir":
    datas = list(st.session_state.avaliacoes_salvas.keys())
    if datas:
        data_sel = st.selectbox("Selecione a avaliação", datas)
        if st.button("Abrir"):
            st.session_state.avaliacao_atual = st.session_state.avaliacoes_salvas[data_sel]
            st.success("Avaliação carregada.")
    else:
        st.info("Nenhuma avaliação salva.")

# =============================
# CABEÇALHO
# =============================
st.subheader("Dados da Avaliação")

cabecalho = {
    "Projeto": st.text_input("Nome do Projeto"),
    "Cliente": st.text_input("Cliente"),
    "Responsável": st.text_input("Responsável"),
    "Data": datetime.now().strftime("%d/%m/%Y %H:%M")
}

# =============================
# UPLOAD
# =============================
uploaded = st.file_uploader("Upload do Excel", type=["xlsx"])

if not uploaded:
    st.stop()

xls = pd.ExcelFile(uploaded)

# =============================
# PROCESSAMENTO
# =============================
for aba in xls.sheet_names:
    df = xls.parse(aba)

    fase = df.iloc[0]["Fase"]
    grupo = df.iloc[0]["Grupo"]
    codigo = df.iloc[0]["Codigo"]
    descricao = df.iloc[0]["Descricao"]

    st.markdown(f"### {fase} > {grupo}")
    with st.expander(f"{codigo} – {descricao}", expanded=False):

        respostas = []

        for tipo in ["Procedimento", "Acompanhamento"]:
            st.markdown(f"**{tipo}**")
            sub = df[df["Tipo"] == tipo]

            for i, r in sub.iterrows():
                key = f"{codigo}_{i}"
                resp = st.selectbox(r["Pergunta"], OPCOES, key=key)
                just = ""
                if resp in ["Ruim", "Crítico"]:
                    just = st.text_input("Justificativa", key=key + "_j")

                respostas.append({
                    "Tipo": tipo,
                    "Pergunta": r["Pergunta"],
                    "Resposta": resp,
                    "Justificativa": just
                })

        status = next((r["Resposta"] for r in respostas if r["Resposta"] in ["Crítico", "Ruim", "Médio", "Bom"]), "NA")

        st.session_state.avaliacao_atual.setdefault(fase, {}).setdefault(grupo, {})[codigo] = {
            "descricao": descricao,
            "status": status,
            "respostas": respostas
        }

# =============================
# SALVAR / PDF
# =============================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.avaliacoes_salvas[chave] = st.session_state.avaliacao_atual
    salvar_avaliacoes(st.session_state.avaliacoes_salvas)
    st.success("Avaliação salva com sucesso.")

if st.button("📄 Gerar PDF"):
    gerar_pdf(cabecalho, st.session_state.avaliacao_atual, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download do PDF", f, "avaliacao.pdf", "application/pdf")
