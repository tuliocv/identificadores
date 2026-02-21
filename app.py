import os
import re
import csv
import time
import random
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Jogo de Identificadores", page_icon="🎮", layout="centered")
st.title("🎮 Jogo: Classificação de Identificadores")
st.caption("Aluno: informe seu nome para iniciar. Admin: login para ver rankings (top 10 / bottom 10).")

# =========================
# ADMIN CREDENTIALS
# =========================
# Recomendado: .streamlit/secrets.toml
# [admin]
# user = "prof"
# pass = "senha_forte"
def get_admin_credentials():
    user = None
    pwd = None
    try:
        user = st.secrets["admin"]["user"]
        pwd = st.secrets["admin"]["pass"]
    except Exception:
        # fallback local (opcional)
        user = os.getenv("ADMIN_USER", "admin")
        pwd = os.getenv("ADMIN_PASS", "admin")
    return user, pwd

ADMIN_USER, ADMIN_PASS = get_admin_credentials()

# =========================
# STORAGE (CSV)
# =========================
DATA_DIR = Path("data")
SCORES_FILE = DATA_DIR / "scores.csv"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CSV_HEADERS = ["timestamp_utc", "student_name", "score", "total", "percent"]

def ensure_scores_file():
    if not SCORES_FILE.exists():
        with open(SCORES_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)

