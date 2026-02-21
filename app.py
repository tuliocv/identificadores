import re
import unicodedata
import streamlit as st
import random

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Jogo de Identificadores", page_icon="🎮", layout="centered")
st.title("🎮 Jogo: Classificação de Identificadores")
st.caption("Classifique o identificador. Se for ❌ inválido ou ⚠️ má prática, justifique marcando opções.")

# =====================================================
# REGRAS DIDÁTICAS
# =====================================================
GENERICOS = {"a", "b", "c", "x", "y", "z", "n", "m", "i", "j", "k"}

def has_accent(text: str) -> bool:
    return unicodedata.normalize("NFKD", text) != text

def is_valid_identifier(name: str) -> bool:
    pattern = r"^[A-Za-z_][A-Za-z0-9_]*$"
    return bool(re.match(pattern, name)) and not has_accent(name)

def is_bad_practice(name: str) -> bool:
    if name in GENERICOS:
        return True
    if len(name) <= 2 and name.isalpha():
        return True
    return False

def compute_gabarito(name: str) -> str:
    valido = is_valid_identifier(name)
    ma_pratica = valido and is_bad_practice(name)
    if valido and not ma_pratica:
        return "✅ Válido"
    if valido and ma_pratica:
        return "⚠️ Válido, mas má prática"
    return "❌ Inválido"

def expected_reasons(name: str) -> set[str]:
    reasons = set()
    if not name:
        reasons.add("vazio")
        return reasons
    if name[0].isdigit():
        reasons.add("começa com número")
    if " " in name:
        reasons.add("tem espaço")
    if has_accent(name):
        reasons.add("tem acento (não ASCII)")
    if re.search(r"[^A-Za-z0-9_ ]", name):
        reasons.add("tem símbolo/operador inválido")
    if is_valid_identifier(name) and is_bad_practice(name):
        reasons.add("pouco descritivo / genérico")
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

# =====================================================
# OPÇÕES DE JUSTIFICATIVA
# =====================================================
JUSTIFICATIVAS_INVALIDO = [
    "Começa com número",
    "Tem espaço",
    "Tem acento (não ASCII)",
    "Tem símbolo/operador inválido (+, -, *, /, %, etc.)",
]

JUSTIFICATIVAS_MA_PRATICA = [
    "É genérico (uma letra ou nome pouco informativo)",
    "É abreviação confusa",
    "Não descreve o que armazena",
]

# =====================================================
# ESTADO
# =====================================================
def reset_game():
    ordem = IDENTIFICADORES[:]
    random.shuffle(ordem)
    st.session_state.ordem = ordem
    st.session_state.index = 0
    st.session_state.score = 0
    st.session_state.show_feedback = False
    st.session_state.last_answer_correct = None
    st.session_state.last_gabarito = None
    st.session_state.last_reasons = None
    st.session_state.last_selected_ok = None

if "ordem" not in st.session_state:
    reset_game()

if "show_feedback" not in st.session_state:
    st.session_state.show_feedback = False

total = len(st.session_state.ordem)

# =====================================================
# FIM DO JOGO
# =====================================================
if st.session_state.index >= total:
    st.success(f"🎉 Fim do jogo! Pontuação: **{st.session_state.score} / {total}**")
    percentual = (st.session_state.score / total) * 100
    st.metric("Desempenho", f"{percentual:.1f}%")

    if st.button("🔁 Jogar novamente"):
        reset_game()
        st.rerun()
    st.stop()

# =====================================================
# QUESTÃO ATUAL
# =====================================================
ident = st.session_state.ordem[st.session_state.index]
gabarito = compute_gabarito(ident)

st.progress(st.session_state.index / total)
st.subheader(f"Identificador: `{ident}`")

# Enquanto estiver mostrando feedback, travamos inputs (para evitar mudar resposta depois)
disabled_inputs = st.session_state.show_feedback

resposta = st.radio(
    "Classifique:",
    ["✅ Válido", "❌ Inválido", "⚠️ Válido, mas má prática"],
    index=0,
    disabled=disabled_inputs,
)

selecionadas = []
if resposta == "❌ Inválido":
    st.markdown("**Justifique (marque ao menos 1 opção):**")
    selecionadas = st.multiselect("Motivos:", JUSTIFICATIVAS_INVALIDO, disabled=disabled_inputs)
elif resposta == "⚠️ Válido, mas má prática":
    st.markdown("**Justifique (marque ao menos 1 opção):**")
    selecionadas = st.multiselect("Motivos:", JUSTIFICATIVAS_MA_PRATICA, disabled=disabled_inputs)

# =====================================================
# CONFIRMAR (sem callback)
# =====================================================
if not st.session_state.show_feedback:
    if st.button("✅ Confirmar"):
        # justificativa obrigatória
        if resposta in ["❌ Inválido", "⚠️ Válido, mas má prática"] and len(selecionadas) == 0:
            st.warning("⚠️ Você precisa justificar marcando ao menos 1 opção.")
            st.stop()

        correto = (resposta == gabarito)
        if correto:
            st.session_state.score += 1

        st.session_state.last_answer_correct = correto
        st.session_state.last_gabarito = gabarito
        st.session_state.last_reasons = expected_reasons(ident)

        # (opcional) checar se justificativa bate com motivo esperado (apenas alerta)
        last_selected_ok = True
        if resposta == "❌ Inválido":
            motivos = st.session_state.last_reasons
            selected_keys = set()
            for s in selecionadas:
                if "número" in s:
                    selected_keys.add("começa com número")
                if "espaço" in s:
                    selected_keys.add("tem espaço")
                if "acento" in s:
                    selected_keys.add("tem acento (não ASCII)")
                if "símbolo" in s or "operador" in s:
                    selected_keys.add("tem símbolo/operador inválido")
            if len(selected_keys.intersection(motivos)) == 0:
                last_selected_ok = False

        st.session_state.last_selected_ok = last_selected_ok
        st.session_state.show_feedback = True
        st.rerun()

# =====================================================
# FEEDBACK (após confirmar)
# =====================================================
if st.session_state.show_feedback:
    if st.session_state.last_answer_correct:
        st.success("✅ Correto!")
    else:
        st.error(f"❌ Incorreto. O correto era: **{st.session_state.last_gabarito}**")

    st.info("📌 Feedback pelas regras do sistema:")
    motivos = st.session_state.last_reasons

    if gabarito == "✅ Válido":
        st.write("- Identificador **válido** e **bem estruturado**.")
    elif gabarito == "⚠️ Válido, mas má prática":
        st.write("- Identificador **válido**, mas **má prática** (geralmente pouco descritivo).")
    else:
        mapa = {
            "começa com número": "Começa com número",
            "tem espaço": "Tem espaço",
            "tem acento (não ASCII)": "Tem acento (não ASCII)",
            "tem símbolo/operador inválido": "Tem símbolo/operador inválido (+, -, *, /, %, etc.)",
        }
        for key, label in mapa.items():
            if key in motivos:
                st.write(f"- {label}")

    if (gabarito == "❌ Inválido") and (st.session_state.last_selected_ok is False):
        st.warning("🟡 Sua justificativa não bateu com a regra violada (confira os motivos acima).")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Pontuação", f"{st.session_state.score} / {total}")
    with col2:
        st.metric("Questão", f"{st.session_state.index + 1} / {total}")

    if st.button("➡️ Próximo"):
        st.session_state.index += 1
        st.session_state.show_feedback = False
        st.session_state.last_answer_correct = None
        st.session_state.last_gabarito = None
        st.session_state.last_reasons = None
        st.session_state.last_selected_ok = None
        st.rerun()
