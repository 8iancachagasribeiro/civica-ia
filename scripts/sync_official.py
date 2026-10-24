"""Sincronização direta de fontes oficiais com reporte explícito de falhas."""
from __future__ import annotations
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path
from app.ingest import import_tse,MANIFESTS
from app.tse_registry import fetch_presidents,verify_manifest
from app.execution_sources import PEOPLE,sync_person
from app.sidra_source import import_sidra
from app.public_sources import import_ibge_ipca
from app.bcb_source import import_bcb_ipca,import_bcb_context
from app.traceability import trace_overview
from app.db import connect

REGISTRY_FILE=Path('data/sources/tse_presidente_2026.json')

def sync_registry():
    """Cadastro oficial de candidaturas; confere o manifesto de planos antes de usá-lo."""
    registry=fetch_presidents(2026)
    problems=verify_manifest(MANIFESTS[2026],2026,registry['candidates'])
    registry['manifest_problems']=problems
    REGISTRY_FILE.parent.mkdir(parents=True,exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(registry,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
    if problems:raise ValueError('Manifesto diverge do cadastro TSE: '+'; '.join(problems))
    return {'candidates':len(registry['candidates']),
            'in_runoff':[c['name'] for c in registry['candidates'] if c['in_runoff']],'zip_sha256':registry['zip_sha256']}

def sync(include_tse=True,include_camara=True,include_ibge=True,require_source=True):
    report={'schema_version':'0.3','started_at':datetime.now(timezone.utc).isoformat(),
     'official_sources':{},'note':('Fontes originais. Temas correlatos não significam execução, '
      'causalidade ou benefício individual. Sem ranquear ou recomendar políticos.')}
    tasks=[]
    if include_tse:
        tasks.append(('tse_cadastro_presidente_2026',sync_registry))
        tasks.append(('tse_planos_2022',lambda:import_tse(2022)))
        tasks.append(('tse_planos_2026',lambda:import_tse(2026)))
    if include_camara:
        for sq,person in PEOPLE.items():
            tasks.append(('registro_legislativo_'+person['scope']+'_'+sq,lambda sq=sq:sync_person(sq)))
    if include_ibge:
        tasks.append(('ibge_ipca',import_ibge_ipca))
        tasks.append(('bcb_ipca_433',import_bcb_ipca))
        tasks.append(('bcb_desocupacao_24369',lambda:import_bcb_context(24369)))
        tasks.append(('bcb_pib_nominal_4380',lambda:import_bcb_context(4380)))
        tasks.append(('ibge_sidra_pnadc_ipca_grupos',import_sidra))
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
