import re
import unicodedata
import streamlit as st

# =========================
# Configuração da página
# =========================
st.set_page_config(
    page_title="Jogo de Identificadores (Java)",
    page_icon="🧠",
    layout="centered",
)

st.title("🧠 Jogo de Identificadores (Java)")
st.caption(
    "Atividade interativa sobre identificadores: regras, validade e boas práticas "
    "(sem acentos/ASCII, sem espaços, sem símbolos de operação, etc.)."
)

# =========================
# Regras (alinhadas ao seu material)
# - não começar com número
# - não ter espaços
# - não ter acento (ASCII)
# - não ter símbolos/operadores (permitimos '_')
# - pode ter números após o primeiro caractere
# =========================
GENERICOS = {"a", "b", "c", "x", "y", "z", "n", "m", "v", "t", "i", "j", "k"}

def has_accent(s: str) -> bool:
    # Se normalizar removendo acentos muda a string, havia acento.
    return unicodedata.normalize("NFKD", s) != s

def is_valid_identifier_java_didatico(name: str) -> bool:
    # Versão didática baseada no seu slide:
    # começa com letra ou '_' e segue com letras/números/'_'
    # (sem acentos)
    pattern = r"^[A-Za-z_][A-Za-z0-9_]*$"
    return bool(re.match(pattern, name)) and not has_accent(name)

def is_bad_practice(name: str) -> bool:
    # Didático: muito curto ou "genérico demais"
    if name in GENERICOS:
        return True
    if len(name) <= 2 and name.isalpha():
        return True
    return False

def analyze_reasons(name: str) -> list[str]:
    r = []
    if not name:
        return ["vazio"]

    if name[0].isdigit():
        r.append("começa com número")
    if " " in name:
        r.append("tem espaço")
    if has_accent(name):
        r.append("tem acento (não ASCII)")
    if re.search(r"[^A-Za-z0-9_ ]", name):
        r.append("tem símbolo/operador inválido (ex.: +, -, *, /, %)")
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name) and ("tem espaço" not in r):
        r.append("não segue padrão letra/_ + letras/números/_")
    if is_valid_identifier_java_didatico(name) and is_bad_practice(name):
        r.append("válido, mas má prática (pouco descritivo)")

    return r

# =========================
# Banco de itens (mistura válido / inválido / má prática)
# =========================
QUESTOES = [
    {"nome": "base", "classe": "valido"},
    {"nome": "altura", "classe": "valido"},
    {"nome": "_altura", "classe": "valido"},
    {"nome": "_altura1", "classe": "valido"},
    {"nome": "parede3lados", "classe": "valido"},
    {"nome": "parede_reta", "classe": "valido"},
    {"nome": "ParedeReta04", "classe": "valido"},
    {"nome": "3base", "classe": "invalido"},
    {"nome": "altura principal", "classe": "invalido"},
    {"nome": "altura1+", "classe": "invalido"},
    {"nome": "triângulo", "classe": "invalido"},
    {"nome": "a", "classe": "ma_pratica"},
    {"nome": "x", "classe": "ma_pratica"},
    {"nome": "m", "classe": "ma_pratica"},
    {"nome": "areaTriangulo", "classe": "valido"},
    {"nome": "baseTriangulo", "classe": "valido"},
    {"nome": "alturaTriangulo", "classe": "valido"},
]

CLASS_MAP = {
    "valido": "✅ Válido",
    "invalido": "❌ Inválido",
    "ma_pratica": "⚠️ Válido, mas má prática",
}

# =========================
# Estado do jogo
# =========================
if "idx" not in st.session_state:
    st.session_state.idx = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "finished" not in st.session_state:
    st.session_state.finished = False

# =========================
# UI - Seleção de modo
# =========================
modo = st.radio(
    "Escolha o modo:",
    ["🎮 Jogo (classificar)", "🛠️ Refatoração (melhorar nomes)"],
    horizontal=True,
)

st.divider()

