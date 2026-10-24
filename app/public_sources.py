"""Importador da série nacional de inflação IBGE (dados da API oficial, sem atribuição causal)."""
from __future__ import annotations
import hashlib
import math
from datetime import datetime, timezone
import requests
from .db import connect

IBGE_IPCA_URL = ('https://servicodados.ibge.gov.br/api/v3/agregados/1737/'
                 'periodos/-36/variaveis/63?localidades=N1%5Ball%5D')

def source_json(url: str, *, session=None, timeout=50):
    if url != IBGE_IPCA_URL:
        raise ValueError('Fonte não autorizada')
    client = session if session is not None else requests
    response = client.get(url, timeout=(10,timeout),headers={'Accept':'application/json','User-Agent':'Civica-IA/0.3'})
    response.raise_for_status()
    if len(response.content)>4_000_000: raise ValueError('Resposta excessiva')
    return response.json(),hashlib.sha256(response.content).hexdigest()

def parse_ibge_ipca(payload:object,source_url:str=IBGE_IPCA_URL)->list[dict]:
    if not isinstance(payload,list) or len(payload)!=1 or not isinstance(payload[0],dict):
        raise ValueError('Formato IBGE inesperado')
    table=payload[0]
    if str(table.get('id'))!='1737' or 'IPCA' not in str(table.get('variavel','')).upper():
        raise ValueError('Tabela ou variável IBGE inesperada')
    results=table.get('resultados',[])
    if not isinstance(results,list):raise ValueError('Resultados ausentes')
    found={}
    for result in results:
        for series in result.get('series',[]):
            loc=series.get('localidade',{})
            if str(loc.get('id'))!='1' or loc.get('nome')!='Brasil':continue
            for period,value in series.get('serie',{}).items():
                if not(isinstance(period,str) and len(period)==6 and period.isdigit()):continue
                if value in (None,'','-','...','..','X'):continue
                try: number=float(str(value).replace(',','.'))
                except (TypeError,ValueError):continue
                if not math.isfinite(number) or abs(number)>100:raise ValueError('IPCA não plausível')
                found[period]={
                   'indicator_code':'IBGE_IPCA_1737_VAR63',
                   'indicator_name':'IPCA - variação mensal','unit':'%',
                   'period':period,'territory':'Brasil',
                   'population':'Índice geral de preços ao consumidor',
                   'value':number,'source_url':source_url,
                   'source_issuer':'IBGE/SIDRA',
                   'methodology':'Tabela IBGE 1737, variável 63. Variação mensal do IPCA. Não infere impacto de um político.'
                }
    if len(found)<2:raise ValueError('Série nacional IBGE indisponível')
    return [found[p] for p in sorted(found)]

def import_ibge_ipca(*,session=None)->dict:
    raw,sha=source_json(IBGE_IPCA_URL,session=session)
    rows=parse_ibge_ipca(raw)
    conn=connect()
    try:
        with conn:
            for r in rows:
                conn.execute("""INSERT INTO outcome_series
                (indicator_code,indicator_name,unit,period,territory,population,value,source_url,source_issuer,methodology)
                VALUES(:indicator_code,:indicator_name,:unit,:period,:territory,:population,:value,:source_url,:source_issuer,:methodology)
                ON CONFLICT(indicator_code,period,territory,population,source_url)
                DO UPDATE SET value=excluded.value,methodology=excluded.methodology,retrieved_at=datetime('now')""",r)
    finally: conn.close()
    return {'source':'IBGE/SIDRA IPCA','url':IBGE_IPCA_URL,'response_sha256':sha,
      'rows':len(rows),'first_period':rows[0]['period'],'last_period':rows[-1]['period'],
      'retrieved_at':datetime.now(timezone.utc).isoformat(),'sample':rows[-1],
      'scientific_limit':'Não atribui causalidade política nem benefício individual.'}
