"""Registros oficiais do que foi apresentado, votado e transformado em norma.

Cobertura DELIBERADAMENTE restrita ao registro normativo público:
- Presidente da República: proposições do Poder Executivo na Câmara (MPV, PL, PLP, PEC);
- Senador: proposições de sua autoria no Senado.
Não inclui decretos, execução orçamentária, entrega de serviços nem votos nominais. Proposta
apresentada não é lei; lei sancionada não é resultado. Funções puras recebem ``fetch`` para teste.
"""
from __future__ import annotations
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable
import requests
from .core import norm
from .db import connect
from .themes import tag_themes
from .traceability import install_trace_schema

CAMARA = "https://dadosabertos.camara.leg.br/api/v2"
SENADO = "https://legis.senado.leg.br/dadosabertos"
CAMARA_FICHA = "https://www.camara.leg.br/proposicoesWeb/fichaTramitacao?idProposicao={id}"
SENADO_MATERIA = "https://www25.senado.leg.br/web/atividade/materias/-/materia/{code}"
EXECUTIVE_TYPES = ("MPV", "PL", "PLP", "PEC")
SENATE_TYPES = {"PL", "PLS", "PLP", "PEC", "PDL"}

# Chave = SQ_CANDIDATO do TSE 2026. Identidade e mandato conferidos em fontes oficiais.
PEOPLE = {
    "280002542548": {
        "name": "Luiz Inácio Lula da Silva", "scope": "executivo", "years": range(2023, 2027),
        "office": "Presidente da República (mandato iniciado em 01/01/2023)",
        "term_start": "2023-01-01",
        "term_source": "https://www.gov.br/planalto/pt-br/conheca-a-presidencia/acervo/presidentes-da-republica",
        "scope_note": ("Proposições enviadas pelo Poder Executivo ao Congresso desde 2023: medidas "
                       "provisórias e projetos. Não inclui decretos, orçamento executado nem serviços entregues."),
    },
    "280002551544": {
        "name": "Flávio Bolsonaro", "scope": "senado", "years": range(2019, 2027), "senate_code": 5894,
        "office": "Senador pelo Rio de Janeiro (mandato iniciado em 01/02/2019)",
        "term_start": "2019-02-01",
        "term_source": "https://legis.senado.leg.br/dadosabertos/senador/5894/mandatos",
        "scope_note": ("Projetos de lei, PEC e decretos legislativos de sua autoria no Senado. É registro "
                       "legislativo (propor e votar), não gestão executiva. Votos nominais não foram coletados."),
    },
}


def _get(url: str, params: dict | None = None) -> object:
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, timeout=45, headers={
                "Accept": "application/json", "User-Agent": "Civica-Evidencias/0.1 (pesquisa)"})
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(str(r.status_code))
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            if attempt == 3:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("inalcançável")


STAGE_LABELS = {
    "lei": "Virou norma jurídica",
    "aprovada": "Aprovada em uma casa",
    "tramitando": "Em tramitação",
    "encerrada": "Arquivada, retirada ou rejeitada",
    "perdeu_eficacia": "Medida provisória que perdeu a eficácia",
}
_CREDIT = re.compile(r"\babre\s+(?:ao|aos|a|as|em favor|credito)\b|\bcredito extraordinario\b|\bcredito suplementar\b")


def nature_of(ementa: str) -> str:
    """'credito' = abertura de crédito orçamentário; 'politica' = demais proposições."""
    return "credito" if _CREDIT.search(norm(ementa or "")) else "politica"


def stage_camara(situation: str) -> str:
    s = norm(situation or "")
    if "norma juridica" in s:
        return "lei"
    if "perdeu a eficacia" in s:
        return "perdeu_eficacia"
    if any(k in s for k in ("arquiv", "retirad", "vetado totalmente", "rejeit", "prejudicad")):
        return "encerrada"
    if "aprovad" in s or "sancao" in s or "apreciacao pelo senado" in s:
        return "aprovada"
    return "tramitando"


def stage_senado(situation: str) -> str:
    s = norm(situation or "")
    if "norma juridica" in s or "transformad" in s:
        return "lei"
    if any(k in s for k in ("arquiv", "retirad", "rejeit", "prejudicad", "vetad")):
        return "encerrada"
    if "remetid" in s or "aprovad" in s or "sancao" in s:
        return "aprovada"
    return "tramitando"


def _executive_candidates(fetch: Callable, year: int) -> list[dict]:
    found: dict[int, dict] = {}
    for kind in EXECUTIVE_TYPES:
        page = 1
        while True:
            data = fetch(f"{CAMARA}/proposicoes", {"siglaTipo": kind, "ano": year, "autor": "Poder Executivo",
                                                   "itens": 100, "pagina": page, "ordem": "ASC", "ordenarPor": "id"})
            rows = data.get("dados", [])
            for row in rows:
                found[row["id"]] = row
            if len(rows) < 100:
                break
            page += 1
    return list(found.values())


