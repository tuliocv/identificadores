import os
import re
import csv
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
st.caption("Aluno: digite seu nome para iniciar.")


# =========================
# ADMIN CREDENTIALS
# =========================
# Recomendado: .streamlit/secrets.toml
# [admin]
# user = "prof"
# pass = "senha_forte"
def get_admin_credentials():
    try:
        user = st.secrets["admin"]["user"]
        pwd = st.secrets["admin"]["pass"]
        return user, pwd
    except Exception:
        # fallback local
        return os.getenv("ADMIN_USER", "admin"), os.getenv("ADMIN_PASS", "admin")


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
            csv.writer(f).writerow(CSV_HEADERS)


def load_scores():
    ensure_scores_file()
    rows = []
    with open(SCORES_FILE, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                row["score"] = int(row["score"])
                row["total"] = int(row["total"])
                row["percent"] = float(row["percent"])
                rows.append(row)
            except Exception:
                pass
    return rows


def append_score(student_name: str, score: int, total: int):
    ensure_scores_file()
    percent = (score / total) * 100 if total else 0.0
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with open(SCORES_FILE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([ts, student_name, score, total, f"{percent:.2f}"])


def clear_scores():
    if SCORES_FILE.exists():
        SCORES_FILE.unlink()
    ensure_scores_file()


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
# IDENTIFICADORES (30)
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
    st.session_state.saved_score = False


if "student_name" not in st.session_state:
    st.session_state.student_name = ""
if "admin_authed" not in st.session_state:
    st.session_state.admin_authed = False
if "confirm_clear" not in st.session_state:
    st.session_state.confirm_clear = False

if "ordem" not in st.session_state:
    reset_game()


# =========================
# NAV (Sidebar)
# =========================
st.sidebar.title("📌 Menu")
view = st.sidebar.radio("Ir para:", ["👤 Aluno", "🔐 Admin"], index=0)


# ==========================================================
# VIEW: STUDENT
# ==========================================================
if view == "👤 Aluno":
    st.subheader("👤 Área do aluno")
    st.caption("Digite seu nome para iniciar o jogo.")

    if not st.session_state.student_name:
        nome = st.text_input("Nome do aluno:", placeholder="Ex.: Maria Silva")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🚀 Iniciar"):
                nome_limpo = (nome or "").strip()
                if len(nome_limpo) < 3:
                    st.warning("⚠️ Informe um nome com pelo menos 3 caracteres.")
                else:
                    st.session_state.student_name = nome_limpo
                    reset_game()
                    st.rerun()

        with col2:
            if st.button("🧹 Limpar"):
                st.session_state.student_name = ""
                reset_game()
                st.rerun()

    else:
        total = len(st.session_state.ordem)

        st.success(f"Aluno: **{st.session_state.student_name}**")
        colA, colB = st.columns(2)
        with colA:
            st.metric("Pontuação", f"{st.session_state.score} / {total}")
        with colB:
            st.metric("Questão", f"{st.session_state.index + 1} / {total}")

        # Fim do jogo
        if st.session_state.index >= total:
            st.success("🎉 Jogo finalizado!")
            percent = (st.session_state.score / total) * 100
            st.metric("Desempenho (%)", f"{percent:.1f}%")

            # salva uma vez
            if not st.session_state.saved_score:
                append_score(st.session_state.student_name, st.session_state.score, total)
                st.session_state.saved_score = True

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔁 Jogar novamente"):
                    reset_game()
                    st.rerun()
            with col2:
                if st.button("👤 Trocar aluno"):
                    st.session_state.student_name = ""
                    reset_game()
                    st.rerun()

        # Jogo em andamento
        else:
            ident = st.session_state.ordem[st.session_state.index]
            gabarito = compute_gabarito(ident)

            st.progress(st.session_state.index / total)
            st.markdown(f"### Identificador: `{ident}`")

            disabled = st.session_state.show_feedback

            resposta = st.radio(
                "Classifique:",
                ["✅ Válido", "❌ Inválido", "⚠️ Válido, mas má prática"],
                index=0,
                disabled=disabled,
            )

            selecionadas = []
            if resposta == "❌ Inválido":
                st.markdown("**Justifique (marque ao menos 1 opção):**")
                selecionadas = st.multiselect("Motivos:", JUSTIFICATIVAS_INVALIDO, disabled=disabled)
            elif resposta == "⚠️ Válido, mas má prática":
                st.markdown("**Justifique (marque ao menos 1 opção):**")
                selecionadas = st.multiselect("Motivos:", JUSTIFICATIVAS_MA_PRATICA, disabled=disabled)

            if not st.session_state.show_feedback:
                if st.button("✅ Confirmar"):
                    if resposta in ["❌ Inválido", "⚠️ Válido, mas má prática"] and len(selecionadas) == 0:
                        st.warning("⚠️ Você precisa justificar marcando ao menos 1 opção.")
                    else:
                        correto = (resposta == gabarito)
                        if correto:
                            st.session_state.score += 1

                        st.session_state.last_answer_correct = correto
                        st.session_state.last_gabarito = gabarito
                        st.session_state.last_reasons = expected_reasons(ident)

                        # checagem leve (apenas alerta)
                        ok_just = True
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
                                ok_just = False

                        st.session_state.last_selected_ok = ok_just
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
                    st.write("- Identificador válido e bem estruturado.")
                elif gabarito == "⚠️ Válido, mas má prática":
                    st.write("- Identificador válido, mas má prática (geralmente pouco descritivo).")
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
                    st.warning("🟡 A justificativa não bateu com a regra violada (confira os motivos acima).")

                if st.button("➡️ Próximo"):
                    st.session_state.index += 1
                    st.session_state.show_feedback = False
                    st.rerun()


# ==========================================================
# VIEW: ADMIN
# ==========================================================
else:
    st.subheader("🔐 Área do administrador")
    st.caption("Login para visualizar ranking (com medalhas), top/bottom 10 e limpar respostas.")

    if not st.session_state.admin_authed:
        user = st.text_input("Usuário")
        pwd = st.text_input("Senha", type="password")

        if st.button("🔓 Entrar"):
            if user == ADMIN_USER and pwd == ADMIN_PASS:
                st.session_state.admin_authed = True
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

        st.info("Configure em `.streamlit/secrets.toml` (recomendado).")
    else:
        st.success("✅ Admin autenticado.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚪 Sair (logout)"):
                st.session_state.admin_authed = False
                st.session_state.confirm_clear = False
                st.rerun()

        with col2:
            if st.button("🗑️ Limpar todas as respostas"):
                st.session_state.confirm_clear = True

        # Confirmação
        if st.session_state.confirm_clear:
            st.warning("⚠️ Tem certeza que deseja apagar TODAS as respostas? Essa ação é irreversível.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Confirmar exclusão"):
                    clear_scores()
                    st.session_state.confirm_clear = False
                    st.success("✔️ Todas as respostas foram apagadas.")
                    st.rerun()
            with c2:
                if st.button("❌ Cancelar"):
                    st.session_state.confirm_clear = False
                    st.rerun()

        rows = load_scores()
        if not rows:
            st.info("Ainda não há pontuações registradas.")
        else:
            # Melhor tentativa por aluno (maior percent; desempate: maior score; desempate: mais recente)
            best_by_student = {}
            for r in rows:
                name = (r.get("student_name") or "").strip()
                if not name:
                    continue

                key = (r["percent"], r["score"], r["timestamp_utc"])
                if name not in best_by_student:
                    best_by_student[name] = r
                else:
                    cur = best_by_student[name]
                    cur_key = (cur["percent"], cur["score"], cur["timestamp_utc"])
                    if key > cur_key:
                        best_by_student[name] = r

            best_list = list(best_by_student.values())
            best_sorted = sorted(best_list, key=lambda x: (x["percent"], x["score"], x["timestamp_utc"]), reverse=True)

            # Ranking com medalhas (top 10)
            st.markdown("## 🏆 Ranking (Top 10) — com medalhas")

            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            ranking_table = []
            for i, r in enumerate(best_sorted[:10], start=1):
                ranking_table.append({
                    "Posição": f"{medals.get(i, '🏅')} {i}",
                    "Aluno": r["student_name"],
                    "Pontos": f'{r["score"]}/{r["total"]}',
                    "%": f'{r["percent"]:.1f}%',
                    "Última tentativa (UTC)": r["timestamp_utc"],
                })

            st.dataframe(ranking_table, use_container_width=True, hide_index=True)

            # Top 10 e Bottom 10 (melhor por aluno)
            top10 = best_sorted[:10]
            bottom10 = sorted(best_list, key=lambda x: (x["percent"], x["score"], x["timestamp_utc"]))[:10]

            st.markdown("### 🧯 Bottom 10")
            bottom_table = []
            for i, r in enumerate(bottom10, start=1):
                bottom_table.append({
                    "Posição": i,
                    "Aluno": r["student_name"],
                    "Pontos": f'{r["score"]}/{r["total"]}',
                    "%": f'{r["percent"]:.1f}%',
                    "Última tentativa (UTC)": r["timestamp_utc"],
                })
            st.dataframe(bottom_table, use_container_width=True, hide_index=True)

            st.markdown("### 🕒 Últimos 25 registros (raw)")
            last = sorted(rows, key=lambda x: x["timestamp_utc"], reverse=True)[:25]
            st.dataframe(last, use_container_width=True, hide_index=True)

            st.caption(f"Armazenamento local: `{SCORES_FILE.as_posix()}`")
