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


def test_bcb_actual_schema_is_parsed():
    from app.bcb_source import parse_bcb_ipca,import_bcb_ipca
    sample=[{'data':'01/07/2026','valor':'0.07'},{'data':'01/08/2026','valor':'-0.32'}]
    assert parse_bcb_ipca(sample)[0]['period']=='202607'
    class FakeResponse:
        content=json.dumps(sample).encode()
        def raise_for_status(self):pass
        def json(self):return sample
    class Session:
        def get(self,url,**kwargs):
            assert 'bcb.gov.br' in url
            return FakeResponse()
    assert import_bcb_ipca(session=Session())['rows']==2
    assert len(find_indicators('Inflação'))==2

def test_bcb_context_series_validate_metadata_and_deduplicate():
    from app.bcb_source import parse_bcb_context, import_bcb_context
    sample=[{"data":"01/07/2026","valor":"5,8"},{"data":"01/08/2026","valor":"5.6"}]
    url="https://api.bcb.gov.br/dados/serie/bcdata.sgs.24369/dados?formato=json"
    rows=parse_bcb_context(sample,24369,url)
    assert [row["period"] for row in rows]==["202607","202608"]
    assert rows[0]["source_issuer"].startswith("IBGE/")
    assert rows[1]["value"]==5.6
    class Response:
        content=json.dumps(sample).encode()
        def raise_for_status(self):pass
        def json(self):return sample
    class Session:
        def get(self,url,**kwargs):
            assert "sgs.24369" in url
            return Response()
    assert import_bcb_context(24369,session=Session())["rows"]==2
    assert import_bcb_context(24369,session=Session())["rows"]==2
    conn=connect()
    try:
        assert conn.execute("select count(*) from outcome_series").fetchone()[0]==2
        assert conn.execute("select count(*) from evidence_links").fetchone()[0]==0
    finally:conn.close()
    with pytest.raises(ValueError):
        parse_bcb_context([{"data":"01/08/2026","valor":"105"}]*2,24369,url)
    with pytest.raises(ValueError):
        import_bcb_context(99999,session=Session())
