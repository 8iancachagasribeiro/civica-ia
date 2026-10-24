"""IPCA: Série 433 do Banco Central do Brasil, originada no IBGE."""
from __future__ import annotations
import hashlib
import math
from datetime import datetime, timezone
import requests
from .db import connect

BCB_IPCA_URL='https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial=01%2F01%2F2019&dataFinal=31%2F12%2F2026'

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

# Séries oficiais adicionais para contexto econômico; variáveis com definições distintas.
CONTEXT_SERIES = {
    24369: {
        "indicator_code": "BCB_SGS_24369_PNADC_DESOCUPACAO",
        "indicator_name": "Taxa de desocupação - PNAD Contínua",
        "unit": "%",
        "population": "Pessoas na força de trabalho de 14 anos ou mais",
        "source_issuer": "IBGE/PNAD Contínua (via BCB/SGS)",
        "methodology": "Taxa no trimestre móvel da PNAD Contínua publicada no SGS 24369; não é taxa mensal independente nem efeito causal de governo.",
        "minimum": 0,
        "maximum": 100,
    },
    4380: {
        "indicator_code": "BCB_SGS_4380_PIB_NOMINAL",
        "indicator_name": "PIB mensal nominal estimado pelo Banco Central",
        "unit": "R$ milhões",
        "population": "Atividade econômica nacional; valores correntes",
        "source_issuer": "Banco Central do Brasil/SGS",
        "methodology": "Estimativa mensal nominal do BCB, SGS 4380; não mede crescimento real nem impacto causal de governo.",
        "minimum": 0,
        "maximum": 1_000_000_000,
    },
}

def parse_bcb_context(data: object, code: int, source_url: str) -> list[dict]:
    """Validate SGS date/value records against a known series, without inferring attribution."""
    if code not in CONTEXT_SERIES or not isinstance(data, list):
        raise ValueError("Série SGS não autorizada ou formato inválido")
    meta = CONTEXT_SERIES[code]
    found = {}
    for entry in data:
        if not isinstance(entry, dict):
            raise ValueError("Item SGS inválido")
        try:
            date = datetime.strptime(entry["data"], "%d/%m/%Y")
            value = float(str(entry["valor"]).replace(",", "."))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Medição SGS inválida") from error
        if not math.isfinite(value) or not (meta["minimum"] <= value <= meta["maximum"]):
            raise ValueError("Valor fora do intervalo validado")
        found[date.strftime("%Y%m")] = {
            "indicator_code": meta["indicator_code"],
            "indicator_name": meta["indicator_name"],
            "unit": meta["unit"],
            "period": date.strftime("%Y%m"),
            "territory": "Brasil",
            "population": meta["population"],
            "value": value,
            "source_url": source_url,
            "source_issuer": meta["source_issuer"],
            "methodology": meta["methodology"],
        }
    if len(found) < 2:
        raise ValueError("Série SGS com menos de dois períodos")
    return [found[period] for period in sorted(found)]

def import_bcb_context(code: int, *, session=None) -> dict:
    if code not in CONTEXT_SERIES:
        raise ValueError("Código SGS não autorizado")
    year = datetime.now(timezone.utc).year
    source_url = (
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
        f"?formato=json&dataInicial=01%2F01%2F2019&dataFinal=31%2F12%2F{year}"
    )
    client = session if session is not None else requests
    response = client.get(source_url, timeout=(10, 60),
                          headers={"Accept": "application/json", "User-Agent": "Civica-IA/0.4"})
    response.raise_for_status()
    if len(response.content) > 1_000_000:
        raise ValueError("Resposta SGS inesperadamente grande")
    rows = parse_bcb_context(response.json(), code, source_url)
    conn = connect()
    try:
        with conn:
            for row in rows:
                conn.execute("""INSERT INTO outcome_series
                    (indicator_code,indicator_name,unit,period,territory,population,value,source_url,source_issuer,methodology)
                    VALUES(:indicator_code,:indicator_name,:unit,:period,:territory,:population,:value,:source_url,:source_issuer,:methodology)
                    ON CONFLICT(indicator_code,period,territory,population,source_url)
                    DO UPDATE SET value=excluded.value,methodology=excluded.methodology,retrieved_at=datetime('now')""", row)
    finally:
        conn.close()
    return {
        "source": CONTEXT_SERIES[code]["indicator_name"], "url": source_url,
        "response_sha256": hashlib.sha256(response.content).hexdigest(),
        "rows": len(rows), "first_period": rows[0]["period"], "last_period": rows[-1]["period"],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "scientific_limit": "Séries de natureza e unidades distintas não demonstram convergência causal."
    }
