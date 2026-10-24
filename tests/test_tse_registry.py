"""Cadastro oficial de candidaturas e conferência do manifesto de planos."""
import json
from pathlib import Path
from app.ingest import MANIFESTS
from app.tse_registry import parse_presidents, verify_manifest

HEADER = "NR_TURNO;DS_CARGO;SQ_CANDIDATO;NM_CANDIDATO;NM_URNA_CANDIDATO;SG_PARTIDO;NR_CANDIDATO;DS_SITUACAO_CANDIDATURA;DS_SIT_TOT_TURNO"
CSV = "\n".join([
    HEADER,
    "1;PRESIDENTE;280002542548;LUIZ INÁCIO LULA DA SILVA;LULA;PT;13;#NE;2º TURNO",
    "2;PRESIDENTE;280002542548;LUIZ INÁCIO LULA DA SILVA;LULA;PT;13;#NE;#NULO",
    "1;PRESIDENTE;280002554479;LEONARDO ALVES DE ARAUJO;LEONARDO AVALANCHE;PRTB;28;#NE;NÃO ELEITO",
    "1;GOVERNADOR;280009999999;FULANO;FULANO;X;11;#NE;ELEITO",
])


def test_parse_presidents_uses_first_round_result_and_ignores_other_offices():
    rows = parse_presidents(CSV)
    assert [r["sq"] for r in rows] == ["280002542548", "280002554479"]
    assert rows[0]["in_runoff"] and not rows[1]["in_runoff"]
    assert rows[0]["name"] == "Luiz Inácio Lula da Silva"


def test_verify_manifest_detects_swapped_missing_and_unmapped():
    cands = parse_presidents(CSV)
    ok = {"2026BR280002542548": "Luiz Inácio Lula da Silva", "2026BR280002554479": "Leonardo Avalanche"}
    assert verify_manifest(ok, 2026, cands) == []
    swapped = {**ok, "2026BR280002542548": "Flávio Bolsonaro"}
    assert any("Flávio Bolsonaro" in p for p in verify_manifest(swapped, 2026, cands))
    assert any("ausente" in p for p in verify_manifest({**ok, "2026BR280000000001": "X"}, 2026, cands))
    assert any("sem plano" in p for p in verify_manifest({"2026BR280002542548": "Luiz Inácio Lula da Silva"}, 2026, cands))


def test_committed_manifest_matches_committed_registry():
    path = Path("data/sources/tse_presidente_2026.json")
    if not path.exists():
        return
    registry = json.loads(path.read_text(encoding="utf-8"))
    assert verify_manifest(MANIFESTS[2026], 2026, registry["candidates"]) == []
