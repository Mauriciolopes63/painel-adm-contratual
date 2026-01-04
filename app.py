import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import green, yellow, orange, red, black

# =========================================================
# CONFIG
# =========================================================
st.set_page_config("Painel Administração Contratual", layout="wide")
AVALIACOES_FILE = "avaliacoes.json"

VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0,
    "NA": None
}

# =========================================================
# PERSISTÊNCIA
# =========================================================
def salvar_avaliacoes(dados):
    with open(AVALIACOES_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_avaliacoes():
    if os.path.exists(AVALIACOES_FILE):
        with open(AVALIACOES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# =========================================================
# CÁLCULO
# =========================================================
def calcular_media(df):
    df = df[df["Resposta"] != "NA"].copy()
    if df.empty:
        return None
    df["valor"] = df["Resposta"].map(VALORES)
    return (df["valor"] * df["Peso"]).sum() / df["Peso"].sum()

def cor_semaforo(nota):
    if nota is None:
        return "⚪"
    if nota <= 0.25:
        return "🟢"
    if nota <= 0.50:
        return "🟡"
    if nota < 0.75:
        return "🟠"
    return "🔴"

def cor_pdf(nota):
    if nota <= 0.25:
        return green
    if nota <= 0.50:
        return yellow
    if nota < 0.75:
        return orange
    return red

# =========================================================
# PDF
# =========================================================
def gerar_pdf(cab, avaliacao, path):
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    y = h - 40
    pagina = 1

    def rodape():
        c.setFont("Helvetica", 8)
        c.drawRightString(w - 40, 20, f"Página {pagina}")

    # CAPA
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "RELATÓRIO – PAINEL ADMINISTRAÇÃO CONTRATUAL")
    y -= 30

    c.setFont("Helvetica", 10)
    for k, v in cab.items():
        c.drawString(40, y, f"{k}: {v}")
        y -= 15

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Resumo por Disciplina")
    y -= 25

    for fase, grupos in avaliacao.items():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, fase)
        y -= 18

        for grupo, disciplinas in grupos.items():
            c.setFont("Helvetica-Bold", 10)
            c.drawString(55, y, grupo)
            y -= 15

            for d in disciplinas:
                c.setFillColor(cor_pdf(d["nota"]))
                c.rect(70, y-5, 8, 8, fill=1)
                c.setFillColor(black)
                c.drawString(85, y, f"{d['codigo']} – {d['descricao']}")
                y -= 15

                if y < 60:
                    rodape()
                    c.showPage()
                    pagina += 1
                    y = h - 40

    rodape()
    c.showPage()
    pagina += 1
    y = h - 40

    # JUSTIFICATIVAS
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Justificativas")
    y -= 25

    for fase, grupos in avaliacao.items():
        for grupo, disciplinas in grupos.items():
            for d in disciplinas:
                if not d["justificativas"]:
                    continue

                c.setFont("Helvetica-Bold", 10)
                c.drawString(40, y, f"{fase} > {grupo} > {d['codigo']}")
                y -= 15

                for item in d["justificativas"]:
                    c.setFont("Helvetica", 9)
                    c.drawString(55, y, f"- [{item['tipo']}] {item['texto']}")
                    y -= 12

                    if y < 60:
                        rodape()
                        c.showPage()
                        pagina += 1
                        y = h - 40

    rodape()
    c.save()

# =========================================================
# ESTADO
# =========================================================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {}

if "modo" not in st.session_state:
    st.session_state.modo = None

# =========================================================
# TELA INICIAL
# =========================================================
st.title("Painel Administração Contratual")

col1, col2 = st.columns(2)
with col1:
    if st.button("🆕 Nova Avaliação", use_container_width=True):
        st.session_state.modo = "nova"
        st.session_state.avaliacao_atual = {}

with col2:
    if st.button("📂 Abrir Avaliação Existente", use_container_width=True):
        st.session_state.modo = "abrir"

if st.session_state.modo is None:
    st.stop()

# =========================================================
# CABEÇALHO
# =========================================================
st.markdown("### Cabeçalho da Avaliação")

nome_projeto = st.text_input("Nome do Projeto")
cliente = st.text_input("Cliente")
responsavel = st.text_input("Responsável")

