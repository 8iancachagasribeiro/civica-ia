import os
import tempfile
from pathlib import Path
import fitz
import pytest
from fastapi.testclient import TestClient

from app.db import connect
from app.core import is_voting_recommendation,find_evidence,find_indicators
from app.ingest import import_pdf,split_chunks,import_indicators
from app.main import app

@pytest.fixture(autouse=True)
def isolated_database(monkeypatch,tmp_path):
    monkeypatch.setenv('CIVICA_DB',str(tmp_path/'db.sqlite3'))
    monkeypatch.setenv('CIVICA_MODE','extractive')


def fake_pdf():
    p=fitz.open()
    a=p.new_page()
    a.insert_text((72,72),'Texto de exemplo ficticio sobre alfabetizacao na escola publica.')
    b=p.new_page()
    b.insert_text((72,72),'Texto de exemplo ficticio sobre vacina e saude publica.')
    out=p.tobytes()
    p.close()
    return out


def test_pdf_import_search_and_provenance():
    pdf=fake_pdf()
    r=import_pdf(pdf,title='Documento ficticio de teste',person='',year=2022,
                 kind='teste',issuer='Teste automatizado',source_url='https://example.org/test.pdf')
    assert r['pages']==2
    assert r['chunks']==2
    assert r['sha256']
    assert import_pdf(pdf,title='Documento ficticio de teste',person='',year=2022,
                 kind='teste',issuer='Teste automatizado',source_url='https://example.org/test.pdf')['already_exists']
    found=find_evidence('Quais registros sobre alfabetizacao?')
    assert len(found)>0
    assert found[0]['page']==1
    assert found[0]['source_url']=='https://example.org/test.pdf'
    assert find_evidence('vacina')[0]['page']==2


def test_public_api_has_no_hardcoded_recommendation():
    client=TestClient(app)
    assert client.get('/health').json()['status']=='ok'
    assert client.get('/').status_code==200
    r=client.post('/api/ask',json={'question':'Qual o melhor candidato Lula ou Bolsonaro?'})
    assert r.status_code==200
    data=r.json()
    assert data['recommendation_blocked'] is True
    assert 'Não classifico' in data['answer']
    assert data['sources']==[]
    assert client.get('/api/documents').json()['documents']==[]


def test_guard_and_empty_search():
    assert is_voting_recommendation('Qual o melhor candidato Lula ou Bolsonaro?')
    assert is_voting_recommendation('Em quem devo votar nas eleições?')
    assert is_voting_recommendation('Pode fazer ranking de políticos?')
    assert not is_voting_recommendation('O que os planos registraram sobre o SUS?')
    assert find_evidence('')==[]
    assert find_evidence('"')==[]


def test_indicator_import_is_not_causal_join(tmp_path):
    f=tmp_path/'ind.csv'
    f.write_text('indicator_code,indicator_name,unit,period,territory,population,value,source_url,source_issuer,methodology\n'
                 'INDX,Taxa de alfabetizacao,%,2022,Brasil,populacao,91.3,https://example.org/data,Orgao ficticio,Dados de teste\n',encoding='utf-8')
    assert import_indicators(f)==1
    assert len(find_indicators('alfabetizacao'))==1
    conn=connect()
    try:
        assert conn.execute('SELECT count(*) FROM evidence_links').fetchone()[0]==0
    finally:conn.close()


def test_chunk_overlap_has_full_coverage():
    text='palavra '*500
    chunks=split_chunks(text,max_chars=200,overlap=30)
    assert len(chunks)>1
    assert 'palavra' in chunks[-1]
