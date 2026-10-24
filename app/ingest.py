"""Ferramenta de linha de comando para importar fontes públicas reais.

A importação não infere cumprimento de promessas ou causalidade.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse
import fitz
import requests
from .db import connect
from .core import theme_for

TSE_ZIPS={
 2022:'https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2022_BR.zip',
 2026:'https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2026_BR.zip',
}
# Identificação explícita pelo sequencial TSE. Arquivos são verificados no ZIP original.
# Os manifestos são revisáveis e a UI expõe o nome exato do arquivo original.
MANIFESTS={
 2022:{
  '2022BR280001607829':'Luiz Inácio Lula da Silva',
  '2022BR280001618036':'Jair Messias Bolsonaro',
 },
 2026:{
  '2026BR280002542548':'Luiz Inácio Lula da Silva',
  '2026BR280002540694':'Renan Santos',
  '2026BR280002541457':'Hertz Dias',
  '2026BR280002551975':'Edmilson Costa',
  '2026BR280002551544':'Flávio Bolsonaro',
  '2026BR280002552484':'Clariana Barão',
  '2026BR280002553884':'Pablo Marçal',
  '2026BR280002552487':'Rui Costa Pimenta',
  '2026BR280002539826':'Romeu Zema',
  '2026BR280002548139':'Wilson Grassi',
  '2026BR280002551932':'Ronaldo Caiado',
  '2026BR280002551547':'Augusto Cury',
  '2026BR280002538811':'Samara Martins',
 }
}
MAX_ZIP=60_000_000
MAX_PDF=20_000_000

def normalize_text(value:str)->str:
    value=value.replace('\x00',' ')
    value=re.sub(r'[ \t]+',' ',value)
    value=re.sub(r'\n{3,}','\n\n',value)
    return value.strip()

def split_chunks(page_text:str,max_chars:int=1000,overlap:int=110):
    # Não elimina texto: sobrepõe uma pequena janela para reduzir cortes de contexto.
    if not page_text.strip():return []
    chunks=[]
    cursor=0
    while cursor<len(page_text):
        end=min(cursor+max_chars,len(page_text))
        if end<len(page_text):
            candidate=page_text.rfind(' ',cursor+max_chars//2,end)
            if candidate>cursor: end=candidate+1
        body=page_text[cursor:end].strip()
        if body:chunks.append(body)
        if end>=len(page_text):break
        cursor=max(cursor+1,end-overlap)
    return chunks

def import_pdf(data:bytes,*,title:str,person:str,year:int|None,kind:str,issuer:str,source_url:str,source_notes:str='')->dict:
    if len(data)>MAX_PDF or not data.startswith(b'%PDF-'):
        raise ValueError('Arquivo deve ser PDF válido com até 20 MB')
    if not source_url.startswith('https://'):
        raise ValueError('source_url deve apontar para fonte HTTPS verificável')
    sha=hashlib.sha256(data).hexdigest()
    pdf=fitz.open(stream=data,filetype='pdf')
    if pdf.page_count>1000:raise ValueError('Número de páginas excede limite')
    conn=connect()
    try:
        old=conn.execute('SELECT id,title FROM documents WHERE sha256=?',(sha,)).fetchone()
        if old:return {'id':old['id'],'title':old['title'],'already_exists':True,'pages':pdf.page_count}
        with conn:
            cur=conn.execute('''INSERT INTO documents(title,person,election_year,doc_type,issuer,source_url,sha256,page_count,source_notes)
                VALUES(?,?,?,?,?,?,?,?,?)''',(title,person,year,kind,issuer,source_url,sha,pdf.page_count,source_notes))
            doc_id=cur.lastrowid
            count=0
            for i,page in enumerate(pdf):
                txt=normalize_text(page.get_text(sort=True))
                for j,chunk in enumerate(split_chunks(txt)):
                    conn.execute('INSERT INTO chunks(document_id,page,chunk_index,body,theme) VALUES(?,?,?,?,?)',
                        (doc_id,i+1,j,chunk,theme_for(chunk)))
                    count+=1
        return {'id':doc_id,'title':title,'pages':pdf.page_count,'chunks':count,'sha256':sha,'already_exists':False}
    finally:
        conn.close()
        pdf.close()

def download_tse(year:int):
    url=TSE_ZIPS[year]
    r=requests.get(url,timeout=(10,120),stream=True,headers={'User-Agent':'Civica-Evidencias/0.1 (pesquisa; fonte TSE)'})
    r.raise_for_status()
    length=int(r.headers.get('Content-Length') or 0)
    if length>MAX_ZIP:raise ValueError('ZIP TSE maior do que limite')
    buffer=io.BytesIO()
    for part in r.iter_content(chunk_size=131072):
        buffer.write(part)
        if buffer.tell()>MAX_ZIP:raise ValueError('ZIP TSE ultrapassou 60 MB')
    return buffer.getvalue(),url

def import_tse(year:int)->list[dict]:
    archive,url=download_tse(year)
    manifest=MANIFESTS[year]
    results=[]
    found=set()
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        members=z.infolist()
        if len(members)>2000: raise ValueError('ZIP com quantidade inesperada de arquivos')
        for member in members:
            name=Path(member.filename).name
            prefix=next((p for p in manifest if name.startswith(p)),None)
            if not prefix or not name.lower().endswith('.pdf'):continue
            if member.file_size>MAX_PDF:raise ValueError('PDF excede limite: '+name)
            # Leitura direta do membro em memória. Nenhum caminho do ZIP é extraído no disco.
            data=z.read(member)
            person=manifest[prefix]
            result=import_pdf(data,title=f'Plano de governo {year} | {person} | {name}',person=person,
                year=year,kind='plano_eleitoral',issuer='Tribunal Superior Eleitoral',source_url=url,
                source_notes=f'Arquivo interno: {member.filename}; arquivo ZIP oficial do TSE.')
            results.append(result)
            found.add(prefix)
    missing=sorted(set(manifest)-found)
    if missing: print('AVISO: identificadores não encontrados no ZIP:',', '.join(missing))
    return results

def import_camara(year:int,limit:int=60)->list[dict]:
    if not 1988<=year<=2100: raise ValueError('Ano fora da faixa prevista')
    if not 1<=limit<=100:raise ValueError('limit deve ser 1..100')
    base='https://dadosabertos.camara.leg.br/api/v2/proposicoes'
    resp=requests.get(base,params={'ano':year,'itens':limit,'pagina':1},timeout=35,
         headers={'Accept':'application/json','User-Agent':'Civica-Evidencias/0.1'})
    resp.raise_for_status()
    rows=resp.json().get('dados',[])
    conn=connect()
    output=[]
    try:
        for obj in rows:
            uri=obj.get('uri') or ''
            ementa=(obj.get('ementa') or '').strip()
            if not uri.startswith('https://dadosabertos.camara.leg.br/') or not ementa:continue
            ident=f"{obj.get('siglaTipo','')} {obj.get('numero','')}/{obj.get('ano','')}"
            sha=hashlib.sha256(('camara:'+str(obj.get('id'))).encode()).hexdigest()
            with conn:
                old=conn.execute('SELECT id FROM documents WHERE sha256=?',(sha,)).fetchone()
                if old:continue
                cursor=conn.execute('''INSERT INTO documents(title,person,election_year,doc_type,issuer,source_url,sha256,page_count,source_notes)
                    VALUES(?,?,?,?,?,?,?,?,?)''',('Câmara | '+ident,'',None,'proposicao_legislativa',
                    'Câmara dos Deputados',uri,sha,1,'Ementa via API oficial; NÃO equivale a lei aprovada.'))
                docid=cursor.lastrowid
                conn.execute('INSERT INTO chunks(document_id,page,chunk_index,body,theme) VALUES(?,?,?,?,?)',
                             (docid,1,0,ementa,theme_for(ementa)))
                output.append({'id':docid,'title':'Câmara | '+ident})
        return output
    finally:conn.close()

def import_indicators(path:Path):
    """CSV UTF-8 com código, nome, unidade, período, território, população, valor, URL oficial, órgão e metodologia.
       NÃO relaciona indicadores automaticamente a pessoas ou propostas."""
    import csv
    required={'indicator_code','indicator_name','unit','period','territory','population','value','source_url','source_issuer','methodology'}
    conn=connect()
    count=0
    try:
        with path.open('r',encoding='utf-8-sig',newline='') as file:
            reader=csv.DictReader(file)
            if not required.issubset(set(reader.fieldnames or [])):
                raise ValueError('Faltam colunas: '+', '.join(sorted(required-set(reader.fieldnames or []))))
            with conn:
                for row in reader:
                    if not row['source_url'].startswith('https://'):
                        raise ValueError('Indicadores devem preservar a URL da fonte HTTPS')
                    conn.execute('''INSERT OR IGNORE INTO outcome_series
                    (indicator_code,indicator_name,unit,period,territory,population,value,source_url,source_issuer,methodology)
                    VALUES (?,?,?,?,?,?,?,?,?,?)''', tuple(
                        row[col] if col!='value' else float(row[col])
                        for col in ['indicator_code','indicator_name','unit','period','territory','population','value','source_url','source_issuer','methodology']))
                    count+=1
        return count
    finally:conn.close()

def main():
    parser=argparse.ArgumentParser(description='Importe dados públicos com rastreabilidade')
    sub=parser.add_subparsers(dest='command',required=True)
    tse=sub.add_parser('tse',help='Baixa ZIP oficial TSE e importa planos mapeados')
    tse.add_argument('--year',type=int,choices=(2022,2026),required=True)
    pdf=sub.add_parser('pdf',help='Importa PDF local com fonte identificada')
    pdf.add_argument('--file',type=Path,required=True)
    for name in ('title','issuer','source-url'):
        pdf.add_argument('--'+name,required=True)
    pdf.add_argument('--person',default='')
    pdf.add_argument('--year',type=int)
    pdf.add_argument('--type',default='documento_publico')
    cam=sub.add_parser('camara',help='Importa ementas de proposições via API oficial')
    cam.add_argument('--year',type=int,required=True)
    cam.add_argument('--limit',type=int,default=60)
    indic=sub.add_parser('indicators',help='Importa indicadores CSV com proveniência')
    indic.add_argument('--file',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='tse': data=import_tse(args.year)
    elif args.command=='camara':data=import_camara(args.year,args.limit)
    elif args.command=='indicators':data={'imported_rows':import_indicators(args.file)}
    else:
        data=import_pdf(args.file.read_bytes(),title=args.title,person=args.person,
             year=args.year,kind=args.type,issuer=args.issuer,source_url=args.source_url)
    print(json.dumps(data,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
