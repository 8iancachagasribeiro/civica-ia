"""Cruzamentos documentais factuais por assunto; não atribuem impactos a governantes."""
from __future__ import annotations
from .db import connect
from .core import TOPICS,theme_for

def factual_cross(topic:str,year:int|None=None,territory:str='Brasil',limit:int=6)->dict:
    if topic not in TOPICS:raise ValueError('Tema inválido')
    if year is not None and not 1990<=year<=2100:raise ValueError('Ano inválido')
    if not 1<=limit<=20:raise ValueError('Limite inválido')
    conn=connect()
    try:
        plans=conn.execute("""SELECT d.id,d.title,d.person,d.election_year,d.source_url,d.sha256,
               c.page,substr(c.body,1,600) AS excerpt
               FROM documents d JOIN chunks c ON c.document_id=d.id
               WHERE d.doc_type='plano_eleitoral' AND c.theme=?
               AND c.id=(SELECT min(c2.id) FROM chunks c2 WHERE c2.document_id=d.id AND c2.theme=?)
               ORDER BY d.election_year,d.id LIMIT ?""",(topic,topic,limit)).fetchall()
        acts=conn.execute("""SELECT d.id,d.title,d.source_url,d.sha256,c.page,
               substr(c.body,1,600) AS excerpt
               FROM documents d JOIN chunks c ON c.document_id=d.id
               WHERE d.doc_type='proposicao_legislativa' AND c.theme=?
               AND c.id=(SELECT min(c2.id) FROM chunks c2 WHERE c2.document_id=d.id AND c2.theme=?)
               ORDER BY d.title,d.id LIMIT ?""",(topic,topic,limit)).fetchall()
        rows=conn.execute("""SELECT indicator_code,indicator_name,unit,period,territory,
               population,value,source_url,source_issuer,methodology,retrieved_at
               FROM outcome_series WHERE territory=? ORDER BY period DESC LIMIT 2000""",(territory,)).fetchall()
    finally:conn.close()
    relevant=[]
    for r in rows:
        if theme_for(r['indicator_name']) != topic:continue
        if year is not None and not str(r['period']).startswith(str(year)):continue
        relevant.append(dict(r))
        if len(relevant)>=limit:break
    return {'theme':topic,'reference_year':year,'territory':territory,
       'electoral_plans':[dict(x) for x in plans],
       'legislative_proposals':[dict(x) for x in acts],
       'observed_indicators':relevant,
       'relation':'Recuperação conjunta por assunto. Nenhum vínculo causal ou pessoal estabelecido.',
       'warnings':['Uma proposta da Câmara não equivale a lei aprovada.',
       'Período de indicador não identifica a causa de mudanças.',
       'Indicadores agregados não demonstram benefício individual.',
       'Acervo parcial: ausência de evidência não equivale a ausência de ação.']}
