import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ======================================================
# CONFIG
# ======================================================
st.set_page_config("Painel Administração Contratual", layout="wide")

ARQ_AVALIACOES = "avaliacoes.json"

SEMAFORO = {
    "Bom": "🟢",
    "Médio": "🟡",
    "Ruim": "🟠",
    "Crítico": "🔴",
    "NA": "⚪"
}

VALORES = {
    "Bom": 0.0,
    "Médio": 0.3333,
    "Ruim": 0.6667,
    "Crítico": 1.0
}

# ======================================================
# PERSISTÊNCIA
# ======================================================
def carregar_avaliacoes():
    if os.path.exists(ARQ_AVALIACOES):
        with open(ARQ_AVALIACOES, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_avaliacoes(dados):
    with open(ARQ_AVALIACOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# ======================================================
# FUNÇÕES DE CÁLCULO
# ======================================================
def calcular_status(df):
    df = df[df["Resposta"] != "NA"].copy()
    if df.empty:
        return "NA"
    df["valor"] = df["Resposta"].map(VALORES)
    media = (df["valor"] * df["Peso"]).sum() / df["Peso"].sum()

    if media <= 0.25:
        return "Bom"
    elif media <= 0.50:
        return "Médio"
    elif media < 0.75:
        return "Ruim"
    else:
        return "Crítico"

# ======================================================
# PDF
# ======================================================
def gerar_pdf(cabecalho, dados, nome_arquivo):
    c = canvas.Canvas(nome_arquivo, pagesize=A4)
    w, h = A4
    y = h - 40
    pagina = 1

    def rodape():
        c.setFont("Helvetica", 8)
        c.drawRightString(w - 40, 20, f"Página {pagina}")

    # ---------- CAPA / RESUMO ----------
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Resumo Geral")
    y -= 30

    for campo, valor in cabecalho.items():
        c.setFont("Helvetica", 10)
        c.drawString(40, y, f"{campo}: {valor}")
        y -= 14

    y -= 20

    for fase, grupos in dados.items():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, fase)
        y -= 18

        for grupo, disciplinas in grupos.items():
            c.setFont("Helvetica-Bold", 10)
            c.drawString(60, y, grupo)
            y -= 16

            for d in disciplinas:
                c.setFont("Helvetica", 10)
                texto = f"{SEMAFORO[d['status']]} {d['codigo']} – {d['descricao']}"
                c.drawString(80, y, texto)
                y -= 14

                if y < 80:
                    rodape()
                    c.showPage()
                    pagina += 1
                    y = h - 40

    rodape()
    c.showPage()
    pagina += 1
    y = h - 40

    # ---------- JUSTIFICATIVAS ----------
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Justificativas")
    y -= 30

    for fase, grupos in dados.items():
        for grupo, disciplinas in grupos.items():
            for d in disciplinas:
                if not d["justificativas"]:
                    continue

                c.setFont("Helvetica-Bold", 10)
                c.drawString(40, y, f"{SEMAFORO[d['status']]} {fase} / {grupo} / {d['codigo']} – {d['descricao']}")
                y -= 16

                for j in d["justificativas"]:
                    c.setFont("Helvetica", 9)
                    c.drawString(60, y, f"- ({j['tipo']}) {j['texto']}")
                    y -= 14

                    if y < 80:
                        rodape()
                        c.showPage()
                        pagina += 1
                        y = h - 40

                y -= 10

    rodape()
    c.save()

# ======================================================
# ESTADO
# ======================================================
if "avaliacoes_salvas" not in st.session_state:
    st.session_state.avaliacoes_salvas = carregar_avaliacoes()

if "avaliacao_atual" not in st.session_state:
    st.session_state.avaliacao_atual = {}

# ======================================================
# INTERFACE
# ======================================================
st.title("Painel Administração Contratual")

st.markdown("### Cabeçalho da Avaliação")
col1, col2, col3 = st.columns(3)
nome_projeto = col1.text_input("Projeto")
cliente = col2.text_input("Cliente")
responsavel = col3.text_input("Responsável")

data = st.date_input("Data", datetime.now().date())
hora = st.time_input("Hora", (datetime.utcnow() - timedelta(hours=3)).time())

st.divider()

modo = st.radio("Modo", ["Nova Avaliação", "Abrir Avaliação Existente"], horizontal=True)

# ======================================================
# ABRIR AVALIAÇÃO EXISTENTE
# ======================================================
if modo == "Abrir Avaliação Existente":
    if not st.session_state.avaliacoes_salvas:
        st.info("Nenhuma avaliação salva.")
        st.stop()

    chave = st.selectbox("Selecione a avaliação", list(st.session_state.avaliacoes_salvas.keys()))
    st.session_state.avaliacao_atual = st.session_state.avaliacoes_salvas[chave]

# ======================================================
# UPLOAD EXCEL
# ======================================================
uploaded = st.file_uploader("Upload do Excel", type=["xlsx"])
if not uploaded:
    st.stop()

df = pd.read_excel(uploaded)

# ======================================================
# CANVAS
# ======================================================
for (fase, grupo, codigo, descricao), base in df.groupby(["Fase", "Grupo", "Codigo", "Descricao"]):
    if codigo not in st.session_state.avaliacao_atual:
        st.session_state.avaliacao_atual[codigo] = base.assign(Resposta="NA", Justificativa="")

    atual = st.session_state.avaliacao_atual[codigo]
    status = calcular_status(atual)
    icone = SEMAFORO[status]

    with st.expander(f"{icone} {codigo} – {descricao}", expanded=False):
        for tipo, bloco in atual.groupby("Tipo"):
            st.markdown(f"**{tipo}**")
            for i, r in bloco.iterrows():
                resp = st.selectbox(
                    r["Pergunta"],
                    ["Bom", "Médio", "Ruim", "Crítico", "NA"],
                    index=["Bom", "Médio", "Ruim", "Crítico", "NA"].index(r["Resposta"]),
                    key=f"{codigo}_{i}"
                )
                atual.at[i, "Resposta"] = resp

                if resp in ["Ruim", "Crítico"]:
                    txt = st.text_input("Justificativa", atual.at[i, "Justificativa"], key=f"j_{codigo}_{i}")
                    atual.at[i, "Justificativa"] = txt

# ======================================================
# SALVAR
# ======================================================
if st.button("💾 Salvar Avaliação"):
    chave = f"{data} {hora.strftime('%H:%M')}"
    serial = {}
    for k, v in st.session_state.avaliacao_atual.items():
        serial[k] = v.to_dict(orient="records")

    st.session_state.avaliacoes_salvas[chave] = serial
    salvar_avaliacoes(st.session_state.avaliacoes_salvas)
    st.success("Avaliação salva.")

# ======================================================
# GERAR PDF
# ======================================================
if st.button("📄 Gerar PDF"):
    estrutura = {}

    for codigo, registros in st.session_state.avaliacao_atual.items():
        dfc = pd.DataFrame(registros)
        fase = dfc.iloc[0]["Fase"]
        grupo = dfc.iloc[0]["Grupo"]
        descricao = dfc.iloc[0]["Descricao"]
        status = calcular_status(dfc)

        justs = []
        for _, r in dfc.iterrows():
            if r["Justificativa"]:
                justs.append({"tipo": r["Tipo"], "texto": r["Justificativa"]})

        estrutura.setdefault(fase, {}).setdefault(grupo, []).append({
            "codigo": codigo,
            "descricao": descricao,
            "status": status,
            "justificativas": justs
        })

    cab = {
        "Projeto": nome_projeto,
        "Cliente": cliente,
        "Responsável": responsavel,
        "Data": data.strftime("%d/%m/%Y"),
        "Hora": hora.strftime("%H:%M")
    }

    gerar_pdf(cab, estrutura, "avaliacao.pdf")
    with open("avaliacao.pdf", "rb") as f:
        st.download_button("⬇️ Download PDF", f, file_name="avaliacao.pdf")