def load_scores():
    ensure_scores_file()
    rows = []
    with open(SCORES_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # normaliza tipos
            try:
                row["score"] = int(row["score"])
                row["total"] = int(row["total"])
                row["percent"] = float(row["percent"])
            except Exception:
                continue
            rows.append(row)
    return rows

def append_score(student_name: str, score: int, total: int):
    ensure_scores_file()
    percent = (score / total) * 100 if total else 0.0
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with open(SCORES_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([ts, student_name, score, total, f"{percent:.2f}"])

# =========================
# RULES (didáticas)
# =========================
GENERICOS = {"a", "b", "c", "x", "y", "z", "n", "m", "i", "j", "k"}

def has_accent(text: str) -> bool:
    return unicodedata.normalize("NFKD", text) != text

def is_valid_identifier(name: str) -> bool:
    # padrão didático: começa com letra ou '_' e segue com letras/números/'_'; sem acento
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

# =========================
# 30 IDENTIFICADORES
# =========================
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

# Justificativas (lista fixa)
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

# =========================
# SESSION STATE
# =========================
def reset_game_order():
    ordem = IDENTIFICADORES[:]
    random.shuffle(ordem)
    st.session_state.ordem = ordem

def reset_game_progress():
    st.session_state.index = 0
    st.session_state.score = 0
    st.session_state.show_feedback = False
    st.session_state.last_answer_correct = None
    st.session_state.last_gabarito = None
    st.session_state.last_reasons = None
    st.session_state.last_selected_ok = None
    st.session_state.saved_score = False

if "role" not in st.session_state:
    st.session_state.role = None  # "student" ou "admin"
if "student_name" not in st.session_state:
    st.session_state.student_name = ""
if "admin_authed" not in st.session_state:
    st.session_state.admin_authed = False

if "ordem" not in st.session_state:
    reset_game_order()
if "index" not in st.session_state:
    reset_game_progress()

# =========================
# NAV: Student | Admin
# =========================
tab_student, tab_admin = st.tabs(["👤 Aluno", "🔐 Admin"])

# ==========================================================
# STUDENT TAB
# ==========================================================
with tab_student:
    st.subheader("👤 Área do aluno")

    # Nome obrigatório para iniciar
    if not st.session_state.student_name:
        nome = st.text_input("Digite seu nome para iniciar:", placeholder="Ex.: Maria Silva")
        if st.button("🚀 Iniciar jogo"):
            nome_limpo = (nome or "").strip()
            if len(nome_limpo) < 3:
                st.warning("⚠️ Informe um nome com pelo menos 3 caracteres.")
                st.stop()
            st.session_state.student_name = nome_limpo
            reset_game_order()
            reset_game_progress()
            st.rerun()
        st.stop()

    # Cabeçalho do aluno
    st.success(f"Aluno: **{st.session_state.student_name}**")
    colA, colB = st.columns(2)
    with colA:
        st.metric("Pontuação", f"{st.session_state.score} / {len(st.session_state.ordem)}")
    with colB:
        st.metric("Questão", f"{st.session_state.index + 1} / {len(st.session_state.ordem)}")

    total = len(st.session_state.ordem)

    # Fim do jogo
    if st.session_state.index >= total:
        st.success("🎉 Jogo finalizado!")
        percent = (st.session_state.score / total) * 100
        st.metric("Desempenho (%)", f"{percent:.1f}%")

        # salvar apenas uma vez
        if not st.session_state.saved_score:
            append_score(st.session_state.student_name, st.session_state.score, total)
            st.session_state.saved_score = True

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔁 Jogar novamente"):
                reset_game_order()
                reset_game_progress()
                st.rerun()
        with col2:
            if st.button("👤 Trocar aluno"):
                st.session_state.student_name = ""
                reset_game_order()
                reset_game_progress()
                st.rerun()
        st.stop()

    # Questão atual
    ident = st.session_state.ordem[st.session_state.index]
    gabarito = compute_gabarito(ident)

    st.progress(st.session_state.index / total)
    st.markdown(f"### Identificador: `{ident}`")

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

    # Confirmar
    if not st.session_state.show_feedback:
        if st.button("✅ Confirmar"):
            if resposta in ["❌ Inválido", "⚠️ Válido, mas má prática"] and len(selecionadas) == 0:
                st.warning("⚠️ Você precisa justificar marcando ao menos 1 opção.")
                st.stop()

            correto = (resposta == gabarito)
            if correto:
                st.session_state.score += 1

            st.session_state.last_answer_correct = correto
            st.session_state.last_gabarito = gabarito
            st.session_state.last_reasons = expected_reasons(ident)

            # checagem leve de justificativa (apenas alerta)
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

    # Feedback + Próximo
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
        if st.button("➡️ Próximo"):
            st.session_state.index += 1
            st.session_state.show_feedback = False
            st.session_state.last_answer_correct = None
            st.session_state.last_gabarito = None
            st.session_state.last_reasons = None
            st.session_state.last_selected_ok = None
            st.rerun()

# ==========================================================
# ADMIN TAB
# ==========================================================
with tab_admin:
    st.subheader("🔐 Área do administrador")

    # Login
    if not st.session_state.admin_authed:
        user = st.text_input("Usuário", value="", placeholder="ex.: prof")
        pwd = st.text_input("Senha", value="", type="password", placeholder="sua senha")

        if st.button("🔓 Entrar"):
            if user == ADMIN_USER and pwd == ADMIN_PASS:
                st.session_state.admin_authed = True
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")
        st.info("Dica: configure usuário/senha em `.streamlit/secrets.toml` no GitHub/Cloud.")
        st.stop()

    # Admin logado
    st.success("✅ Admin autenticado.")
    if st.button("🚪 Sair (logout)"):
        st.session_state.admin_authed = False
        st.rerun()

    # Carregar dados
    rows = load_scores()
    if not rows:
        st.warning("Ainda não há pontuações registradas.")
        st.stop()

    # Melhor tentativa por aluno (pega a maior % ou maior score)
    best_by_student = {}
    for r in rows:
        name = r["student_name"].strip()
        if not name:
            continue
        # critério: maior percent; empate: maior score; empate: mais recente
        key = (r["percent"], r["score"], r["timestamp_utc"])
        if name not in best_by_student or key > (
            best_by_student[name]["percent"],
            best_by_student[name]["score"],
            best_by_student[name]["timestamp_utc"],
        ):
            best_by_student[name] = r

    best_list = list(best_by_student.values())

    # Ordenações
    top10 = sorted(best_list, key=lambda x: (x["percent"], x["score"], x["timestamp_utc"]), reverse=True)[:10]
    bottom10 = sorted(best_list, key=lambda x: (x["percent"], x["score"], x["timestamp_utc"]))[:10]

    st.markdown("### 🏆 Top 10 (melhores alunos)")
    st.dataframe(top10, use_container_width=True, hide_index=True)

    st.markdown("### 🧯 Bottom 10 (piores alunos)")
    st.dataframe(bottom10, use_container_width=True, hide_index=True)

    st.markdown("### 🕒 Últimos registros (raw)")
    last = sorted(rows, key=lambda x: x["timestamp_utc"], reverse=True)[:25]
    st.dataframe(last, use_container_width=True, hide_index=True)

    st.caption(f"Arquivo de armazenamento: `{SCORES_FILE.as_posix()}`")
