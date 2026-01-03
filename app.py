import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import green, yellow, orange, red, black

# =========================================================
# CONFIGURAÇÕES
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
def carregar_avaliacoes():
    if os.path.exists(AVALIACOES_FILE):
        with open(AVALIACOES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_avaliacoes(dados):
    with open(AVALIACOES_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# =========================================================
# CÁLCULOS
# =========================================================
def calcular_media(df):
    df_validas = df[df["Resposta"] != "NA"].copy()
    if df_validas.empty:
        return None
    df_validas["valor"] = df_validas["Resposta"].map(VALORES)
    return (df_validas["valor"] * df_validas["Peso"]).sum() / df_validas["Peso"].sum()

def cor_por_nota(nota):
    if nota is None:
        return "⚪", black
    if nota <= 0.25:
        return "🟢", green
    if nota <= 0.50:
        return "🟡", yellow
    if nota < 0.75:
        return "🟠", orange
    return "🔴", red

# =========================================================
# PDF
# =========================================================
def gerar_pdf(avaliacao, nome_arquivo):
    c = canvas.Canvas(nome_arquivo, pagesize=A4)
    w, h = A4
    y = h - 40

    cab = avaliacao["cabecalho"]

    # CAPA
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Painel Administração Contratual")
    y -= 30
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Projeto: {cab['projeto']}")
    y -= 15
    c.drawString(40, y, f"Cliente: {cab['cliente']}")
    y -= 15
    c.drawString(40, y, f"Responsável: {cab['responsavel']}")
    y -= 15
    c.drawString(40, y, f"Data: {cab['data']}")
    y -= 30

    # RESUMO
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Resumo por Disciplina")
    y -= 20

    for disc, dados in avaliacao["dados"].items():
        nota = calcular_media(pd.DataFrame(dados))
        emoji, cor = cor_por_nota(nota)
        c.setFillColor(cor)
        c.rect(40, y - 10, 10, 10, fill=1)
        c.setFillColor(black)
        c.drawString(60, y - 8, disc)
        y -= 20
        if y < 60:
            c.showPage()
            y = h - 40

    # JUSTIFICATIVAS
    c.showPage()
    y = h - 40
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Justificativas")
    y -= 25

    for disc, dados in avaliacao["dados"].items():
        df = pd.DataFrame(dados)
        for tipo in ["Procedimento", "Acompanhamento"]:
            sub = df[(df["Tipo"] == tipo) & (df["Resposta"].isin(["Ruim", "Crítico"]))]
            if sub.empty:
                continue

            c.setFont("Helvetica-Bold", 10)
            c.drawString(40, y, f"{disc} – {tipo}")
            y -= 15

            for _, r in sub.iterrows():
                c.setFont("Helvetica", 9)
                c.drawString(50, y, f"- {r['Justificativa']}")
                y -= 12
                if y < 60:
                    c.showPage()
                    y = h - 40

    c.save()

# =========================================================
# ESTADO
# =========================================================
if "modo" not in st.session_state:
    st.session_state.modo = None

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = None

avaliacoes_salvas = carregar_avaliacoes()

# =========================================================
# TOPO
# =========================================================
st.title("Painel Administração Contratual")

col1, col2 = st.columns(2)
with col1:
    if st.button("🆕 Nova Avaliação"):
        st.session_state.modo = "nova"
        st.session_state.avaliacao_atual = None
        st.rerun()

with col2:
    if st.button("📂 Abrir Avaliação Existente"):
        st.session_state.modo = "abrir"
        st.rerun()

# =========================================================
# ABRIR AVALIAÇÃO
# =========================================================
if st.session_state.modo == "abrir":
    if not avaliacoes_salvas:
        st.info("Nenhuma avaliação salva.")
        st.stop()

    chave = st.selectbox("Selecione a avaliação", sorted(avaliacoes_salvas.keys(), reverse=True))

    if st.button("Abrir"):
        st.session_state.avaliacao_atual = json.loads(json.dumps(avaliacoes_salvas[chave]))
        st.session_state.modo = "nova"
        st.rerun()

# =========================================================
# NOVA / EDITAR
# =========================================================
if st.session_state.modo != "nova":
    st.stop()

# CABEÇALHO
st.subheader("Cabeçalho")
col1, col2, col3 = st.columns(3)
with col1:
    projeto = st.text_input("Projeto", value=st.session_state.avaliacao_atual["cabecalho"]["projeto"] if st.session_state.avaliacao_atual else "")
with col2:
    cliente = st.text_input("Cliente", value=st.session_state.avaliacao_atual["cabecalho"]["cliente"] if st.session_state.avaliacao_atual else "")
with col3:
    responsavel = st.text_input("Responsável", value=st.session_state.avaliacao_atual["cabecalho"]["responsavel"] if st.session_state.avaliacao_atual else "")

data = st.date_input("Data", datetime.now().date())
hora = st.time_input("Hora", (datetime.utcnow() - timedelta(hours=3)).time())

uploaded = st.file_uploader("Upload Excel", type=["xlsx"])
if not uploaded:
    st.stop()

xls = pd.ExcelFile(uploaded)

dados = {}
st.subheader("Canvas")

for aba in xls.sheet_names:
    df = xls.parse(aba)

    if st.session_state.avaliacao_atual:
        df_salvo = pd.DataFrame(st.session_state.avaliacao_atual["dados"][aba])
        df["Resposta"] = df_salvo["Resposta"]
        df["Justificativa"] = df_salvo["Justificativa"]
    else:
        df["Resposta"] = "NA"
        df["Justificativa"] = ""

    nota = calcular_media(df)
    emoji, _ = cor_por_nota(nota)

    with st.expander(f"{emoji} {df.iloc[0]['Codigo']} – {df.iloc[0]['Descricao']}"):
        for tipo in ["Procedimento", "Acompanhamento"]:
            st.markdown(f"**{tipo}**")
            sub = df[df["Tipo"] == tipo]
            for i, r in sub.iterrows():
                resp = st.selectbox(
                    r["Pergunta"],
                    ["NA", "Bom", "Médio", "Ruim", "Crítico"],
                    index=["NA", "Bom", "Médio", "Ruim", "Crítico"].index(r["Resposta"]),
                    key=f"{aba}_{i}"
                )
                df.at[i, "Resposta"] = resp
                if resp in ["Ruim", "Crítico"]:
                    df.at[i, "Justificativa"] = st.text_input(
                        "Justificativa",
                        value=r["Justificativa"],
                        key=f"{aba}_{i}_j"
                    )

    dados[aba] = df.to_dict(orient="records")

# =========================================================
# SALVAR / PDF
# =========================================================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data} {hora.strftime('%H:%M')}"
    avaliacoes_salvas[chave] = {
        "cabecalho": {
            "projeto": projeto,
            "cliente": cliente,
            "responsavel": responsavel,
            "data": chave
        },
        "dados": dados
    }
    salvar_avaliacoes(avaliacoes_salvas)
    st.success("Avaliação salva com sucesso.")

if st.button("📄 Gerar PDF"):
    nome = "avaliacao.pdf"
    gerar_pdf({
        "cabecalho": {
            "projeto": projeto,
            "cliente": cliente,
            "responsavel": responsavel,
            "data": f"{data} {hora.strftime('%H:%M')}"
        },
        "dados": dados
    }, nome)

    with open(nome, "rb") as f:
        st.download_button("⬇️ Download PDF", f, file_name=nome)
