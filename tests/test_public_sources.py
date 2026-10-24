import json
import pytest
from app.public_sources import parse_ibge_ipca, import_ibge_ipca, source_json
from app.db import connect
from app.core import find_indicators

@pytest.fixture(autouse=True)
def database(monkeypatch,tmp_path):
    monkeypatch.setenv('CIVICA_DB',str(tmp_path/'db.sqlite3'))

def fixture_payload():
    return [{'id':'1737','variavel':'IPCA - Variação mensal','unidade':'%',
       'resultados':[{'classificacoes':[],'series':[{'localidade':{'id':'1','nome':'Brasil'},
          'serie':{'202401':'0.42','202402':'0.83','202403':'...'}}]}]}]

def test_validates_retrieved_values_and_metadata():
    values=parse_ibge_ipca(fixture_payload())
    assert len(values)==2
    assert values[0]['period']=='202401'
    assert values[1]['value']==0.83
    assert values[0]['source_issuer']=='IBGE/SIDRA'
    with pytest.raises(ValueError):parse_ibge_ipca([])
    with pytest.raises(ValueError):parse_ibge_ipca([{'id':1419,'variavel':'IPCA'}])

def test_official_import_idempotent_and_no_causal_links():
    class Response:
        content=json.dumps(fixture_payload()).encode()
        def raise_for_status(self):pass
        def json(self):return fixture_payload()
    class Session:
        def get(self,url,**kwargs):
            assert 'servicodados.ibge.gov.br' in url
            return Response()
    s=Session()
    assert import_ibge_ipca(session=s)['rows']==2
    assert import_ibge_ipca(session=s)['rows']==2
    conn=connect()
    try:
        assert conn.execute('select count(*) FROM outcome_series').fetchone()[0]==2
        assert conn.execute('select count(*) FROM evidence_links').fetchone()[0]==0
    finally:conn.close()
    assert len(find_indicators('IPCA'))==2

def test_ssrf_prevention():
    with pytest.raises(ValueError):source_json('https://example.org/no')
