"""Classificação temática e leitura de passagens, determinística e auditável.

Substitui a busca por trecho de palavra (``"sus" in texto`` casa "sustentável") por
expressões com fronteira de palavra. Uma passagem pode pertencer a vários temas.
Nada aqui pontua pessoas ou propostas: são marcadores lexicais descritivos.
"""
from __future__ import annotations
import re
import unicodedata
from .core import norm

# (chave, rótulo, [(padrão, peso)]). Peso 2 = termo forte; limiar de marcação = 2.
AXES: tuple[tuple[str, str, tuple[tuple[str, int], ...]], ...] = (
    ("mulheres", "Mulheres", (
        (r"\bmulher(?:es)?\b", 2), (r"\bfeminin\w*", 1), (r"\bfeminicid\w*", 2),
        (r"\bgenero\b", 1), (r"\bcreches?\b", 1), (r"\bmaternidade\b", 1),
        (r"\bmaria da penha\b", 2), (r"\bigualdade salarial\b", 2),
        (r"\bviolencia domestica\b", 2), (r"\bgestantes?\b", 1), (r"\bmeninas?\b", 1),
    )),
    ("economia", "Economia", (
        (r"\beconomi\w*", 1), (r"\binflacao\b", 2), (r"\bipca\b", 2), (r"\brenda\b", 1),
        (r"\bemprego\w*", 1), (r"\bsalari\w*", 1), (r"\btribut\w*", 1), (r"\bimpostos?\b", 1),
        (r"\bpobreza\b", 1), (r"\bdesocupa\w*", 2), (r"\bdesempreg\w*", 2), (r"\bpib\b", 2),
        (r"\bjuros\b", 1), (r"\bdivida publica\b", 2), (r"\bfiscal\b", 1), (r"\bcrescimento\b", 1),
        (r"\bsalario minimo\b", 2), (r"\bimposto de renda\b", 2),
    )),
    ("saude", "Saúde", (
        (r"\bsaude\b", 2), (r"\bsus\b", 2), (r"\bhospita\w*", 1), (r"\bvacin\w*", 2),
        (r"\bmedic\w*", 1), (r"\bmortalidade\b", 1), (r"\bubs\b", 2), (r"\bsamu\b", 2),
        (r"\batencao basica\b", 2), (r"\bdoencas?\b", 1), (r"\bmais medicos\b", 2),
    )),
    ("educacao", "Educação", (
        (r"\beducacao\b", 2), (r"\bescol\w*", 1), (r"\buniversidades?\b", 1),
        (r"\balfabetiza\w*", 2), (r"\bensino\b", 1), (r"\bestudantes?\b", 1),
        (r"\bprofessor\w*", 1), (r"\bfundeb\b", 2), (r"\benem\b", 2), (r"\bpe[- ]de[- ]meia\b", 2),
        (r"\bprouni\b", 2), (r"\bfies\b", 2), (r"\bcreches?\b", 1),
    )),
    ("seguranca", "Segurança", (
        (r"\bseguranca publica\b", 2), (r"\bviolencia\b", 1), (r"\bhomicid\w*", 2),
        (r"\bpolicia\w*", 1), (r"\bcrimes?\b", 1), (r"\bcrime organizado\b", 2),
        (r"\bfaccoes\b", 2), (r"\barmas?\b", 1), (r"\bsistema prisional\b", 2),
        (r"\bpenitenciar\w*", 2), (r"\btrafico\b", 1), (r"\bpresidios?\b", 2),
    )),
    ("justica", "Justiça", (
        (r"\bjustica\b", 1), (r"\bjudiciario\b", 2), (r"\bjudicia\w*", 1),
        (r"\btribunai?s?\b", 1), (r"\bstf\b", 2), (r"\bdefensoria\b", 2),
        (r"\bministerio publico\b", 2), (r"\bcorrupcao\b", 2), (r"\bimpunidade\b", 2),
        (r"\bforo privilegiado\b", 2),
    )),
    ("habitacao", "Habitação", (
        (r"\bhabitac\w*", 2), (r"\bmoradias?\b", 2), (r"\baluguel\b", 1), (r"\bsaneamento\b", 2),
        (r"\bminha casa\b", 2), (r"\bfavelas?\b", 1), (r"\bcasa propria\b", 2),
        (r"\bregularizacao fundiaria\b", 2), (r"\bdeficit habitacional\b", 2),
    )),
    ("ambiente", "Meio ambiente", (
        (r"\bmeio ambiente\b", 2), (r"\bambienta\w*", 1), (r"\bflorestas?\b", 1),
        (r"\bclima\w*", 1), (r"\bdesmat\w*", 2), (r"\bamazonia\b", 1), (r"\benergia\w*", 1),
        (r"\bcarbono\b", 2), (r"\bsustentabilidade\b", 1),
    )),
)
LABELS = {key: label for key, label, _ in AXES}
_COMPILED = {key: tuple((re.compile(p), w) for p, w in patterns) for key, _, patterns in AXES}
MIN_SCORE = 2