# =========================
# MODO 1: Jogo
# =========================
if modo == "🎮 Jogo (classificar)":
    total = len(QUESTOES)
    if st.session_state.idx >= total:
        st.session_state.finished = True

    if st.session_state.finished:
        st.success(f"Fim do jogo! Pontuação: **{st.session_state.score} / {total}**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔁 Jogar novamente"):
                st.session_state.idx = 0
                st.session_state.score = 0
                st.session_state.finished = False
                st.rerun()
        with col2:
            st.metric("Acertos", st.session_state.score)
        st.stop()

    q = QUESTOES[st.session_state.idx]
    nome = q["nome"]

    st.subheader(f"🔤 Identificador: `{nome}`")
    st.progress((st.session_state.idx) / total)

    escolha = st.radio(
        "Classifique:",
        ["✅ Válido", "❌ Inválido", "⚠️ Válido, mas má prática"],
        index=0,
    )

    st.markdown("**Justificativa (marque o que se aplica):**")
    c1 = st.checkbox("Começa com número")
    c2 = st.checkbox("Tem espaço")
    c3 = st.checkbox("Tem acento (não ASCII)")
    c4 = st.checkbox("Tem símbolo/operador inválido (+, -, *, /, %...)")
    c5 = st.checkbox("É pouco descritivo (uma letra / genérico)")

    if st.button("✅ Confirmar resposta"):
        gabarito = CLASS_MAP[q["classe"]]

        # Análise automática
        auto_valido = is_valid_identifier_java_didatico(nome)
        auto_ma_pratica = auto_valido and is_bad_practice(nome)
        motivos = analyze_reasons(nome)

        if escolha == gabarito:
            st.session_state.score += 1
            st.success("Acertou! ✅")
        else:
            st.error(f"Quase! O gabarito era: **{gabarito}**")

        st.info("📌 Análise pelas regras (feedback do app):")
        if auto_valido and not auto_ma_pratica:
            st.write("- **Válido**: segue padrão e não tem acento/espaço/símbolos proibidos.")
        elif auto_ma_pratica:
            st.write("- **Válido**, mas **má prática**: nome genérico/pouco descritivo.")
        else:
            for m in motivos:
                st.write(f"- {m}")

        st.caption("Dica: em Java e no mercado, nomes claros reduzem bugs e melhoram manutenção.")
        st.session_state.idx += 1
        st.rerun()

# =========================
# MODO 2: Refatoração
# =========================
else:
    st.subheader("🛠️ Refatoração (deixar profissional)")
    st.markdown("Trecho original (ruim):")
    st.code("a = (b * c) / 2;", language="java")

    st.markdown("Sugira nomes melhores (**camelCase**, sem acento, sem espaço):")
    area = st.text_input("Nome para `a` (resultado):", value="areaTriangulo")
    base = st.text_input("Nome para `b` (base):", value="baseTriangulo")
    altura = st.text_input("Nome para `c` (altura):", value="alturaTriangulo")

    if st.button("🔎 Validar nomes"):
        nomes = {"Resultado": area, "Base": base, "Altura": altura}
        ok = True

        for rotulo, n in nomes.items():
            if not is_valid_identifier_java_didatico(n):
                ok = False
                st.error(f"❌ {rotulo}: `{n}` é inválido. Motivos: {', '.join(analyze_reasons(n))}")
            elif is_bad_practice(n):
                ok = False
                st.warning(f"⚠️ {rotulo}: `{n}` é válido, mas má prática (genérico).")
            else:
                st.success(f"✅ {rotulo}: `{n}` está ótimo!")

        if ok:
            st.balloons()
            st.markdown("✅ Versão refatorada:")
            st.code(f"{area} = ({base} * {altura}) / 2;", language="java")

    st.divider()

    st.markdown("### 🎯 Desafio extra (contexto)")
    st.caption("Crie identificadores claros para cada situação.")
    d1 = st.text_input("Distância entre dois átomos:", value="distanciaEntreAtomos")
    d2 = st.text_input("Cateto de um triângulo retângulo:", value="catetoOposto")
    d3 = st.text_input("Idade de uma pessoa:", value="idadePessoa")
    d4 = st.text_input("Área de um cilindro:", value="areaCilindro")

    if st.button("✅ Checar desafio extra"):
        extras = [d1, d2, d3, d4]
        ok2 = True
        for n in extras:
            if not is_valid_identifier_java_didatico(n):
                ok2 = False
                st.error(f"❌ `{n}` inválido: {', '.join(analyze_reasons(n))}")
            elif is_bad_practice(n):
                ok2 = False
                st.warning(f"⚠️ `{n}` válido, mas má prática.")
            else:
                st.success(f"✅ `{n}` ok!")
        if ok2:
            st.balloons()
            st.success("Mandou bem! Identificadores claros = código profissional.")
