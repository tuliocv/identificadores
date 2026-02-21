import re
import unicodedata
import streamlit as st
import random

# =====================================================
# CONFIGURAÇÃO
# =====================================================
st.set_page_config(page_title="Jogo de Identificadores", page_icon="🎮", layout="centered")

st.title("🎮 Jogo: Classificação de Identificadores")
st.caption("Classifique corretamente o identificador. Se for inválido ou má prática, justifique.")

# =====================================================
# REGRAS DIDÁTICAS
# =====================================================
GENERICOS = {"a", "b", "c", "x", "y", "z", "n", "m", "i", "j", "k"}

def has_accent(text):
    return unicodedata.normalize("NFKD", text) != text

def is_valid_identifier(name):
    pattern = r"^[A-Za-z_][A-Za-z0-9_]*$"
    return bool(re.match(pattern, name)) and not has_accent(name)

def is_bad_practice(name):
    if name in GENERICOS:
        return True
    if len(name) <= 2 and name.isalpha():
        return True
    return False

def analyze(name):
    reasons = []
    if name[0].isdigit():
        reasons.append("Começa com número")
    if " " in name:
        reasons.append("Possui espaço")
    if has_accent(name):
        reasons.append("Possui acento (não ASCII)")
    if re.search(r"[^A-Za-z0-9_ ]", name):
        reasons.append("Possui símbolo inválido (+ - * / % etc)")
    if is_valid_identifier(name) and is_bad_practice(name):
        reasons.append("Nome pouco descritivo")
    return reasons

# =====================================================
# 30 IDENTIFICADORES
# =====================================================
IDENTIFICADORES = [
    "base", "altura", "_altura", "_altura1", "parede3lados",
    "parede_reta", "ParedeReta04", "3base", "altura principal",
    "altura1+", "triângulo", "a", "x", "m",
    "areaTriangulo", "baseTriangulo", "alturaTriangulo",
    "mediaFinal", "notaA1", "notaA2",
    "notaA3", "2nota", "salárioBruto",
    "salarioLiquido", "valor-total", "valorTotal",
    "numero1", "numero_2", "Idade", "i"
]

random.shuffle(IDENTIFICADORES)

# =====================================================
# ESTADO
# =====================================================
if "index" not in st.session_state:
    st.session_state.index = 0
    st.session_state.score = 0
    st.session_state.finished = False

total = len(IDENTIFICADORES)

# =====================================================
# FIM DO JOGO
# =====================================================
if st.session_state.index >= total:
    st.session_state.finished = True

if st.session_state.finished:
    st.success(f"🎉 Fim do jogo! Pontuação: {st.session_state.score} / {total}")
    percentual = (st.session_state.score / total) * 100
    st.metric("Desempenho (%)", f"{percentual:.1f}%")

    if st.button("🔁 Jogar novamente"):
        st.session_state.index = 0
        st.session_state.score = 0
        st.session_state.finished = False
        random.shuffle(IDENTIFICADORES)
        st.rerun()

    st.stop()

# =====================================================
# JOGO
# =====================================================
identificador = IDENTIFICADORES[st.session_state.index]

st.progress(st.session_state.index / total)
st.subheader(f"Identificador: `{identificador}`")

resposta = st.radio(
    "Classifique:",
    ["✅ Válido", "❌ Inválido", "⚠️ Válido, mas má prática"]
)

justificativa = ""

if resposta in ["❌ Inválido", "⚠️ Válido, mas má prática"]:
    justificativa = st.text_area("Justifique sua resposta:")

if st.button("Confirmar"):
    valido = is_valid_identifier(identificador)
    ma_pratica = valido and is_bad_practice(identificador)

    # Determinar gabarito
    if valido and not ma_pratica:
        gabarito = "✅ Válido"
    elif valido and ma_pratica:
        gabarito = "⚠️ Válido, mas má prática"
    else:
        gabarito = "❌ Inválido"

    # Verificar justificativa obrigatória
    if resposta in ["❌ Inválido", "⚠️ Válido, mas má prática"] and justificativa.strip() == "":
        st.warning("⚠️ Você precisa justificar sua resposta.")
        st.stop()

    # Pontuação
    if resposta == gabarito:
        st.success("✅ Correto!")
        st.session_state.score += 1
    else:
        st.error(f"❌ Incorreto. O correto era: {gabarito}")

    # Mostrar análise automática
    st.info("📌 Análise do sistema:")
    motivos = analyze(identificador)

    if not motivos:
        st.write("Identificador válido e bem estruturado.")
    else:
        for m in motivos:
            st.write(f"- {m}")

    st.session_state.index += 1

    if st.session_state.index < total:
        if st.button("➡️ Avançar"):
            st.rerun()