def theme_scores(text: str) -> dict[str, int]:
    """Pontuação lexical por tema (soma de pesos × ocorrências, até 5 por padrão)."""
    t = norm(text or "")
    out: dict[str, int] = {}
    for key, patterns in _COMPILED.items():
        score = sum(w * min(5, len(rx.findall(t))) for rx, w in patterns)
        if score:
            out[key] = score
    return out


def tag_themes(text: str, min_score: int = MIN_SCORE) -> dict[str, int]:
    return {k: v for k, v in theme_scores(text).items() if v >= min_score}


_PROSPECTIVE = re.compile(
    r"\b(?:vamos|iremos|criaremos|implantaremos|implementaremos|ampliaremos|garantiremos|"
    r"reduziremos|instituiremos|proporemos|buscaremos|manteremos|fortaleceremos|promoveremos|"
    r"enviaremos|zeraremos|retomaremos|construiremos|aprovaremos|asseguraremos|elevaremos|"
    r"universalizaremos|modernizaremos|expandiremos|eliminaremos|criar|implantar|implementar|"
    r"ampliar|garantir|reduzir|instituir|fortalecer|promover|assegurar|zerar|eliminar|elevar|"
    r"universalizar|modernizar|expandir|propor|aprovar|construir)\b")
_RETROSPECTIVE = re.compile(
    r"\b(?:criou|criamos|instituiu|instituimos|retomou|retomamos|lancou|lancamos|entregou|entregamos|"
    r"ampliou|ampliamos|reduziu|reduzimos|garantiu|garantimos|recriou|aprovou|aprovamos|implantou|"
    r"implantamos|zerou|expandiu|reconstruiu|reconstruimos|reajustou|aumentou|fizemos|realizou|"
    r"conquistou|devolveu|sancionou|investiu|resgatou|recuperou|foi criado|foram criados|"
    r"foi criada|foram criadas|foi aprovado|foi aprovada|foram aprovados|foram aprovadas)\b")
_NUMBER = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:%|por cento)|r\$\s*\d|\b\d+(?:[.,]\d+)?\s*(?:mil|milhao|milhoes|bilhao|"
    r"bilhoes|trilhao|trilhoes)\b|\b\d{1,3}(?:\.\d{3})+\b|\bmeta(?:s)?\b")
_DEADLINE = re.compile(
    r"\b(?:ate|em|ate o fim de|a partir de)\s+20(?:2[6-9]|3\d)\b|\b20(?:27|28|29|30)\b|"
    r"\bprimeiros?\s+\d*\s*(?:dias|meses|anos)\b|\bprimeiro ano\b|\bem\s+\d+\s+(?:dias|meses|anos)\b")
_FUNDING = re.compile(
    r"\borcamento\b|\bfinanciament\w*|\brecursos?\s+(?:da uniao|publicos|do orcamento|do fundo|"
    r"federais|adicionais)\b|\bfonte\s+de\s+(?:recursos|financiamento|receita)\b|\bfundo\s+\w+|"
    r"\bcompensacao\b|\bem\s+\d+\s*%\s+do\s+pib\b")


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?;:])\s+|\s*[•●▪]\s*", re.sub(r"\s+", " ", text or "").strip())
    return [s for s in parts if len(s) > 25]


