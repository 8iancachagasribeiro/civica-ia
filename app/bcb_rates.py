"""Selic e juros de financiamento imobiliário (Banco Central), como séries observadas.

São médias nacionais do mercado: não são oferta a uma pessoa nem efeito de governo. A API
de séries diárias do BCB aceita janelas curtas, por isso a Selic é pedida desde 2022.
"""
from __future__ import annotations
import statistics
import time
import urllib.parse as up
from datetime import date
import requests
from .core import norm
from .db import connect

SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados"
OLINDA = "https://olinda.bcb.gov.br/olinda/servico/taxaJuros/versao/v2/odata/TaxasJurosMensalPorMes"
ISSUER = "Banco Central do Brasil"
SINCE = "2022-01"
MODALITIES = {  # (regulação, indexador) → chave da série
    ("reguladas", "tr"): "REGULADA_TR",
    ("mercado", "tr"): "MERCADO_TR",
    ("mercado", "prefixado"): "MERCADO_PREFIXADO",
}
LABELS = {
    "REGULADA_TR": "Financiamento imobiliário com taxas reguladas, pós-fixado (acima da TR)",
    "MERCADO_TR": "Financiamento imobiliário com taxas de mercado, pós-fixado (acima da TR)",
    "MERCADO_PREFIXADO": "Financiamento imobiliário com taxas de mercado, prefixado",
}


def parse_selic(rows: list[dict]) -> list[dict]:
    """Meta Selic vigente no último dia de cada mês."""
    last: dict[str, float] = {}
    for r in rows:
        d, m, y = r["data"].split("/")
        last[f"{y}{m}"] = float(r["valor"])
    url = SGS_URL + "?formato=json"
    return [{"indicator_code": "BCB_SGS_432_SELIC_META", "indicator_name": "Meta da taxa Selic (fim do mês)",
             "unit": "% a.a.", "period": p, "territory": "Brasil", "population": "Taxa básica de juros",
             "value": v, "source_url": url, "source_issuer": ISSUER + "/Copom",
             "methodology": "SGS 432. Taxa básica da economia; não é a taxa cobrada de uma pessoa."}
            for p, v in sorted(last.items())]


def _modality_key(name: str) -> str | None:
    n = norm(name)
    if "imobiliario" not in n:
        return None
    regime = "reguladas" if "taxas reguladas" in n else "mercado" if "taxas de mercado" in n else None
    index = "tr" if "referenciado em tr" in n else "prefixado" if n.endswith("prefixado") else None
    return MODALITIES.get((regime, index))


def parse_mortgage(rows: list[dict]) -> list[dict]:
    """Mediana entre instituições e taxa da CAIXA, por mês e modalidade (taxa ao ano)."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        key = _modality_key(r["Modalidade"])
        if key and r["TaxaJurosAoAno"] and r["TaxaJurosAoAno"] > 0:
            groups.setdefault((r["anoMes"].replace("-", ""), key), []).append(r)
    out = []
    for (period, key), items in sorted(groups.items()):
        base = {"unit": "% a.a.", "period": period, "territory": "Brasil", "source_url": OLINDA,
                "source_issuer": ISSUER + "/Taxas de juros por modalidade",
                "methodology": "Média mensal das taxas informadas pelas instituições; acima da TR quando pós-fixado. "
                               "Não é oferta a uma pessoa."}
        out.append({**base, "indicator_code": f"BCB_OLINDA_IMOB_{key}_MEDIANA", "indicator_name": LABELS[key],
                    "population": f"Mediana entre {len(items)} instituições",
                    "value": round(statistics.median(i["TaxaJurosAoAno"] for i in items), 2)})
        caixa = [i for i in items if "CAIXA ECONOMICA" in norm(i["InstituicaoFinanceira"]).upper()]
        if caixa:
            out.append({**base, "indicator_code": f"BCB_OLINDA_IMOB_{key}_CAIXA", "indicator_name": LABELS[key],
                        "population": "CAIXA Econômica Federal", "value": caixa[0]["TaxaJurosAoAno"]})
    return out


def _fetch_selic() -> list[dict]:
    """Um ano por requisição: a API do BCB recusa janelas longas em séries diárias."""
    rows: list[dict] = []
    today = date.today()
    for year in range(2022, today.year + 1):
        end = min(date(year, 12, 31), today)
        for attempt in range(5):
            r = requests.get(SGS_URL, params={"formato": "json", "dataInicial": f"01/01/{year}",
                                              "dataFinal": end.strftime("%d/%m/%Y")}, timeout=60)
            if r.ok and r.headers.get("content-type", "").startswith("application/json"):
                rows += r.json()
                break
            if attempt == 4:
                raise ValueError(f"SGS 432 indisponível para {year}")
            time.sleep(4 * (attempt + 1))
    return rows


def _fetch_mortgage() -> list[dict]:
    flt = f"anoMes ge '{SINCE}' and contains(Modalidade,'imobili')"
    url = OLINDA + "?%24top=100000&%24format=json&%24filter=" + up.quote(flt, safe="")
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    return r.json()["value"]


def import_rates(fetch_selic=_fetch_selic, fetch_mortgage=_fetch_mortgage) -> dict:
    rows = parse_selic(fetch_selic()) + parse_mortgage(fetch_mortgage())
    if not rows:
        raise ValueError("Nenhuma taxa de juros importada")
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
