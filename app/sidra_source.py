"""Séries oficiais do IBGE/SIDRA por tema, para leitura do que mudou no país.

Cada série é preservada com período, unidade, população e URL de consulta. São observações
agregadas nacionais: NÃO são atribuídas a candidaturas nem demonstram efeito de uma política.
Períodos trimestrais usam o formato ``AAAATn`` para não colidir com o mensal ``AAAAMM``.
"""
from __future__ import annotations
import re
import requests
from .core import norm
from .db import connect

API = "https://apisidra.ibge.gov.br/values"
PAGE = "https://sidra.ibge.gov.br/tabela/{table}"
ISSUER = "IBGE/SIDRA"

# (código, tabela, variável, classificação, nome, unidade, população, método, períodos)
SPECS = (
    ("IBGE_5436_RENDIMENTO_{g}", 5436, "5932", "c2/6794,4,5", "Rendimento médio real habitual do trabalho principal",
     "R$", "Ocupados de 14+ anos, {gl}", "PNAD Contínua trimestral, valores reais; média, não mediana.", "last%2028"),
    ("IBGE_4093_DESOCUPACAO_{g}", 4093, "4099", "c2/6794,4,5", "Taxa de desocupação",
     "%", "Pessoas de 14+ anos, {gl}", "PNAD Contínua trimestral; definição da semana de referência.", "last%2028"),
    ("IBGE_8529_INFORMALIDADE", 8529, "12466", "", "Taxa de informalidade",
     "%", "Ocupados de 14+ anos", "PNAD Contínua trimestral; inclui empregados sem carteira, conta própria sem CNPJ e outros.",
     "last%2028"),
)
IPCA_GROUPS = {"7169": "Índice geral", "7445": "Habitação", "7660": "Saúde e cuidados pessoais", "7766": "Educação"}
GENDERS = {"Total": ("TOTAL", "ambos os sexos"), "Homens": ("HOMENS", "homens"), "Mulheres": ("MULHERES", "mulheres")}


def quarter_period(code: str, label: str) -> str:
    m = re.match(r"^(\d{4})0([1-4])$", code or "")
    return f"{m.group(1)}T{m.group(2)}" if m else label


def parse_rows(rows: list[dict], spec: tuple, page_url: str) -> list[dict]:
    code_t, _t, _v, _c, name, unit, pop_t, method, _p = spec
    out = []
    for r in rows[1:]:
        raw = (r.get("V") or "").strip()
        if raw in ("", "..", "...", "-", "X"):
            continue
        sex = r.get("D4N") or ""
        if "{g}" in code_t and sex not in GENDERS:
            continue
        g, gl = GENDERS.get(sex, ("", ""))
        out.append({
            "indicator_code": code_t.format(g=g), "indicator_name": name, "unit": unit,
            "period": quarter_period(r.get("D3C", ""), r.get("D3N", "")), "territory": "Brasil",
            "population": pop_t.format(gl=gl), "value": float(raw), "source_url": page_url,
            "source_issuer": ISSUER, "methodology": method + " Série observada; não mede efeito de política.",
        })
    return out


def parse_ipca_groups(rows: list[dict], page_url: str) -> list[dict]:
    out = []
    for r in rows[1:]:
        raw = (r.get("V") or "").strip()
        label = re.sub(r"^\d+\.", "", r.get("D4N") or "")
        if raw in ("", "..", "...", "-") or label not in IPCA_GROUPS.values():
            continue
        out.append({
            "indicator_code": "IBGE_7060_IPCA12M_" + re.sub(r"\W+", "_", norm(label).upper()),
            "indicator_name": "IPCA acumulado em 12 meses: " + label, "unit": "%",
            "period": r["D3C"], "territory": "Brasil", "population": "Preços ao consumidor (famílias de 1 a 40 SM)",
            "value": float(raw), "source_url": page_url, "source_issuer": ISSUER,
            "methodology": "Variação de preços; para saúde, educação e habitação mede custo de vida, "
                           "não qualidade nem acesso ao serviço público.",
        })
    return out


def _fetch(path: str) -> list[dict]:
    r = requests.get(f"{API}/{path}", timeout=60, headers={"User-Agent": "Civica-Evidencias/0.1 (pesquisa)"})
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list) or len(data) < 2:
        raise ValueError("Resposta SIDRA vazia")
    return data


def collect(fetch=_fetch) -> list[dict]:
    rows: list[dict] = []
    for spec in SPECS:
        _c, table, var, cls, *_rest, period = spec
        path = f"t/{table}/n1/all/v/{var}/p/{period}" + (f"/{cls}" if cls else "")
        rows += parse_rows(fetch(path), spec, PAGE.format(table=table))
    ids = ",".join(IPCA_GROUPS)
    rows += parse_ipca_groups(fetch(f"t/7060/n1/all/v/2265/p/last%2084/c315/{ids}"), PAGE.format(table=7060))
    return rows


def import_sidra(fetch=_fetch) -> dict:
    rows = collect(fetch)
    if not rows:
        raise ValueError("Nenhuma observação SIDRA importada")
    conn = connect()
    try:
        with conn:
            conn.executemany(
                """INSERT OR REPLACE INTO outcome_series(indicator_code,indicator_name,unit,period,territory,
                   population,value,source_url,source_issuer,methodology) VALUES
                   (:indicator_code,:indicator_name,:unit,:period,:territory,:population,:value,:source_url,
                    :source_issuer,:methodology)""", rows)
    finally:
        conn.close()
    return {"rows": len(rows), "series": len({r["indicator_code"] for r in rows}),
            "first_period": min(r["period"] for r in rows), "last_period": max(r["period"] for r in rows)}
