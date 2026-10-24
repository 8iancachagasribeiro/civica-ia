"""Snapshot must be populated only from sourced records, never a demo masquerading as facts."""
from scripts.export_app_data import build_snapshot, official_url
from app.db import connect

def test_domain_allowlist():
    assert official_url("https://api.bcb.gov.br/dados")
    assert official_url("https://cdn.tse.jus.br/planos.zip")
    assert not official_url("https://tse.jus.br.malicioso.exemplo/p")
    assert not official_url("http://dados.ibge.gov.br/a")

def test_snapshot_no_fake_records(tmp_path, monkeypatch):
    monkeypatch.setenv("CIVICA_DB",str(tmp_path/"data.sqlite3"))
    conn=connect()
    with conn:
        conn.execute("""INSERT INTO documents(id,title,person,election_year,doc_type,issuer,source_url,sha256)
        VALUES(1,'Fonte de teste','','2022','plano_eleitoral','TSE','https://dadosabertos.tse.jus.br/ficticio','ficticio')""")
        conn.execute("""INSERT INTO chunks(document_id,page,chunk_index,body,theme)
        VALUES(1,1,0,'Educação teste sem relação causal','educação')""")
        conn.execute("""INSERT INTO outcome_series(indicator_code,indicator_name,unit,period,territory,population,value,source_url,source_issuer)
        VALUES('X','IPCA teste','%',202401,'Brasil','Agregado',1.1,'https://api.bcb.gov.br/ficticio','BCB')""")
    conn.close()
    snapshot=build_snapshot()
    assert snapshot["counts"] == {"documents":1,"excerpts":1,"indicators":1}
    assert snapshot["excerpts"][0]["page"] == 1
    assert "não comprova execução" in snapshot["methodology"]
