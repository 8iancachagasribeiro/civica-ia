"""Selic e juros imobiliários: parsing sem rede."""
from app.bcb_rates import parse_mortgage, parse_selic
from app.sidra_source import IPCA_ITEMS, parse_ipca_items


def test_selic_keeps_last_value_of_each_month():
    rows = [{"data": "01/03/2026", "valor": "14.75"}, {"data": "31/03/2026", "valor": "14.75"},
            {"data": "01/04/2026", "valor": "14.75"}, {"data": "30/04/2026", "valor": "14.50"}]
    out = parse_selic(rows)
    assert [(r["period"], r["value"]) for r in out] == [("202603", 14.75), ("202604", 14.5)]
    assert out[0]["indicator_code"] == "BCB_SGS_432_SELIC_META"


def test_mortgage_groups_by_modality_median_and_caixa_and_skips_zero_rates():
    def row(inst, rate, mod="Financiamento imobiliário com taxas reguladas - Pós-fixado referenciado em TR"):
        return {"anoMes": "2026-09", "Modalidade": mod, "InstituicaoFinanceira": inst, "TaxaJurosAoAno": rate}
    rows = [row("CAIXA ECONOMICA FEDERAL", 8.0), row("BANCO A", 10.0), row("BANCO B", 12.0), row("BANCO C", 0.0),
            row("BANCO D", 9.0, "Financiamento imobiliário com taxas reguladas - Pós-fixado referenciado em IPCA")]
    out = {r["indicator_code"]: r for r in parse_mortgage(rows)}
    assert set(out) == {"BCB_OLINDA_IMOB_REGULADA_TR_MEDIANA", "BCB_OLINDA_IMOB_REGULADA_TR_CAIXA"}
    assert out["BCB_OLINDA_IMOB_REGULADA_TR_MEDIANA"]["value"] == 10.0  # mediana de 8, 10, 12 (zero excluído)
    assert out["BCB_OLINDA_IMOB_REGULADA_TR_CAIXA"]["value"] == 8.0
    assert out["BCB_OLINDA_IMOB_REGULADA_TR_MEDIANA"]["period"] == "202609"


def test_ipca_items_use_ascii_codes_and_skip_unknown_items():
    rows = [{"V": "x"}, {"V": "4.71", "D3C": "202609", "D4C": "7448"}, {"V": "1", "D3C": "202609", "D4C": "9999"},
            {"V": "..", "D3C": "202609", "D4C": "7449"}]
    out = parse_ipca_items(rows, "https://sidra.ibge.gov.br/tabela/7060")
    assert [r["indicator_code"] for r in out] == ["IBGE_7060_IPCA12M_ITEM_ALUGUEL_RESIDENCIAL"]
    assert "7448" in IPCA_ITEMS
