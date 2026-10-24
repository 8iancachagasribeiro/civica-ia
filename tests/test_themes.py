"""Classificação por tema: fronteira de palavra, multirrótulo e leitura de passagens."""
from app.themes import LABELS, anchor, norm_same_len, read_passage, tag_themes, theme_scores


def test_sus_does_not_match_sustentavel():
    # Regressão: a busca por trecho de palavra marcava "sustentável" como Saúde.
    assert "saude" not in theme_scores("Um país soberano, democrático, desenvolvido e sustentável")
    assert "saude" not in tag_themes("Promover a sustentabilidade ambiental")
    assert "saude" in tag_themes("Fortalecer o SUS e a atenção básica")


def test_accents_and_case_are_ignored():
    assert "educacao" in tag_themes("EDUCAÇÃO básica e alfabetização na idade certa")
    assert "seguranca" in tag_themes("Segurança pública e combate ao crime organizado")
    assert "seguranca" not in tag_themes("Segurança alimentar e nutricional")


def test_one_passage_can_belong_to_several_themes():
    themes = tag_themes("Ampliar creches e escola em tempo integral, com educação para mulheres trabalhadoras")
    assert {"educacao", "mulheres"} <= set(themes)


def test_all_labels_are_unique_and_normalized_keys():
    assert len(LABELS) == len(set(LABELS)) == 8
    assert all(k == k.lower() and " " not in k for k in LABELS)


def test_read_passage_separates_promise_from_claim():
    promise = read_passage("Vamos ampliar as vagas e reduzir a fila até 2028, com R$ 10 bilhões do orçamento.")
    assert promise["kind"] == "compromisso"
    assert set(promise["markers"]) == {"n", "p", "r"}
    claim = read_passage("O governo criou o programa, ampliou a rede e entregou 2 mil unidades.")
    assert claim["kind"] == "balanco"
    assert read_passage("O país enfrenta desafios históricos.")["kind"] == "contexto"


def test_anchor_points_to_the_theme_term_in_the_original_text():
    text = "Introdução longa… O SUS será fortalecido."
    assert text[anchor(text, "saude"):].startswith("SUS")
    assert len(norm_same_len("Ação… ½ ﬁm")) == len("Ação… ½ ﬁm")
