"""Coletores de registro legislativo: estágio, autoria verificada e escopo, sem rede."""
import pytest
from app import execution_sources as ex
from app.db import connect


@pytest.fixture(autouse=True)
def database(monkeypatch, tmp_path):
    monkeypatch.setenv("CIVICA_DB", str(tmp_path / "db.sqlite3"))


def test_stage_mapping_does_not_turn_lapsed_provisional_measure_into_failure():
    assert ex.stage_camara("Transformado em Norma Jurídica") == "lei"
    assert ex.stage_camara("Perdeu a Eficácia") == "perdeu_eficacia"
    assert ex.stage_camara("Aguardando Apreciação pelo Senado Federal") == "aprovada"
    assert ex.stage_camara("Arquivada") == "encerrada"
    assert ex.stage_camara("") == "tramitando"
    assert ex.stage_senado("Remetida à Câmara dos Deputados") == "aprovada"
    assert ex.stage_senado("Transformada em norma jurídica com veto parcial") == "lei"
    assert ex.stage_senado("Aguardando designação do relator") == "tramitando"


def test_credit_openings_are_flagged():
    assert ex.nature_of("Abre crédito extraordinário, em favor do Ministério da Saúde") == "credito"
    assert ex.nature_of("Institui o Programa Agora Tem Especialistas") == "politica"


def test_first_signatory_vs_cosigner():
    text = "Senador Marcos do Val (PODEMOS/ES), Senador Flávio Bolsonaro (PL/RJ)"
    assert not ex._first_signatory(text, "Flávio Bolsonaro")
    assert ex._first_signatory("Senador Flávio Bolsonaro (PL/RJ), Senadora Ana (PT/BA)", "Flávio Bolsonaro")


def _camara_fetch(url, params=None):
    if url.endswith("/proposicoes"):
        return {"dados": [{"id": 1}, {"id": 2}, {"id": 3}] if params["siglaTipo"] == "PL" else []}
    pid = int(url.rstrip("/").split("/")[-2 if url.endswith("/autores") else -1])
    if url.endswith("/autores"):
        return {"dados": [{"nome": "Poder Executivo" if pid != 2 else "Dep. Fulano", "proponente": 1}]}
    return {"dados": {"siglaTipo": "PL", "numero": pid, "ano": 2024, "ementa": "Dispõe sobre a saúde pública.",
                      "dataApresentacao": "2022-12-30T10:00" if pid == 3 else "2024-02-01T10:00",
                      "statusProposicao": {"descricaoSituacao": "Transformado em Norma Jurídica"}}}


def test_executive_collection_checks_authorship_and_term_start():
    rows = ex.collect_executive([2024], "2023-01-01", fetch=_camara_fetch, workers=1)
    assert [r["identifier"] for r in rows] == ["PL 1/2024"]  # 2: outro autor; 3: antes do mandato
    assert rows[0]["stage"] == "lei" and "saude" in rows[0]["themes"]
    assert rows[0]["source_url"].startswith("https://www.camara.leg.br/")


def test_senate_collection_keeps_bills_and_separates_authorship():
    def fetch(url, params=None):
        return [
            {"identificacao": "PL 10/2024", "autoria": "Senador Flávio Bolsonaro (PL/RJ)", "ementa": "Segurança pública.",
             "dataApresentacao": "2024-03-01", "situacaoAtual": "AGUARDANDO DESIGNAÇÃO DO RELATOR", "codigoMateria": 99},
            {"identificacao": "RQS 3/2024", "autoria": "Senador Flávio Bolsonaro (PL/RJ)", "ementa": "Voto de aplauso.",
             "dataApresentacao": "2024-03-02", "situacaoAtual": "APROVADO", "codigoMateria": 100},
            {"identificacao": "PEC 5/2024", "autoria": "Senador Zé (X/Y), Senador Flávio Bolsonaro (PL/RJ)", "ementa": "Altera a Constituição.",
             "dataApresentacao": "2024-03-03", "situacaoAtual": "REMETIDA À CÂMARA", "codigoMateria": 101},
        ]
    rows = ex.collect_senate(5894, "Flávio Bolsonaro", [2024], fetch=fetch)
    assert [r["identifier"] for r in rows] == ["PL 10/2024", "PEC 5/2024"]  # requerimento excluído
    assert [r["authorship"] for r in rows] == ["primeiro signatário", "coautor"]
    assert rows[0]["source_url"].endswith("/99") and rows[1]["stage"] == "aprovada"


def test_save_records_is_idempotent_and_records_the_term():
    sq = "280002551544"
    records = ex.collect_senate(5894, "Flávio Bolsonaro", [2024], fetch=lambda u, p=None: [
        {"identificacao": "PL 10/2024", "autoria": "Senador Flávio Bolsonaro (PL/RJ)", "ementa": "Armas.",
         "dataApresentacao": "2024-03-01", "situacaoAtual": "ARQUIVADA", "codigoMateria": 99}])
    assert ex.save_records(sq, records) == 1 and ex.save_records(sq, records) == 1
    conn = connect()
    assert conn.execute("SELECT count(*) FROM execution_records").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM office_terms").fetchone()[0] == 1
    conn.close()
