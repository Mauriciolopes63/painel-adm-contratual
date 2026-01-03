import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ===============================
# ARQUIVOS
# ===============================
AVALIACOES_FILE = "avaliacoes.json"

# ===============================
# PERSISTÊNCIA
# ===============================
def salvar_avaliacoes(dados):
    with open(AVALIACOES_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_avaliacoes():
    if os.path.exists(AVALIACOES_FILE):
        with open(AVALIACOES_FILE, "r", encoding="utf-8") as f:
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

    return soma / peso_total if peso_total > 0 else None

def semaforo_por_nota(nota):
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

# ===============================
# PDF
# ===============================
def gerar_pdf(cabecalho, canvas_resultados, justificativas):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Página 1 – Canvas
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, height - 40, "Painel Administração Contratual")

    pdf.setFont("Helvetica", 10)
    y = height - 80
    pdf.drawString(40, y, f"Projeto: {cabecalho['projeto']}")
    y -= 15
    pdf.drawString(40, y, f"Cliente: {cabecalho['cliente']}")
    y -= 15
    pdf.drawString(40, y, f"Responsável: {cabecalho['responsavel']}")
    y -= 15
    pdf.drawString(40, y, f"Data da Avaliação: {cabecalho['data']}")

    y -= 40
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y, "Canvas da Avaliação")
    y -= 25

    pdf.setFont("Helvetica", 11)
    for disciplina, semaforo in canvas_resultados.items():
        pdf.drawString(60, y, f"{semaforo}  {disciplina}")
        y -= 18
        if y < 60:
            pdf.showPage()
            y = height - 60

    # Página 2 – Justificativas
    pdf.showPage()
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, height - 40, "Justificativas (Ruim / Crítico)")

    y = height - 80
    pdf.setFont("Helvetica", 11)

    if not justificativas:
        pdf.drawString(40, y, "Nenhuma justificativa registrada.")
    else:
        for item in justificativas:
            pdf.drawString(40, y, f"{item['disciplina']}:")
            y -= 15
            text = pdf.beginText(60, y)
            text.textLines(item["texto"])
            pdf.drawText(text)
            y = text.getY() - 20
            if y < 60:
                pdf.showPage()
                y = height - 60

    pdf.save()
    buffer.seek(0)
    return buffer.read()

# ===============================
# APP
# ===============================
st.set_page_config("Painel Administração Contratual", layout="wide")

if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacoes" not in st.session_state:
    st.session_state.avaliacoes = {}

st.title("Painel Administração Contratual")

# ===============================
# CABEÇALHO
# ===============================
st.markdown("### Dados do Empreendimento")

col1, col2, col3 = st.columns(3)
with col1:
    nome_projeto = st.text_input("Nome do Projeto")
with col2:
    nome_cliente = st.text_input("Nome do Cliente")
with col3:
    responsavel = st.text_input("Responsável")

st.markdown("### Data da Avaliação")
col4, col5 = st.columns(2)
with col4:
    data_avaliacao = st.date_input("Data", datetime.now().date())
with col5:
    hora_avaliacao = st.time_input(
        "Hora",
        (datetime.utcnow() - timedelta(hours=3)).time()
    )

# ===============================
# MODO
# ===============================
modo = st.radio(
    "O que deseja fazer?",
    ["Nova Avaliação", "Abrir Avaliação Existente"],
    horizontal=True
)

# ===============================
# ABRIR AVALIAÇÃO
# ===============================
if modo == "Abrir Avaliação Existente":

    if not st.session_state.avaliacoes_por_data:
        st.info("ℹ️ Ainda não existem avaliações salvas.")
        st.stop()

    data_selecionada = st.selectbox(
        "Selecione a avaliação",
        sorted(st.session_state.avaliacoes_por_data.keys(), reverse=True)
    )

    if st.button("📂 Abrir Avaliação"):
        st.session_state.avaliacoes = {}
        for aba, registros in st.session_state.avaliacoes_por_data[data_selecionada].items():
            st.session_state.avaliacoes[aba] = pd.DataFrame(registros)

        st.success(f"Avaliação {data_selecionada} carregada.")

# ===============================
# UPLOAD EXCEL
# ===============================
uploaded_file = st.file_uploader(
    "Carregar Excel do Projeto",
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
    df_base = xls.parse(aba)

    if aba not in st.session_state.avaliacoes:
        df_base["Resposta"] = "NA"
        df_base["Justificativa"] = ""
        st.session_state.avaliacoes[aba] = df_base
    else:
        df_base = st.session_state.avaliacoes[aba]

    nota = calcular_media_ponderada(df_base)
    semaforo = semaforo_por_nota(nota)

    with st.expander(f"{semaforo} {aba}", expanded=False):

        for i, row in df_base.iterrows():
            st.markdown(f"**{row['Pergunta']}**")

            resposta = st.selectbox(
                "Avaliação",
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

            df_base.at[i, "Resposta"] = resposta
            df_base.at[i, "Justificativa"] = justificativa

        st.session_state.avaliacoes[aba] = df_base

# ===============================
# SALVAR
# ===============================
st.divider()

if st.button("💾 Salvar Avaliação"):
    chave = f"{data_avaliacao.strftime('%Y-%m-%d')} {hora_avaliacao.strftime('%H:%M')}"

    dados = {}
    for aba, df in st.session_state.avaliacoes.items():
        dados[aba] = df.to_dict(orient="records")

    st.session_state.avaliacoes_por_data[chave] = dados
    salvar_avaliacoes(st.session_state.avaliacoes_por_data)

    st.success(f"Avaliação salva em {chave}")

# ===============================
# PDF
# ===============================
st.divider()

if modo == "Abrir Avaliação Existente" and st.session_state.avaliacoes:

    if st.button("📄 Gerar PDF da Avaliação"):
        canvas_resultados = {}
        justificativas = []

        for aba, df in st.session_state.avaliacoes.items():
            nota = calcular_media_ponderada(df)
            canvas_resultados[aba] = semaforo_por_nota(nota)

            for _, row in df.iterrows():
                if row["Resposta"] in ["Ruim", "Crítico"] and row["Justificativa"]:
                    justificativas.append({
                        "disciplina": aba,
                        "texto": row["Justificativa"]
                    })

        cabecalho = {
            "projeto": nome_projeto,
            "cliente": nome_cliente,
            "responsavel": responsavel,
            "data": data_selecionada
        }

        pdf = gerar_pdf(cabecalho, canvas_resultados, justificativas)

        st.download_button(
            "⬇️ Download PDF",
            data=pdf,
            file_name=f"Avaliacao_{data_selecionada}.pdf",
            mime="application/pdf"
        )