def collect_executive(years, since: str, fetch: Callable = _get, workers: int = 6) -> list[dict]:
    """Proposições cujo autor é o Poder Executivo, com desfecho atual e autoria conferida."""
    candidates: list[dict] = []
    for year in years:
        candidates.extend(_executive_candidates(fetch, year))

    def detail(row: dict) -> dict | None:
        authors = fetch(f"{CAMARA}/proposicoes/{row['id']}/autores", None).get("dados", [])
        if not any(a.get("nome") == "Poder Executivo" and a.get("proponente") == 1 for a in authors):
            return None
        info = fetch(f"{CAMARA}/proposicoes/{row['id']}", None)["dados"]
        presented = (info.get("dataApresentacao") or "")[:10]
        if presented < since:
            return None
        situation = (info.get("statusProposicao") or {}).get("descricaoSituacao") or ""
        ementa = re.sub(r"\s+", " ", info.get("ementa") or "").strip()
        return {
            "identifier": f"{info['siglaTipo']} {info['numero']}/{info['ano']}", "kind": info["siglaTipo"],
            "ementa": ementa, "presented_on": presented, "situation": situation,
            "stage": stage_camara(situation), "body": "Câmara dos Deputados",
            "authorship": "Poder Executivo", "source_url": CAMARA_FICHA.format(id=row["id"]),
            "themes": list(tag_themes(ementa, 1)), "nature": nature_of(ementa),
        }
    with ThreadPoolExecutor(workers) as pool:
        return [r for r in pool.map(detail, candidates) if r]


def _first_signatory(authorship: str, name: str) -> bool:
    first = re.sub(r"^(?:senador(?:a)?\s+)", "", (authorship or "").split(", Senador")[0].strip(), flags=re.I)
    return norm(first).startswith(norm(name))


def collect_senate(code: int, name: str, years, fetch: Callable = _get) -> list[dict]:
    out: dict[str, dict] = {}
    for year in years:
        rows = fetch(f"{SENADO}/processo", {"codigoParlamentarAutor": code, "ano": year})
        for row in rows:
            ident = row.get("identificacao") or ""
            sigla = ident.split(" ")[0]
            if sigla not in SENATE_TYPES or name not in (row.get("autoria") or ""):
                continue
            ementa = re.sub(r"\s+", " ", row.get("ementa") or "").strip()
            situation = row.get("situacaoAtual") or ""
            out[ident] = {
                "identifier": ident, "kind": sigla, "ementa": ementa,
                "presented_on": row.get("dataApresentacao") or "", "situation": situation.capitalize(),
                "stage": stage_senado(situation), "body": "Senado Federal",
                "authorship": "primeiro signatário" if _first_signatory(row.get("autoria", ""), name) else "coautor",
                "source_url": SENADO_MATERIA.format(code=row.get("codigoMateria")),
                "themes": list(tag_themes(ementa, 1)), "nature": nature_of(ementa),
            }
    return sorted(out.values(), key=lambda r: r["presented_on"])


def save_records(person_sq: str, records: list[dict]) -> int:
    conn = connect()
    try:
        install_trace_schema(conn)
        with conn:
            conn.execute("DELETE FROM execution_records WHERE person_sq=?", (person_sq,))
            conn.executemany(
                """INSERT OR REPLACE INTO execution_records(person_sq,identifier,kind,ementa,presented_on,situation,
                   stage,body,authorship,source_url,themes,nature) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                [(person_sq, r["identifier"], r["kind"], r["ementa"], r["presented_on"], r["situation"],
                  r["stage"], r["body"], r["authorship"], r["source_url"], ",".join(r["themes"]), r["nature"])
                 for r in records])
            person = PEOPLE[person_sq]
            conn.execute("DELETE FROM office_terms WHERE person_name=? AND started_at=?",
                         (person["name"], person["term_start"]))
            conn.execute("""INSERT INTO office_terms(person_name,office,jurisdiction,started_at,source_url)
                            VALUES (?,?,?,?,?)""",
                         (person["name"], person["office"], "Brasil" if person["scope"] == "executivo" else "RJ",
                          person["term_start"], person["term_source"]))
        return len(records)
    finally:
        conn.close()


def sync_person(person_sq: str, fetch: Callable = _get) -> dict:
    person = PEOPLE[person_sq]
    if person["scope"] == "executivo":
        records = collect_executive(person["years"], person["term_start"], fetch)
    else:
        records = collect_senate(person["senate_code"], person["name"], person["years"], fetch)
    count = save_records(person_sq, records)
    by_stage: dict[str, int] = {}
    for r in records:
        by_stage[r["stage"]] = by_stage.get(r["stage"], 0) + 1
    return {"person": person["name"], "records": count, "by_stage": by_stage}
