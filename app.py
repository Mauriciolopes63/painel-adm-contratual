import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ===============================
# CONFIGURAÇÕES
# ===============================
st.set_page_config(
    page_title="Painel Administração Contratual",
    layout="wide"
)

ARQUIVO_AVALIACOES = "avaliacoes.json"

# ===============================
# PERSISTÊNCIA
# ===============================
def salvar_avaliacoes(dados):
    with open(ARQUIVO_AVALIACOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_avaliacoes():
    if os.path.exists(ARQUIVO_AVALIACOES):
        with open(ARQUIVO_AVALIACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ===============================
# REGRAS DE NEGÓCIO
# ===============================
VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0,
    "NA": None
}

def calcular_media_ponderada(df):
    df_validas = df[df["Resposta"] != "NA"].copy()
    if df_validas.empty:
        return None

    df_validas["valor"] = df_validas["Resposta"].map(VALORES)
    soma = (df_validas["valor"] * df_validas["Peso"]).sum()
    peso_total = df_validas["Peso"].sum()

    if peso_total == 0:
        return None

    return soma / peso_total

def semaforo_tela(nota):
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

def semaforo_pdf(nota):
    if nota is None:
        return "N/A"
    if nota <= 0.25:
        return "VERDE"
    elif nota <= 0.50:
        return "AMARELO"
    elif nota < 0.75:
        return "LARANJA"
    else:
        return "VERMELHO"

# ===============================
# PDF
# ===============================
def gerar_pdf(cabecalho, avaliacoes, caminho):
    c = canvas.Canvas(caminho, pagesize=A4)
    largura, altura = A4

    y = altura - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "RELATÓRIO DE AVALIAÇÃO CONTRATUAL")

    y -= 30
    c.setFont("Helvetica", 10)
    for k, v in cabecalho.items():
        c.drawString(40, y, f"{k}: {v}")
        y -= 15

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Resumo por Disciplina")

    y -= 20
    c.setFont("Helvetica", 10)

    for aba, registros in avaliacoes.items():
        df = pd.DataFrame(registros)
        nota = calcular_media_ponderada(df)
        status = semaforo_pdf(nota)

        c.drawString(40, y, f"{aba}: {status}")
        y -= 15

        if y < 80:
            c.showPage()
            y = altura - 50

    c.showPage()
    c.save()

# ===============================
# ESTADO
# ===============================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

# ===============================
# TÍTULO
# ===============================
st.title("Painel Administração Contratual")

# ===============================
# CABEÇALHO
# ===============================
st.subheader("Dados do Projeto")

col1, col2, col3 = st.columns(3)

with col1:
    nome_projeto = st.text_input("Nome do Projeto")

with col2:
    nome_cliente = st.text_input("Cliente")

with col3:
    responsavel = st.text_input("Responsável")

st.divider()

# ===============================
# DATA / HORA
# ===============================
col4, col5 = st.columns(2)

with col4:
    data_avaliacao = st.date_input("Data da Avaliação", datetime.now().date())

with col5:
    hora_avaliacao = st.time_input("Hora da Avaliação", datetime.now().time())

# ===============================
# ABRIR AVALIAÇÃO EXISTENTE
# ===============================
st.subheader("Avaliações Salvas")

if st.session_state.avaliacoes_por_data:
    data_sel = st.selectbox(
        "Selecionar avaliação existente",
        list(st.session_state.avaliacoes_por_data.keys())
    )

    if st.button("📂 Abrir Avaliação"):
        dados = st.session_state.avaliacoes_por_data[data_sel]
        st.session_state.avaliacoes = {
            aba: pd.DataFrame(registros)
            for aba, registros in dados.items()
        }
        st.success("Avaliação carregada.")
else:
    st.info("Nenhuma avaliação salva.")

st.divider()

# ===============================
# UPLOAD EXCEL
# ===============================
uploaded_file = st.file_uploader(
    "Upload do Excel de Perguntas",
    type=["xlsx"]
)

if not uploaded_file:
    st.stop()

xls = pd.ExcelFile(uploaded_file)

# ===============================
# CANVAS
# ===============================
st.subheader("Canvas do Projeto")

for aba in xls.sheet_names:
    df = xls.parse(aba)

    if aba not in st.session_state.avaliacoes:
        df["Resposta"] = "NA"
        df["Justificativa"] = ""
        st.session_state.avaliacoes[aba] = df
    else:
        df = st.session_state.avaliacoes[aba]

    nota = calcular_media_ponderada(df)
    status = semaforo_tela(nota)

    with st.expander(f"{status} {aba}", expanded=False):
        for i, row in df.iterrows():
            st.markdown(f"**{row['Pergunta']}**")

            resposta = st.selectbox(
                "Resposta",
                ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                index=["Bom", "Médio", "Ruim", "Crítico", "NA"].index(row["Resposta"]),
                key=f"{aba}_{i}"
            )

            justificativa = row["Justificativa"]
            if resposta in ["Ruim", "Crítico"]:
                justificativa = st.text_input(
                    "Justificativa",
                    value=justificativa,
                    key=f"{aba}_{i}_j"
                )
            else:
                justificativa = ""

            df.at[i, "Resposta"] = resposta
            df.at[i, "Justificativa"] = justificativa

    st.session_state.avaliacoes[aba] = df

# ===============================
# AÇÕES
# ===============================
st.divider()

cabecalho = {
    "Projeto": nome_projeto,
    "Cliente": nome_cliente,
    "Responsável": responsavel,
    "Data": data_avaliacao.strftime("%d/%m/%Y"),
    "Hora": hora_avaliacao.strftime("%H:%M")
}

dados_atual = {
    aba: df.to_dict(orient="records")
    for aba, df in st.session_state.avaliacoes.items()
}

if st.button("💾 Salvar Avaliação"):
    chave = f"{data_avaliacao} {hora_avaliacao.strftime('%H:%M')}"
    st.session_state.avaliacoes_por_data[chave] = dados_atual
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success("Avaliação salva com sucesso.")

if st.button("📄 Gerar PDF"):
    gerar_pdf(cabecalho, dados_atual, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button(
            "⬇️ Download PDF",
            f,
            file_name="avaliacao.pdf",
            mime="application/pdf"
        )
