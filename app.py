import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ======================================================
# CONFIGURAÇÃO
# ======================================================
st.set_page_config("Painel Administração Contratual", layout="wide")
ARQUIVO_AVALIACOES = "avaliacoes.json"

# ======================================================
# PERSISTÊNCIA
# ======================================================
def salvar_avaliacoes(dados):
    with open(ARQUIVO_AVALIACOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_avaliacoes():
    if os.path.exists(ARQUIVO_AVALIACOES):
        with open(ARQUIVO_AVALIACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ======================================================
# REGRAS DE NEGÓCIO
# ======================================================
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

def semaforo(nota):
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

# ======================================================
# PDF
# ======================================================
def gerar_pdf(cabecalho, canvas_disciplinas, justificativas):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    # -------- Página 1 | Canvas --------
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, h - 40, "Painel Administração Contratual")

    pdf.setFont("Helvetica", 10)
    y = h - 80
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
    for item in canvas_disciplinas:
        pdf.drawString(
            60, y,
            f"{item['semaforo']}  {item['codigo']} – {item['descricao']}"
        )
        y -= 18
        if y < 60:
            pdf.showPage()
            y = h - 60

    # -------- Página 2 | Justificativas --------
    pdf.showPage()
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, h - 40, "Justificativas (Ruim / Crítico)")

    y = h - 80
    pdf.setFont("Helvetica", 11)

    if not justificativas:
        pdf.drawString(40, y, "Nenhuma justificativa registrada.")
    else:
        for j in justificativas:
            pdf.drawString(40, y, f"{j['codigo']} – {j['descricao']}")
            y -= 15
            texto = pdf.beginText(60, y)
            texto.textLines(j["texto"])
            pdf.drawText(texto)
            y = texto.getY() - 20
            if y < 60:
                pdf.showPage()
                y = h - 60

    pdf.save()
    buffer.seek(0)
    return buffer.read()

# ======================================================
# ESTADO
# ======================================================
if "avaliacoes_por_data" not in st.session_state:
    st.session_state.avaliacoes_por_data = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {}

# ======================================================
# INTERFACE
# ======================================================
st.title("Painel Administração Contratual")

# Cabeçalho
st.markdown("### Dados do Empreendimento")
c1, c2, c3 = st.columns(3)
with c1:
    nome_projeto = st.text_input("Nome do Projeto")
with c2:
    nome_cliente = st.text_input("Nome do Cliente")
with c3:
    responsavel = st.text_input("Responsável")

st.markdown("### Data da Avaliação")
c4, c5 = st.columns(2)
with c4:
    data_avaliacao = st.date_input("Data", datetime.now().date())
with c5:
    hora_avaliacao = st.time_input(
        "Hora",
        (datetime.utcnow() - timedelta(hours=3)).time()
    )

modo = st.radio(
    "O que deseja fazer?",
    ["Nova Avaliação", "Abrir Avaliação Existente"],
    horizontal=True
)

# ======================================================
# ABRIR AVALIAÇÃO
# ======================================================
data_selecionada = None
if modo == "Abrir Avaliação Existente":

    if not st.session_state.avaliacoes_por_data:
        st.info("ℹ️ Nenhuma avaliação salva.")
        st.stop()

    data_selecionada = st.selectbox(
        "Selecione a avaliação",
        sorted(st.session_state.avaliacoes_por_data.keys(), reverse=True)
    )

    if st.button("📂 Abrir Avaliação"):
        st.session_state.avaliacao_atual = {
            aba: pd.DataFrame(reg)
            for aba, reg in st.session_state.avaliacoes_por_data[data_selecionada].items()
        }
        st.success("Avaliação carregada.")

# ======================================================
# UPLOAD EXCEL
# ======================================================
uploaded_file = st.file_uploader("Carregar Excel do Projeto", type=["xlsx"])
if not uploaded_file:
    st.stop()

xls = pd.ExcelFile(uploaded_file)

# ======================================================
# CANVAS
# ======================================================
st.subheader("Canvas do Projeto")

for aba in xls.sheet_names:
    base = xls.parse(aba)

    if aba not in st.session_state.avaliacao_atual:
        base["Resposta"] = "NA"
        base["Justificativa"] = ""
        st.session_state.avaliacao_atual[aba] = base
    else:
        base = st.session_state.avaliacao_atual[aba]

    nota = calcular_media_ponderada(base)
    icone = semaforo(nota)

    codigo = base.iloc[0]["CodigoDisciplina"]
    descricao = base.iloc[0]["DescricaoDisciplina"]

    with st.expander(f"{icone} {codigo} – {descricao}", expanded=False):
        for i, row in base.iterrows():
            st.markdown(f"**{row['Pergunta']}**")

            resp = st.selectbox(
                "Avaliação",
                ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                index=["Bom", "Médio", "Ruim", "Crítico", "NA"].index(row["Resposta"]),
                key=f"{aba}_{i}"
            )

            just = row["Justificativa"]
            if resp in ["Ruim", "Crítico"]:
                just = st.text_input(
                    "Justificativa",
                    value=just,
                    key=f"{aba}_{i}_j"
                )

            base.at[i, "Resposta"] = resp
            base.at[i, "Justificativa"] = just

        st.session_state.avaliacao_atual[aba] = base

# ======================================================
# SALVAR
# ======================================================
st.divider()
if st.button("💾 Salvar Avaliação"):
    chave = f"{data_avaliacao.strftime('%Y-%m-%d')} {hora_avaliacao.strftime('%H:%M')}"

    st.session_state.avaliacoes_por_data[chave] = {
        aba: df.to_dict(orient="records")
        for aba, df in st.session_state.avaliacao_atual.items()
    }

    salvar_avaliacoes(st.session_state.avaliacoes_por_data)
    st.success(f"Avaliação salva em {chave}")

# ======================================================
# PDF
# ======================================================
if modo == "Abrir Avaliação Existente" and data_selecionada:

    if st.button("📄 Gerar PDF da Avaliação"):
        canvas_pdf = []
        justificativas_pdf = []

        for aba, df in st.session_state.avaliacao_atual.items():
            nota = calcular_media_ponderada(df)
            canvas_pdf.append({
                "codigo": df.iloc[0]["CodigoDisciplina"],
                "descricao": df.iloc[0]["DescricaoDisciplina"],
                "semaforo": semaforo(nota)
            })

            for _, r in df.iterrows():
                if r["Resposta"] in ["Ruim", "Crítico"] and r["Justificativa"]:
                    justificativas_pdf.append({
                        "codigo": df.iloc[0]["CodigoDisciplina"],
                        "descricao": df.iloc[0]["DescricaoDisciplina"],
                        "texto": r["Justificativa"]
                    })

        cabecalho = {
            "projeto": nome_projeto,
            "cliente": nome_cliente,
            "responsavel": responsavel,
            "data": data_selecionada
        }

        pdf = gerar_pdf(cabecalho, canvas_pdf, justificativas_pdf)

        st.download_button(
            "⬇️ Download PDF",
            data=pdf,
            file_name=f"Avaliacao_{data_selecionada}.pdf",
            mime="application/pdf"
        )
