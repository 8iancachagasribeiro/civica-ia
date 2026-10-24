"""Sincronização direta de fontes oficiais com reporte explícito de falhas."""
from __future__ import annotations
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path
from app.ingest import import_tse,import_camara
from app.public_sources import import_ibge_ipca
from app.traceability import trace_overview
from app.db import connect

def sync(include_tse=True,include_camara=True,include_ibge=True,require_source=True):
    report={'schema_version':'0.3','started_at':datetime.now(timezone.utc).isoformat(),
     'official_sources':{},'note':('Fontes originais. Temas correlatos não significam execução, '
      'causalidade ou benefício individual. Sem ranquear ou recomendar políticos.')}
    tasks=[]
    if include_tse:tasks.append(('tse_planos_2022',lambda:import_tse(2022)))
    if include_camara:tasks.append(('camara_proposicoes_2024',lambda:import_camara(2024,25)))
    if include_ibge:tasks.append(('ibge_ipca',import_ibge_ipca))
    for name,fn in tasks:
        try:
            out=fn()
            if isinstance(out,list):
                if not out:raise ValueError('Nenhum registro oficial importado')
                out={'rows':len(out),'example_titles':[r.get('title') for r in out[:2]]}
            report['official_sources'][name]={'status':'ok','result':out}
        except Exception as e:
            report['official_sources'][name]={'status':'error','error_type':type(e).__name__,'message':str(e)[:250]}
    conn=connect()
    try:
        report['db_counts']={t:int(conn.execute('SELECT count(*) FROM '+t).fetchone()[0])
          for t in ('documents','chunks','outcome_series','commitments')}
    finally:conn.close()
    report['trace_counts']=trace_overview()
    report['finished_at']=datetime.now(timezone.utc).isoformat()
    report['sources_successful']=sum(x['status']=='ok' for x in report['official_sources'].values())
    report['sources_attempted']=len(tasks)
    if require_source and not report['sources_successful']:
        raise RuntimeError('Nenhuma fonte oficial validada: '+json.dumps(report['official_sources'],ensure_ascii=False))
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--without-tse',action='store_true')
    p.add_argument('--without-camara',action='store_true')
    p.add_argument('--without-ibge',action='store_true')
    p.add_argument('--out',type=Path,default=Path('data/official_snapshot.json'))
    args=p.parse_args()
    result=sync(not args.without_tse,not args.without_camara,not args.without_ibge)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'sources':result['official_sources'],'counts':result['db_counts']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
