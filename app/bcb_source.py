"""IPCA: Série 433 do Banco Central do Brasil, originada no IBGE."""
from __future__ import annotations
import hashlib
import math
from datetime import datetime, timezone
import requests
from .db import connect

BCB_IPCA_URL='https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/96?formato=json'

def parse_bcb_ipca(data:object,source_url:str=BCB_IPCA_URL)->list[dict]:
    if not isinstance(data,list):raise ValueError('Formato SGS inválido')
    found={}
    for entry in data:
        if not isinstance(entry,dict):raise ValueError('Item SGS inválido')
        try:
            date=datetime.strptime(entry['data'],'%d/%m/%Y')
            number=float(str(entry['valor']).replace(',','.'))
        except (KeyError,TypeError,ValueError) as e:
            raise ValueError('Medição SGS inválida') from e
        if not math.isfinite(number) or abs(number)>100:raise ValueError('IPCA incompatível')
        period=date.strftime('%Y%m')
        found[period]={
          'indicator_code':'BCB_SGS_433_IPCA','indicator_name':'Inflação (IPCA) - variação mensal',
          'unit':'%','period':period,'territory':'Brasil',
          'population':'Índice nacional de preços ao consumidor amplo',
          'value':number,'source_url':source_url,
          'source_issuer':'Banco Central do Brasil/SGS (fonte IBGE)',
          'methodology':'Série SGS 433; IPCA do IBGE publicado pelo BCB. Variação mensal não é efeito causal de governo.'}
    if len(found)<2:raise ValueError('Poucos meses na série SGS')
    return [found[x] for x in sorted(found)]

def import_bcb_ipca(*,session=None)->dict:
    client=session if session is not None else requests
    response=client.get(BCB_IPCA_URL,timeout=(10,60),
            headers={'Accept':'application/json','User-Agent':'Civica-IA/0.3'})
    response.raise_for_status()
    if len(response.content)>1_000_000:raise ValueError('Série SGS inesperadamente grande')
    rows=parse_bcb_ipca(response.json())
    conn=connect()
    try:
        with conn:
            for row in rows:
                conn.execute("""INSERT INTO outcome_series
                 (indicator_code,indicator_name,unit,period,territory,population,value,source_url,source_issuer,methodology)
                 VALUES(:indicator_code,:indicator_name,:unit,:period,:territory,:population,:value,:source_url,:source_issuer,:methodology)
                 ON CONFLICT(indicator_code,period,territory,population,source_url)
                 DO UPDATE SET value=excluded.value,retrieved_at=datetime('now')""",row)
    finally:conn.close()
    return {'source':'Banco Central SGS série 433 (IPCA; fonte IBGE)',
        'url':BCB_IPCA_URL,'response_sha256':hashlib.sha256(response.content).hexdigest(),
        'rows':len(rows),'first_period':rows[0]['period'],'last_period':rows[-1]['period'],
        'retrieved_at':datetime.now(timezone.utc).isoformat(),
        'sample':rows[-1],
        'scientific_limit':'Inflação observada não mede benefício individual nem estabelece causalidade governamental.'}