def read_passage(text: str) -> dict:
    """Natureza e marcadores de especificidade da passagem (heurística lexical).

    kind: ``compromisso`` (linguagem prospectiva), ``balanco`` (alegação de feito passado,
    não verificada) ou ``contexto``. Marcadores: n=número/meta, p=prazo, r=fonte de recursos.
    """
    t = norm(text or "")
    pros = len(_PROSPECTIVE.findall(t))
    retro = len(_RETROSPECTIVE.findall(t))
    kind = "contexto"
    if retro > pros:
        kind = "balanco"
    elif pros:
        kind = "compromisso"
    markers = [code for code, rx in (("n", _NUMBER), ("p", _DEADLINE), ("r", _FUNDING)) if rx.search(t)]
    return {"kind": kind, "markers": markers}


def norm_same_len(text: str) -> str:
    """Normalização que preserva o comprimento (um caractere → um caractere) para posições."""
    out = []
    for ch in text:
        base = next((c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c)), " ")
        out.append(base.lower())
    return "".join(out)


def anchor(text: str, theme: str) -> int:
    """Posição (no texto original) da primeira ocorrência de um termo do tema."""
    t = norm_same_len(text or "")
    hits = [m.start() for rx, _w in _COMPILED[theme] if (m := rx.search(t))]
    return min(hits) if hits else 0


def anchor_regex(text: str, pattern: str) -> int:
    m = re.search(pattern, norm_same_len(text or ""))
    return m.start() if m else 0


# Séries observadas exibidas por tema. Cada grupo mostra códigos lado a lado (ex.: por sexo).
# Temas sem série integrada ficam ausentes: a interface declara a lacuna.
THEME_INDICATORS: dict[str, list[dict]] = {
    "mulheres": [
        {"label": "Rendimento médio real habitual do trabalho principal (R$)", "ratio": True,
         "codes": {"Mulheres": "IBGE_5436_RENDIMENTO_MULHERES", "Homens": "IBGE_5436_RENDIMENTO_HOMENS"}},
        {"label": "Taxa de desocupação (%)",
         "codes": {"Mulheres": "IBGE_4093_DESOCUPACAO_MULHERES", "Homens": "IBGE_4093_DESOCUPACAO_HOMENS"}},
    ],
    "economia": [
        {"label": "IPCA acumulado em 12 meses (%)", "codes": {"Índice geral": "IBGE_7060_IPCA12M_INDICE_GERAL"}},
        {"label": "Taxa de desocupação (%)", "codes": {"Total": "IBGE_4093_DESOCUPACAO_TOTAL"}},
        {"label": "Rendimento médio real habitual do trabalho principal (R$)",
         "codes": {"Total": "IBGE_5436_RENDIMENTO_TOTAL"}},
        {"label": "Taxa de informalidade (%)", "codes": {"Total": "IBGE_8529_INFORMALIDADE"}},
    ],
    "saude": [
        {"label": "IPCA 12 meses: preços de saúde e cuidados pessoais (%)",
         "note": "Mede custo de vida, não qualidade nem acesso ao SUS.",
         "codes": {"Saúde e cuidados pessoais": "IBGE_7060_IPCA12M_SAUDE_E_CUIDADOS_PESSOAIS",
                   "Índice geral": "IBGE_7060_IPCA12M_INDICE_GERAL"}},
    ],
    "educacao": [
        {"label": "IPCA 12 meses: preços de educação (%)",
         "note": "Mede custo de vida (mensalidades, material), não aprendizagem nem acesso.",
         "codes": {"Educação": "IBGE_7060_IPCA12M_EDUCACAO", "Índice geral": "IBGE_7060_IPCA12M_INDICE_GERAL"}},
    ],
    "habitacao": [
        {"label": "IPCA 12 meses: preços de habitação (%)",
         "note": "Mede custo de vida (aluguel, energia, condomínio), não déficit habitacional.",
         "codes": {"Habitação": "IBGE_7060_IPCA12M_HABITACAO", "Índice geral": "IBGE_7060_IPCA12M_INDICE_GERAL"}},
    ],
}
