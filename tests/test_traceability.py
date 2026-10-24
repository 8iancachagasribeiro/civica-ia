"""O vínculo entre promessa, ação e resultado exige evidência documental explícita."""
from fastapi.testclient import TestClient
from app.db import connect
from app.traceability import get_trace, install_trace_schema
from app.main import app


def test_empty_graph_is_explicit(monkeypatch,tmp_path):
    monkeypatch.setenv('CIVICA_DB',str(tmp_path/'graph.sqlite3'))
    client=TestClient(app)
    assert client.get('/api/evidence-trace/overview').json()['documented_actions']==0
    assert client.get('/api/evidence-trace/321').status_code==404


def test_documented_graph_has_no_automatic_attribution(monkeypatch,tmp_path):
    monkeypatch.setenv('CIVICA_DB',str(tmp_path/'graph.sqlite3'))
    conn=connect()
    install_trace_schema(conn)
    conn.execute("INSERT INTO documents(id,title,person,election_year,doc_type,issuer,source_url,sha256) VALUES(1,'Plano ficticio','Pessoa ficticia',2022,'plano','Exemplo','https://example.org/plano','sha-ficticio')")
    conn.execute("INSERT INTO commitments(id,document_id,page,exact_excerpt) VALUES(1,1,4,'Promessa ficticia')")
    conn.execute("INSERT INTO office_terms(id,person_name,office,jurisdiction,started_at,source_url) VALUES(1,'Pessoa ficticia','Cargo ficticio','Jurisdicao ficticia','2020-01-01','https://example.org/mandato')")
    conn.execute("INSERT INTO documented_actions(id,term_id,event_date,action_type,description,government_body,source_url) VALUES(1,1,'2021-01-01','projeto','Projeto ficticio','Orgao ficticio','https://example.org/ato')")
    conn.commit()
    # Coincidência de nome ou de tema não gera vínculo automaticamente.
    assert get_trace(1)['actions']==[]
    conn.execute("INSERT INTO commitment_action_links(commitment_id,action_id,relationship,evidence_url,reviewed_by,reviewed_at) VALUES(1,1,'relacionada','https://example.org/estudo','Revisor de teste','2026-01-01')")
    conn.commit()
    r=get_trace(1)
    assert len(r['actions'])==1
    assert r['actions'][0]['outcomes']==[]
    assert 'Não há recomendações eleitorais' in r['notices'][-1]
    conn.close()
