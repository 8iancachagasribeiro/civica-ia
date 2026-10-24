from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from .db import connect
from .core import find_evidence, find_indicators, is_voting_recommendation
from .llm import make_answer
from .traceability import get_trace, trace_overview

app=FastAPI(title='Cívica | IA de Evidências Públicas',version='0.1.0',
            description='Consulta auditável de documentos públicos, sem recomendação eleitoral.')
ROOT=Path(__file__).parent

class AskRequest(BaseModel):
    question:str=Field(min_length=3,max_length=800)

@app.get('/')
def index(): return FileResponse(ROOT/'static'/'index.html')

@app.get('/health')
def health(): return {'status':'ok'}

@app.get('/api/documents')
def documents():
    conn=connect()
    try:
        docs=conn.execute('SELECT id,title,person,doc_type,election_year,issuer,source_url,sha256,page_count,collected_at FROM documents ORDER BY election_year DESC, title').fetchall()
        return {'documents':[dict(d) for d in docs]}
    finally: conn.close()

@app.post('/api/ask')
def ask(req:AskRequest):
    blocked=is_voting_recommendation(req.question)
    evidence=find_evidence(req.question,8)
    indicators=find_indicators(req.question,8)
    answer=make_answer(req.question,evidence,blocked)
    clean=[{k:v for k,v in r.items() if k!='relevance'} for r in evidence]
    return {'answer':answer, 'sources':clean, 'indicators':indicators, 'recommendation_blocked':blocked,
            'notice':'Promessas ≠ implementação. Correlação ≠ causalidade. Acervo pode estar incompleto.'}

 
@app.get('/api/evidence-trace/overview')
def evidence_trace_overview():
    return trace_overview()

@app.get('/api/evidence-trace/{commitment_id}')
def evidence_trace(commitment_id: int):
    from fastapi import HTTPException
    if commitment_id < 1:
        raise HTTPException(status_code=404, detail='Registro não encontrado.')
    result = get_trace(commitment_id)
    if result is None:
        raise HTTPException(status_code=404, detail='Registro não encontrado.')
    return result
