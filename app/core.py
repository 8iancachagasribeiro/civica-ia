"""Recuperação lexical verificável e regras públicas de apresentação."""
from __future__ import annotations
import re
import unicodedata
from collections import defaultdict
from .db import connect

TOPICS = {
 "economia": ("econom", "renda", "emprego", "salário", "salario", "inflação", "inflacao", "tribut", "pobreza"),
 "saúde": ("saúde", "saude", "sus", "hospital", "vacina", "medicament", "mortalidade"),
 "educação": ("educ", "escola", "professor", "universidade", "alfabet", "ensino"),
 "segurança": ("seguran", "polícia", "policia", "violência", "violencia", "homicid", "feminic"),
 "justiça": ("justiça", "justica", "judici", "direitos", "tribunal", "pris"),
 "habitação": ("moradia", "habita", "aluguel", "saneamento"),
 "ambiente": ("ambien", "floresta", "clima", "desmat", "energia"),
}
STOP = {"a","o","as","os","de","da","do","das","dos","e","em","um","uma","qual","quais","que","para","por","com","na","no","nos","nas","foi","foram","ser","são","sao","mais","sobre","se","tem","entre","governo","plano","proposta","propostas"}

def norm(s:str)->str:
    return ''.join(c for c in unicodedata.normalize('NFKD',s.lower()) if not unicodedata.combining(c))

def theme_for(text:str)->str:
    t = norm(text)
    for label, stems in TOPICS.items():
        if any(norm(stem) in t for stem in stems): return label
    return "geral"

# Não produz voto recomendado, ranking de candidatos ou favorecimento eleitoral.
ELECTORAL_VERDICT = re.compile(
    r"\b(mais\s+(?:vantajos[oa]|ben[eé]fic[oa]|indicado)|melhor(?:es)?|pior(?:es)?|recomend[ae]|"
    r"ranque(?:ie|ar|amento)|ranking|pontua(?:ç[aã]o|r)|nota|score|"
    r"em\s+quem\s+votar|devo\s+votar|vot[ae]\s+em\s+quem|"
    r"qual\s+(?:dos?\s+\w+\s+)?candidat[oa]\s+(?:devo|merece)|"
    r"quem\s+(?:beneficia|favorece)\s+mais)\b",
    re.IGNORECASE,
)
ELECTION_CONTEXT = re.compile(r"\b(candidat|pol[ií]tic|partid|vot|elei[cç]|president|lula|bolsonaro|governante)\w*\b",re.IGNORECASE)

def is_voting_recommendation(question: str) -> bool:
    return bool(ELECTORAL_VERDICT.search(question) and ELECTION_CONTEXT.search(question))

def find_evidence(question:str, limit:int=8)->list[dict]:
    words=[]
    for token in re.findall(r"\w+", norm(question)):
        if len(token)>=3 and token not in STOP and token not in words:
            words.append(token)
    if not words: return []
    # FTS5 usa palavras literais devidamente escapadas; nenhum operador do usuário é executado.
    expression=' OR '.join('"'+t.replace('"','')+'"' for t in words[:12])
    conn=connect()
    try:
        rows=conn.execute("""
            SELECT chunks.id AS chunk_id, chunks.body, chunks.page, chunks.theme,
                   documents.id AS document_id, documents.title, documents.person,
                   documents.issuer, documents.doc_type, documents.election_year,
                   documents.source_url, documents.sha256, bm25(chunk_search) AS relevance
            FROM chunk_search JOIN chunks ON chunks.id=chunk_search.rowid
                 JOIN documents ON documents.id=chunks.document_id
            WHERE chunk_search MATCH ?
            ORDER BY relevance ASC LIMIT 70
        """,(expression,)).fetchall()
    finally: conn.close()
    # Diversidade de documentos com limite simétrico por fonte; não ranqueia políticos.
    grouped=defaultdict(list)
    for row in rows: grouped[row['document_id']].append(dict(row))
    result=[]
    for layer in range(3):
        for document_id in sorted(grouped):
            if len(grouped[document_id])>layer:
                result.append(grouped[document_id][layer])
            if len(result)>=limit: return result
    return result

def extractive_answer(evidence:list[dict], blocked:bool=False)->str:
    if blocked:
        return ("Não classifico nem recomendo candidaturas. Posso localizar compromissos registrados, "
                "ações documentadas e indicadores públicos, informando fontes e limites da evidência. "
                "Veja os documentos recuperados abaixo ou faça uma pergunta factual específica.")
    if not evidence:
        return ("Não encontrei evidências no acervo local para esta consulta. "
                "Importe documentos oficiais primeiro ou reformule a busca. "
                "Ausência de resultado na base não significa ausência do fato na realidade.")
    return (f"Localizei {len(evidence)} trechos documentais relacionados à consulta. "
            "Os excertos abaixo vêm das fontes cadastradas; não comprovam execução "
            "de propostas, impactos causais nem veracidade independente das alegações presentes nos planos.")


def find_indicators(question:str, limit:int=8)->list[dict]:
    """Localiza séries por tema, sem associá-las automaticamente a uma candidatura."""
    tokens=[t for t in re.findall(r"\w+",norm(question)) if len(t)>=4 and t not in STOP]
    if not tokens:return []
    conn=connect()
    try:
        # A base numérica é alimentada por CSV auditável com fonte, época e população.
        rows=conn.execute("""SELECT indicator_code, indicator_name, unit, period, territory,
            population, value, source_url, source_issuer, methodology
            FROM outcome_series ORDER BY period DESC LIMIT 1500""").fetchall()
    finally:conn.close()
    matches=[]
    for row in rows:
        haystack=norm(row['indicator_code']+' '+row['indicator_name']+' '+row['territory']+' '+row['population'])
        if any(t in haystack for t in tokens):
            matches.append(dict(row))
            if len(matches)>=limit:break
    return matches
