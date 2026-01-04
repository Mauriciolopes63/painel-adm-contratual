import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from io import BytesIO

# =====================================================
# CONFIGURAÇÃO
# =====================================================
st.set_page_config(
    page_title="Painel Administração Contratual",
    layout="wide"
)

AVALIACOES_FILE = "avaliacoes.json"

VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0,
    "NA": None
}

CORES_PDF = {
    "🟢": colors.green,
    "🟡": colors.yellow,
    "🟠": colors.orange,
    "🔴": colors.red,
    "⚪": colors.lightgrey
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
# CÁLCULOS
# =====================================================
def calcular_media_ponderada(df):
    validas = df[df["Resposta"] != "NA"].copy()
    if validas.empty:
        return None
    validas["valor"] = validas["Resposta"].map(VALORES)
    soma = (validas["valor"] * validas["Peso"]).sum()
    peso = validas["Peso"].sum()
    return soma / peso if peso > 0 else None

def cor_por_nota(nota):
    if nota is None:
        return "⚪"
    if nota <= 0.25:
        return "🟢"
    elif nota <= 0.50:
        return "🟡"
    elif nota < 0.75:
        return "🟠"
    else:
        return "🔴"

# =====================================================
# PDF
# =====================================================
def gerar_pdf(cabecalho, avaliacao):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # -------- CAPA --------
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "PAINEL ADMINISTRAÇÃO CONTRATUAL")
    y -= 40

    c.setFont("Helvetica", 11)
    for k, v in cabecalho.items():
        c.drawString(50, y, f"{k}: {v}")
        y -= 20

    c.showPage()

    # -------- RESUMO --------
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 40, "Resumo Executivo – Semáforos por Disciplina")

    y = height - 80
    c.setFont("Helvetica", 10)

    for disc, dados in avaliacao.items():
        cor = CORES_PDF[dados["semaforo"]]
        c.setFillColor(cor)
        c.rect(50, y - 10, 10, 10, fill=1)
        c.setFillColor(colors.black)
        c.drawString(70, y - 10, f"{disc} – {dados['descricao']}")
        y -= 20

        if y < 60:
            c.showPage()
            y = height - 60

    c.showPage()

    # -------- JUSTIFICATIVAS --------
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 40, "Justificativas")
    y = height - 80

    for disc, dados in avaliacao.items():
        for tipo, itens in dados["justificativas"].items():
            if not itens:
                continue

            c.setFont("Helvetica-Bold", 11)
            c.drawString(50, y, f"{disc} – {dados['descricao']} ({tipo})")
            y -= 20

            for p in itens:
                c.setFont("Helvetica", 10)
                c.drawString(60, y, f"- {p}")
                y -= 15

                if y < 60:
                    c.showPage()
                    y = height - 60

    c.save()
    buffer.seek(0)
    return buffer

# =====================================================
# ESTADO
# =====================================================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {}

# =====================================================
# CABEÇALHO
# =====================================================
st.title("Painel Administração Contratual")

st.markdown("### Dados do Cabeçalho")
col1, col2, col3 = st.columns(3)
with col1:
    nome_projeto = st.text_input("Nome do Projeto")
with col2:
    nome_cliente = st.text_input("Nome do Cliente")
with col3:
    responsavel = st.text_input("Responsável")

st.markdown("### Data da Avaliação")
data = st.date_input("Data", datetime.now().date())
hora = st.time_input("Hora", (datetime.utcnow() - timedelta(hours=3)).time())

# =====================================================
# AÇÕES
# =====================================================
colA, colB = st.columns(2)
with colA:
    nova = st.button("🆕 Nova Avaliação", use_container_width=True)
with colB:
    abrir = st.button("📂 Abrir Avaliação Existente", use_container_width=True)

if abrir:
    if not st.session_state.avaliacoes_por_data:
        st.info("Nenhuma avaliação salva.")
    else:
        chave = st.selectbox(
            "Selecione a avaliação",
            list(st.session_state.avaliacoes_por_data.keys())
        )
        st.session_state.avaliacao_atual = st.session_state.avaliacoes_por_data[chave]

# =====================================================
# UPLOAD EXCEL
# =====================================================
uploaded_file = st.file_uploader("Upload do Excel", type=["xlsx"])
if not uploaded_file:
    st.stop()

xls = pd.ExcelFile(uploaded_file)

# =====================================================
# CANVAS
# =====================================================
st.subheader("Canvas do Projeto")

avaliacao_pdf = {}

for aba in xls.sheet_names:
    df = xls.parse(aba)

    if aba not in st.session_state.avaliacao_atual:
        df["Resposta"] = "NA"
        df["Justificativa"] = ""
    else:
        df = pd.DataFrame(st.session_state.avaliacao_atual[aba]["dados"])

    codigo = df.iloc[0]["Codigo"]
    descricao = df.iloc[0]["Descricao"]

    proc = df[df["Tipo"] == "Procedimento"]
    acomp = df[df["Tipo"] == "Acompanhamento"]

    nota = calcular_media_ponderada(df)
    semaforo = cor_por_nota(nota)

    with st.expander(f"{semaforo} {codigo} – {descricao}", expanded=False):

        st.markdown("**Procedimento**")
        for i, r in proc.iterrows():
            resp = st.selectbox(
                r["Pergunta"],
                ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                index=["Bom", "Médio", "Ruim", "Crítico", "NA"].index(df.at[i, "Resposta"]),
                key=f"{aba}_{i}"
            )
            df.at[i, "Resposta"] = resp
            if resp in ["Ruim", "Crítico"]:
                df.at[i, "Justificativa"] = st.text_input(
                    "Justificativa",
                    value=df.at[i, "Justificativa"],
                    key=f"{aba}_{i}_j"
                )

        st.markdown("**Acompanhamento**")
        for i, r in acomp.iterrows():
            resp = st.selectbox(
                r["Pergunta"],
                ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                index=["Bom", "Médio", "Ruim", "Crítico", "NA"].index(df.at[i, "Resposta"]),
                key=f"{aba}_{i}_a"
            )
            df.at[i, "Resposta"] = resp
            if resp in ["Ruim", "Crítico"]:
                df.at[i, "Justificativa"] = st.text_input(
                    "Justificativa",
                    value=df.at[i, "Justificativa"],
                    key=f"{aba}_{i}_aj"
                )

    justificativas = {
        "Procedimento": proc[proc["Justificativa"] != ""]["Justificativa"].tolist(),
        "Acompanhamento": acomp[acomp["Justificativa"] != ""]["Justificativa"].tolist()
    }

    avaliacao_pdf[aba] = {
        "descricao": descricao,
        "semaforo": semaforo,
        "justificativas": justificativas,
        "dados": df.to_dict(orient="records")
    }

    st.session_state.avaliacao_atual[aba] = avaliacao_pdf[aba]

# =====================================================
# SALVAR
# =====================================================
if st.button("💾 Salvar Avaliação"):
    chave = f"{data} {hora.strftime('%H:%M')}"
    st.session_state.avaliacoes_por_data[chave] = st.session_state.avaliacao_atual
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success("Avaliação salva com sucesso.")

# =====================================================
# PDF
# =====================================================
if st.button("📄 Gerar PDF"):
    cabecalho = {
        "Projeto": nome_projeto,
        "Cliente": nome_cliente,
        "Responsável": responsavel,
        "Data": f"{data} {hora.strftime('%H:%M')}"
    }
    pdf = gerar_pdf(cabecalho, avaliacao_pdf)
    st.download_button(
        "⬇️ Download PDF",
        data=pdf,
        file_name="avaliacao_contratual.pdf",
        mime="application/pdf"
    )
