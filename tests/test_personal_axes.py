"""Eixos de vida: filtros determinísticos, sem pontuação, sem sumário e sem ruído de substring."""
import json
import re
from app.personal_axes import AXES, PROFILE, SERIES, build_personal, is_toc, plan_hits, record_hits
from app.comparison import load_studies


def _profile_values():
    out = {}
    for f in PROFILE:
        out[f["key"]] = {o["value"] for o in f["options"]} if f["type"] == "radio" else {True}
    return out


def test_every_rule_refers_to_a_real_profile_option():
    values = _profile_values()
    for ax in AXES:
        rule = ax["applies"]
        assert rule.get("always") or rule["any"]
        for key, value in rule.get("any", []):
            assert value in values[key], (ax["id"], key, value)


def test_patterns_compile_and_axes_have_required_text():
    ids = [a["id"] for a in AXES]
    assert len(ids) == len(set(ids))
    for ax in AXES:
        re.compile(ax["plan"]); re.compile(ax["records"])
        assert ax["why"] and ax["check"] and ax["caveats"], ax["id"]
        for key in ax["series"]:
            assert key in SERIES


def test_studies_and_series_codes_exist():
    known = {s["id"] for s in load_studies()}
    for ax in AXES:
        assert set(ax["studies"]) <= known, ax["id"]
    for group in SERIES.values():
        for code in group["codes"].values():
            assert re.fullmatch(r"(IBGE|BCB)_[A-Z0-9_]+", code), code


def test_rent_pattern_does_not_match_allocation():
    rent = next(a for a in AXES if a["id"] == "aluguel")
    assert not re.search(rent["plan"], "a alocacao de capital e a realocacao de recursos")  # 'alocacao' não é aluguel
    assert re.search(rent["plan"], "contrato de locacao residencial")
    assert re.search(rent["plan"], "quem paga aluguel a vida inteira")


def test_table_of_contents_lines_are_ignored():
    assert is_toc("CRECHE GARANTIDA ........................ 21")
    assert not is_toc("Vamos ampliar a oferta de creches em período integral.")
    rows = [{"id": 1, "page": 3, "body": "Creche – ampliação de vagas ........ 21", "markers": [], "kind": "contexto"},
            {"id": 2, "page": 21, "body": "Vamos ampliar creches para as famílias.", "markers": [], "kind": "compromisso"}]
    picks, total = plan_hits(rows, r"\bcreches?\b")
    assert total == 1 and picks[0][0] == 2


def test_record_hits_ranks_by_fit_then_stage_and_skips_credit():
    recs = [
        {"identifier": "MPV 1/2025", "ementa": "Abre crédito extraordinário para moradia digna", "presented_on": "2025-01-01",
         "stage": "lei", "authorship": "Poder Executivo", "body": "Câmara", "source_url": "u", "nature": "credito"},
        {"identifier": "PL 2/2025", "ementa": "Programa Minha Casa: moradia digna e casa própria", "presented_on": "2025-02-01",
         "stage": "tramitando", "authorship": "Poder Executivo", "body": "Câmara", "source_url": "u", "nature": "politica"},
        {"identifier": "PL 3/2025", "ementa": "Trata de moradia digna", "presented_on": "2025-03-01",
         "stage": "lei", "authorship": "Poder Executivo", "body": "Câmara", "source_url": "u", "nature": "politica"},
    ]
    out = record_hits(recs, r"minha casa|moradia digna|casa propria")
    assert out["count"] == 2 and [i["id"] for i in out["items"]] == ["PL 2/2025", "PL 3/2025"]


def test_build_personal_is_symmetric_and_has_no_score():
    ex = [{"id": i, "page": i, "body": "Vamos ampliar creches e o Minha Casa Minha Vida.", "doc_type": "plano_eleitoral",
           "sq": sq, "election_year": 2026, "markers": [], "kind": "compromisso"}
          for i, sq in ((1, "280000000001"), (2, "280000000002"))]
    out = build_personal(ex, [])
    assert len(out["axes"]) == len(AXES)
    for ax in out["axes"]:
        assert set(ax["cands"]) == {"280000000001", "280000000002"}
    blob = json.dumps(out, ensure_ascii=False).lower()
    assert "score" not in blob and "ranking" not in blob and "melhor candidato" not in blob
