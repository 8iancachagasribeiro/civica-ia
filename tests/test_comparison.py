"""Resumo candidatura × tema: simetria estrutural, sem pontuação e vínculo a estudos."""
import json
from pathlib import Path
from app.comparison import enrich_excerpt, load_studies, summarize_execution, summarize_plans
from app.themes import LABELS

BODY_A = "Vamos ampliar o SUS e a vacinação até 2028, com R$ 5 bilhões. Manteremos o Bolsa Família."
BODY_B = "O governo criou a Farmácia Popular e ampliou a atenção básica do SUS."


def _row(i, sq, body, page, year=2026):
    return enrich_excerpt({"id": i, "document_id": 1, "page": page, "body": body, "theme": "saúde", "title":
                           f"Plano | X | {year}BR{sq}_01.pdf", "person": "X", "doc_type": "plano_eleitoral",
                           "source_url": "https://cdn.tse.jus.br/x.zip", "election_year": year})


def test_summary_has_identical_shape_for_every_candidate_and_no_score():
    rows = [_row(1, "280000000001", BODY_A, 3), _row(2, "280000000002", BODY_B, 4)]
    out = summarize_plans(rows, load_studies())
    assert set(out) == {"280000000001", "280000000002"}
    for sq in out:
        assert {t for t in out[sq] if not t.startswith("_")} == set(LABELS)
        blob = json.dumps(out[sq])
        assert "score" not in blob and "rank" not in blob and "melhor" not in blob
    a, b = out["280000000001"]["saude"], out["280000000002"]["saude"]
    assert a["commitments"] == 1 and a["with_number"] == 1 and a["with_deadline"] == 1 and a["with_funding"] == 0
    assert b["claims"] == 1 and b["commitments"] == 0
    assert [s["study"] for s in a["studies"]] == ["pbf-mortalidade-infantil-2013"]
    assert a["top_commitments"][0][0] == 1 and isinstance(a["top_commitments"][0][1], int)


def test_only_the_requested_election_year_is_summarized():
    rows = [_row(1, "280000000001", BODY_A, 3, year=2022)]
    assert summarize_plans(rows, []) == {}


def test_execution_summary_counts_stage_and_keeps_credit_separate():
    recs = [{"stage": "lei", "themes": ["saude"], "authorship": "Poder Executivo", "nature": "politica"},
            {"stage": "perdeu_eficacia", "themes": ["saude"], "authorship": "Poder Executivo", "nature": "credito"},
            {"stage": "tramitando", "themes": [], "authorship": "coautor", "nature": "politica"}]
    s = summarize_execution(recs)
    assert s["total"] == 3 and s["by_theme"]["saude"]["total"] == 2
    assert s["by_theme"]["saude"]["credito"] == 1 and s["by_theme"]["saude"]["perdeu_eficacia"] == 1
    assert s["principal"] == 2


def test_impact_studies_file_is_well_formed_and_sourced():
    studies = json.loads(Path("app/static/data/impact_studies.json").read_text(encoding="utf-8"))["studies"]
    labels = set(LABELS.values())
    ids = [s["id"] for s in studies]
    assert len(ids) == len(set(ids))
    for s in studies:
        for field in ("policy", "outcome", "estimate", "period", "population", "method", "limits",
                      "source_title", "source_url", "type", "policy_patterns", "themes"):
            assert s.get(field), (s["id"], field)
        assert s["source_url"].startswith("https://")
        assert s["type"] in {"contrafactual", "quase_experimental", "painel_ajustado", "tendencia"}
        assert set(s["themes"]) <= labels
        assert len(s["limits"]) > 40  # limites obrigatórios e substantivos
        import re
        [re.compile(p) for p in s["policy_patterns"]]
