import pytest
from fastapi.testclient import TestClient
from app.db import connect
from app.main import app
from app.crossings import factual_cross

@pytest.fixture(autouse=True)
def database(monkeypatch,tmp_path):
    monkeypatch.setenv('CIVICA_DB',str(tmp_path/'db.sqlite3'))

def test_cross_is_not_political_score_or_causal_join():
    conn=connect()
    with conn:
        conn.execute("""INSERT INTO documents(id,title,person,election_year,doc_type,issuer,source_url,sha256)
           VALUES (1,'Plano fictício','Pessoa de teste',2022,'plano_eleitoral','Origem','https://example.org/1','abcd')""")
        conn.execute("""INSERT INTO chunks(document_id,page,chunk_index,body,theme)
           VALUES (1,2,0,'Uma escola fictícia e alfabetização','educação')""")
        conn.execute("""INSERT INTO documents(id,title,person,election_year,doc_type,issuer,source_url,sha256)
           VALUES (2,'Projeto fictício','',NULL,'proposicao_legislativa','Origem','https://example.org/2','efgh')""")
        conn.execute("""INSERT INTO chunks(document_id,page,chunk_index,body,theme)
           VALUES (2,1,0,'Projeto sobre escola fictícia','educação')""")
        conn.execute("""INSERT INTO outcome_series(indicator_code,indicator_name,unit,period,territory,population,value,source_url,source_issuer)
           VALUES ('X','Educação fictícia','%',2024,'Brasil','Agregado',3.4,'https://example.org/3','Teste')""")
    conn.close()
    x=factual_cross('educação',2024)
    assert len(x['electoral_plans'])==1
    assert len(x['legislative_proposals'])==1
    assert x['observed_indicators'][0]['value']==3.4
    assert 'Nenhum vínculo causal' in x['relation']
    assert 'score' not in x and 'ranking' not in x
    assert TestClient(app).get('/api/public-cross',params={'tema':'educação','ano':2024}).status_code==200
    assert TestClient(app).get('/api/public-cross',params={'tema':'tema_fake'}).status_code==422
