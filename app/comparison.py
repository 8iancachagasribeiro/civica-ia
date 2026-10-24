"""Resumo simétrico por candidatura × tema: o que pretende, o que alega e o que há de registro oficial.

Princípios: mesma estrutura e mesmo número de itens para toda candidatura; nenhuma pontuação,
ordem de mérito ou "melhor" entre candidaturas. A ordenação ocorre só DENTRO de cada
candidatura × tema, por aderência lexical ao tema e presença de marcadores de especificidade.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from .core import norm
from .themes import LABELS, THEME_INDICATORS, anchor, anchor_regex, tag_themes, read_passage

TOP_COMMITMENTS = 3
TOP_CLAIMS = 2
PLAN_SQ = re.compile(r"\b(\d{4})BR(\d{12})_\d+\.pdf\b")
STUDIES_FILE = Path("app/static/data/impact_studies.json")
# Passagens do tema que citam literalmente cada governo; não verifica o feito citado.
GOVERNMENTS = {
    "bolsonaro": re.compile(r"\bgoverno (?:do )?(?:presidente )?(?:jair )?bolsonaro\b|\bgestao bolsonaro\b"),
    "lula": re.compile(r"\bgoverno (?:do )?(?:presidente )?lula\b|\bgestao lula\b|\bcom lula\b"),
}


def plan_sq(title: str) -> str | None:
    m = PLAN_SQ.search(title or "")
    return m.group(2) if m else None


def enrich_excerpt(row: dict) -> dict:
    """Etiquetas de tema (todas as fontes) e leitura da passagem (somente planos)."""
    themes = tag_themes(row["body"])
    if themes:
        row["themes"] = themes
    if row.get("doc_type") == "plano_eleitoral":
        read = read_passage(row["body"])
        row["kind"], row["markers"] = read["kind"], read["markers"]
        sq = plan_sq(row.get("title", ""))
        if sq:
            row["sq"] = sq
    return row


def _rank(row: dict, theme: str) -> tuple:
    return (-(row["themes"][theme] + 2 * len(row["markers"])), row["page"], row["id"])


def _pick(rows: list[dict], theme: str, limit: int) -> list[list[int]]:
    """[[id do trecho, posição do termo do tema]], no máximo um trecho por página."""
    chosen, pages = [], set()
    for row in sorted(rows, key=lambda r: _rank(r, theme)):
        if row["page"] in pages:
            continue
        chosen.append([row["id"], anchor(row["body"], theme)])
        pages.add(row["page"])
        if len(chosen) == limit:
            break
    return chosen


def load_studies(path: Path = STUDIES_FILE) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("studies", [])


def _theme_key(label: str) -> str | None:
    wanted = norm(label)
    return next((k for k, lab in LABELS.items() if norm(lab) == wanted), None)


def study_matches(study: dict, text_norm: str) -> bool:
    return any(re.search(rx, text_norm) for rx in study.get("policy_patterns", []))


def summarize_plans(excerpts: list[dict], studies: list[dict], year: int = 2026) -> dict:
    """{sq: {tema: contagens, ids dos trechos e estudos citados}} para planos do ano."""
    plans = [r for r in excerpts if r.get("doc_type") == "plano_eleitoral" and r.get("sq") and r.get("themes")
             and r.get("election_year") == year]
    every = [r for r in excerpts if r.get("doc_type") == "plano_eleitoral" and r.get("sq")
             and r.get("election_year") == year]
    out: dict[str, dict] = {}
    for sq in sorted({r["sq"] for r in every}):
        mine = [r for r in plans if r["sq"] == sq]
        out[sq] = {"_chunks": sum(r["sq"] == sq for r in every)}
        for theme in LABELS:
            rows = [r for r in mine if theme in r["themes"]]
            if not rows:
                out[sq][theme] = {"passages": 0}
                continue
            commits = [r for r in rows if r["kind"] == "compromisso"]
            claims = [r for r in rows if r["kind"] == "balanco"]
            linked = []
            for study in studies:
                if not any(_theme_key(t) == theme for t in study["themes"]):
                    continue
                hits = [r for r in rows if study_matches(study, norm(r["body"]))]
                if hits:
                    pattern = next(rx for rx in study["policy_patterns"] if re.search(rx, norm(hits[0]["body"])))
                    linked.append({"study": study["id"], "passages": [[r["id"], anchor_regex(r["body"], pattern)]
                                                                      for r in hits[:3]]})
            out[sq][theme] = {
                "passages": len(rows), "commitments": len(commits), "claims": len(claims),
                "with_number": sum("n" in r["markers"] for r in commits),
                "with_deadline": sum("p" in r["markers"] for r in commits),
                "with_funding": sum("r" in r["markers"] for r in commits),
                "cites_gov": {k: sum(bool(rx.search(norm(r["body"]))) for r in rows) for k, rx in GOVERNMENTS.items()},
                "top_commitments": _pick(commits, theme, TOP_COMMITMENTS),
                "top_claims": _pick(claims, theme, TOP_CLAIMS),
                "studies": linked,
            }
    return out


STAGES = ("lei", "aprovada", "tramitando", "encerrada", "perdeu_eficacia")


def summarize_execution(records: list[dict]) -> dict:
    """Contagens por tema × estágio; o estágio nunca é traduzido em mérito."""
    def count(rows: list[dict]) -> dict:
        return {"total": len(rows), **{st: sum(r["stage"] == st for r in rows) for st in STAGES},
                "credito": sum(r.get("nature") == "credito" for r in rows),
                "principal": sum(r["authorship"] in ("Poder Executivo", "primeiro signatário") for r in rows)}
    return {**count(records), "by_theme": {t: count([r for r in records if t in r["themes"]]) for t in LABELS}}


def indicators_by_theme() -> dict:
    return THEME_INDICATORS
