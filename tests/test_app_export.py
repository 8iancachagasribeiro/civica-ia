"""Snapshot must be populated only from sourced records, never a demo masquerading as facts."""
import json
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


def test_snapshot_exposes_comparison_without_score_or_ranking(tmp_path, monkeypatch):
    monkeypatch.setenv("CIVICA_DB",str(tmp_path/"data.sqlite3"))
    conn=connect()
    with conn:
        conn.execute("""INSERT INTO documents(id,title,person,election_year,doc_type,issuer,source_url,sha256)
        VALUES(1,'Plano de governo 2026 | Teste | 2026BR280000000001_01.pdf','Teste',2026,'plano_eleitoral','TSE','https://cdn.tse.jus.br/p.zip','h1')""")
        conn.execute("""INSERT INTO chunks(document_id,page,chunk_index,body,theme)
        VALUES(1,4,0,'Vamos ampliar o SUS e reduzir a fila até 2028.','saúde')""")
        conn.execute("""INSERT INTO execution_records(person_sq,identifier,kind,ementa,presented_on,situation,stage,body,authorship,source_url,themes,nature)
        VALUES('280000000001','PL 1/2024','PL','Dispõe sobre a saúde.','2024-02-01','Arquivada','encerrada','Câmara dos Deputados','Poder Executivo','https://www.camara.leg.br/x','saude','politica')""")
    conn.close()
    snap=build_snapshot()
    assert snap["schema_version"]=="app-snapshot-2"
    assert snap["excerpts"][0]["sq"]=="280000000001" and "saude" in snap["excerpts"][0]["themes"]
    plan=snap["comparison"]["plans"]["280000000001"]
    assert plan["saude"]["commitments"]==1 and plan["_chunks"]==1
    assert snap["comparison"]["execution"]["280000000001"]["summary"]["by_theme"]["saude"]["encerrada"]==1
    blob=json.dumps(snap["comparison"],ensure_ascii=False).lower()
    assert "score" not in blob and "ranking" not in blob and "melhor" not in blob