data = st.date_input("Data", datetime.now().date())
hora = st.time_input("Hora", (datetime.utcnow() - timedelta(hours=3)).time())

# =========================================================
# ABRIR AVALIAÇÃO
# =========================================================
if st.session_state.modo == "abrir":
    if not st.session_state.avaliacoes_por_data:
        st.info("Nenhuma avaliação salva.")
        st.stop()

    chave = st.selectbox(
        "Selecione a avaliação",
        list(st.session_state.avaliacoes_por_data.keys())
    )

    if st.button("Abrir"):
        st.session_state.avaliacao_atual = st.session_state.avaliacoes_por_data[chave]
        st.success("Avaliação carregada.")

# =========================================================
# UPLOAD EXCEL
# =========================================================
uploaded = st.file_uploader("Carregar Excel", type=["xlsx"])
if not uploaded:
    st.stop()

xls = pd.ExcelFile(uploaded)

# =========================================================
# TELA DE PERGUNTAS
# =========================================================
estrutura = {}

for aba in xls.sheet_names:
    base = xls.parse(aba)

    fase = base.iloc[0]["Fase"]
    grupo = base.iloc[0]["Grupo"]
    codigo = base.iloc[0]["Codigo"]
    descricao = base.iloc[0]["Descricao"]

    base["Resposta"] = base.get("Resposta", "NA")
    base["Justificativa"] = base.get("Justificativa", "")

    estrutura.setdefault(fase, {}).setdefault(grupo, []).append({
        "codigo": codigo,
        "descricao": descricao,
        "df": base
    })

st.subheader("Questionário")

for fase, grupos in estrutura.items():
    with st.expander(fase, expanded=True):
        for grupo, disciplinas in grupos.items():
            with st.expander(grupo, expanded=False):
                for d in disciplinas:
                    nota = calcular_media(d["df"])
                    sem = cor_semaforo(nota)

                    with st.expander(f"{sem} {d['codigo']} – {d['descricao']}"):
                        for tipo in ["Procedimento", "Acompanhamento"]:
                            st.markdown(f"**{tipo}**")
                            for i, r in d["df"][d["df"]["Tipo"] == tipo].iterrows():
                                resp = st.selectbox(
                                    r["Pergunta"],
                                    ["NA", "Bom", "Médio", "Ruim", "Crítico"],
                                    index=["NA","Bom","Médio","Ruim","Crítico"].index(r["Resposta"]),
                                    key=f"{fase}|{grupo}|{d['codigo']}|{r['Tipo']}|{i}"
                                )

                                d["df"].at[i, "Resposta"] = resp
                                if resp in ["Ruim", "Crítico"]:
                                    d["df"].at[i, "Justificativa"] = st.text_input(
                                        "Justificativa",
                                        value=r["Justificativa"],
                                        key=f"{aba}_{i}_j"
                                    )

# =========================================================
# SALVAR + PDF
# =========================================================
if st.button("💾 Salvar Avaliação"):
    chave = f"{data} {hora.strftime('%H:%M')}"
    salvar = {}

    for fase, grupos in estrutura.items():
        salvar[fase] = {}
        for grupo, disciplinas in grupos.items():
            salvar[fase][grupo] = []
            for d in disciplinas:
                nota = calcular_media(d["df"])
                salvar[fase][grupo].append({
                    "codigo": d["codigo"],
                    "descricao": d["descricao"],
                    "nota": nota,
                    "justificativas": [
                        {
                            "tipo": r["Tipo"],
                            "texto": r["Justificativa"]
                        }
                        for _, r in d["df"].iterrows()
                        if r["Justificativa"]
                    ]
                })

    st.session_state.avaliacoes_por_data[chave] = salvar
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success("Avaliação salva.")

if st.button("📄 Gerar PDF"):
    cab = {
        "Projeto": nome_projeto,
        "Cliente": cliente,
        "Responsável": responsavel,
        "Data": f"{data} {hora.strftime('%H:%M')}"
    }
    gerar_pdf(cab, st.session_state.avaliacoes_por_data[chave], "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF", f, "avaliacao.pdf")
