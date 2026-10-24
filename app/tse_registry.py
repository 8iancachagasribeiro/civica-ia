"""Cadastro oficial de candidaturas presidenciais (TSE, dados abertos).

É a fonte de identidade dos planos: o ``SQ_CANDIDATO`` do cadastro é a chave do nome
do arquivo do plano. O manifesto em ``app/ingest.py`` é conferido contra este cadastro.
"""
from __future__ import annotations
import csv
import hashlib
import io
import time
import zipfile
from datetime import datetime, timezone
import requests
from .core import norm

_SMALL = {"da", "de", "do", "das", "dos", "e"}


def _title(name: str) -> str:
    return " ".join(w.lower() if w.lower() in _SMALL else w.capitalize() for w in name.split())

REGISTRY_URLS = {
    2022: "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2022.zip",
    2026: "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2026.zip",
}
MAX_ZIP = 30_000_000


def parse_presidents(csv_text: str) -> list[dict]:
    """Candidatos a Presidente. O 1º turno traz a situação de totalização ("2º TURNO")."""
    rows: dict[str, dict] = {}
    for row in csv.DictReader(io.StringIO(csv_text), delimiter=";"):
        if row.get("DS_CARGO") != "PRESIDENTE":
            continue
        sq = row["SQ_CANDIDATO"]
        turn = str(row.get("NR_TURNO", "1"))
        item = rows.setdefault(sq, {
            "sq": sq, "name": _title(row["NM_CANDIDATO"]), "ballot_name": row["NM_URNA_CANDIDATO"],
            "party": row["SG_PARTIDO"], "number": row["NR_CANDIDATO"],
            "registration_status": row["DS_SITUACAO_CANDIDATURA"], "result_first_round": None,
        })
        if turn == "1":
            item["result_first_round"] = row.get("DS_SIT_TOT_TURNO") or None
    out = sorted(rows.values(), key=lambda r: int(r["number"]))
    for item in out:
        item["in_runoff"] = item["result_first_round"] == "2º TURNO"
    return out


def fetch_presidents(year: int) -> dict:
    url = REGISTRY_URLS[year]
    for attempt in range(4):
        try:
            resp = requests.get(url, timeout=(15, 180),
                                headers={"User-Agent": "Civica-Evidencias/0.1 (pesquisa; fonte TSE)"})
            resp.raise_for_status()
            break
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    if len(resp.content) > MAX_ZIP:
        raise ValueError("ZIP do cadastro TSE excede o limite esperado")
    sha = hashlib.sha256(resp.content).hexdigest()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
        name = f"consulta_cand_{year}_BR.csv"
        if name not in archive.namelist():
            raise ValueError("Arquivo nacional ausente no ZIP do cadastro")
        text = archive.read(name).decode("latin-1")
    candidates = parse_presidents(text)
    if not candidates:
        raise ValueError("Nenhuma candidatura presidencial encontrada")
    return {
        "source_name": "TSE, consulta de candidaturas (dados abertos)",
        "source_url": url, "year": year, "zip_sha256": sha,
        "accessed_at": datetime.now(timezone.utc).isoformat(), "candidates": candidates,
    }


def verify_manifest(manifest: dict[str, str], year: int, candidates: list[dict]) -> list[str]:
    """Problemas do manifesto (nome do arquivo → pessoa) frente ao cadastro oficial."""
    by_sq = {c["sq"]: c for c in candidates}
    problems = []
    for key, person in manifest.items():
        sq = key[len(f"{year}BR"):]
        cand = by_sq.get(sq)
        if cand is None:
            problems.append(f"{key}: SQ_CANDIDATO ausente do cadastro oficial")
            continue
        tokens = {t for t in norm(person).split() if t not in _SMALL}
        official = set(norm(cand["name"]).split()) | set(norm(cand["ballot_name"]).split())
        if not tokens <= official:
            problems.append(f"{key}: manifesto diz '{person}', cadastro diz '{cand['name']}'")
    for sq, cand in by_sq.items():
        if not any(k.endswith(sq) for k in manifest):
            problems.append(f"{cand['name']} ({sq}): candidatura sem plano mapeado no manifesto")
    return problems
