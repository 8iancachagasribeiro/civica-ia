"""Parsing de séries SIDRA: períodos, sexo e valores ausentes, sem rede."""
from app.sidra_source import SPECS, parse_ipca_groups, parse_rows, quarter_period

HEADER = {"V": "Valor"}


def test_quarter_codes_do_not_collide_with_months():
    assert quarter_period("202602", "2º trimestre 2026") == "2026T2"
    assert quarter_period("202609", "setembro 2026") == "setembro 2026"  # mensal não é tratado como trimestre


def test_parse_by_sex_skips_missing_values_and_keeps_total():
    rows = [HEADER,
            {"V": "3177", "D3C": "202602", "D3N": "2º trimestre 2026", "D4N": "Mulheres"},
            {"V": "3959", "D3C": "202602", "D3N": "2º trimestre 2026", "D4N": "Homens"},
            {"V": "..", "D3C": "202101", "D3N": "1º trimestre 2021", "D4N": "Mulheres"},
            {"V": "3621", "D3C": "202602", "D3N": "2º trimestre 2026", "D4N": "Total"}]
    out = parse_rows(rows, SPECS[0], "https://sidra.ibge.gov.br/tabela/5436")
    assert {r["indicator_code"] for r in out} == {"IBGE_5436_RENDIMENTO_MULHERES", "IBGE_5436_RENDIMENTO_HOMENS",
                                                  "IBGE_5436_RENDIMENTO_TOTAL"}
    assert all(r["period"] == "2026T2" for r in out)


def test_ipca_groups_are_labeled_as_cost_of_living():
    rows = [HEADER, {"V": "5.75", "D3C": "202609", "D4N": "6.Saúde e cuidados pessoais"},
            {"V": "9", "D3C": "202609", "D4N": "1.Alimentação e bebidas"}]
    out = parse_ipca_groups(rows, "https://sidra.ibge.gov.br/tabela/7060")
    assert len(out) == 1 and out[0]["indicator_code"] == "IBGE_7060_IPCA12M_SAUDE_E_CUIDADOS_PESSOAIS"
    assert "custo de vida" in out[0]["methodology"]
