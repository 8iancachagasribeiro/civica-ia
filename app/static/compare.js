"use strict";
/* Cruzamento por tema × candidatura: pretende / diz que fez / registro oficial / impacto possível.
   Descritivo e simétrico: mesma estrutura para toda candidatura, ordem pelo número na urna,
   sem pontuação, sem destaque de "melhor" e sem inferência de causalidade. */
(function(){
const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=String(text);return n};
const norm=(v)=>String(v||"").normalize("NFD").replace(/[̀-ͯ]/g,"").toLowerCase();
const fmt=(n,d=0)=>Number(n).toLocaleString("pt-BR",{maximumFractionDigits:d,minimumFractionDigits:d});
const link=(url,label)=>{
  const a=el("a","source-link",label||"Consultar fonte ↗");
  try{const u=new URL(url);if(u.protocol==="https:"){a.href=url;a.target="_blank";a.rel="noopener noreferrer";return a}}catch{}
  a.textContent="Origem não verificada";return a;
};
const GAP_SOURCES={
  saude:"mortalidade e internações (SIM e SIH/DATASUS), cobertura da atenção básica (CNES/e-Gestor)",
  educacao:"aprendizagem e fluxo escolar (INEP: Saeb, Ideb, Censo Escolar)",
  seguranca:"homicídios e crimes registrados (Sinesp, SIM/DATASUS, Anuário do Fórum Brasileiro de Segurança Pública)",
  justica:"tempo e estoque de processos (CNJ, Justiça em Números)",
  ambiente:"desmatamento e queimadas (INPE: PRODES, DETER), emissões (SEEG)",
  habitacao:"déficit habitacional e saneamento (PNAD Contínua, SNIS), entregas de unidades (Ministério das Cidades)",
  mulheres:"violência contra mulheres (Sinesp, SIM/DATASUS, Anuário do FBSP)",
  economia:"execução fiscal e contas nacionais (Tesouro Nacional, IBGE Contas Nacionais)"
};
const TYPE_LABEL={contrafactual:"Contrafactual",quase_experimental:"Quase-experimental",painel_ajustado:"Painel ajustado: associação, não experimento",tendencia:"Tendência antes/depois, não causal"};
const MARKERS={n:"número ou meta",p:"prazo",r:"fonte de recursos"};

function periodParts(p){
  let m=String(p).match(/^(\d{4})T([1-4])$/);if(m)return{year:+m[1],slot:+m[2],kind:"q"};
  m=String(p).match(/^(\d{4})(\d{2})$/);if(m&&+m[2]>=1&&+m[2]<=12)return{year:+m[1],slot:+m[2],kind:"m"};
  return null;
}
function fmtPeriod(p){
  const parts=periodParts(p);
  if(!parts)return String(p);
  return parts.kind==="q"?parts.slot+"º tri/"+parts.year:String(parts.slot).padStart(2,"0")+"/"+parts.year;
}
const periodKey=(p)=>{const x=periodParts(p);return x?x.year*100+x.slot:NaN};
const sameSlot=(kind,year,slot)=>kind==="q"?year+"T"+slot:year+String(slot).padStart(2,"0");

function byId(data){
  if(!data._byId)data._byId=new Map(data.excerpts.map(row=>[row.id,row]));
  return data._byId;
}
function snippet(body,at){
  const flat=String(body).replace(/\s+/g," ");
  const cut=String(body).slice(0,at).replace(/\s+/g," ").length;
  let from=Math.max(0,cut-90),to=Math.min(flat.length,cut+300);
  if(from>0){const sp=flat.indexOf(" ",from);if(sp>-1&&sp<cut)from=sp+1}
  if(to<flat.length){const sp=flat.lastIndexOf(" ",to);if(sp>cut)to=sp}
  return(from?"… ":"")+flat.slice(from,to).trim()+(to<flat.length?" …":"");
}
function passage(data,cand,pair,kindLabel){
  const row=byId(data).get(pair[0]);
  const box=el("blockquote","passage");
  if(!row){box.append(el("p","","Trecho indisponível."));return box}
  box.append(el("p","",snippet(row.body,pair[1])));
  const foot=el("div","passage-foot");
  foot.append(el("span","meta","Página "+row.page+(kindLabel?" · "+kindLabel:"")),link(row.source_url,"Plano oficial no TSE ↗"));
  box.append(foot);
  return box;
}
function block(kind,title,subtitle){
  const b=el("section","layer layer-"+kind);
  const h=el("div","layer-head");
  h.append(el("h4","",title));
  if(subtitle)h.append(el("span","layer-sub",subtitle));
  b.append(h);
  return b;
}
const note=(text)=>el("p","layer-note",text);

function pretende(data,cand,theme){
  const b=block("plan","Pretende","Plano de governo 2026");
  const plans=data.comparison.plans[cand.sq];
  if(!cand.plan_document_id||!plans){b.append(note("Plano não importado para esta candidatura."));return b}
  const s=plans[theme],total=plans._chunks||0;
  if(!s||!s.passages){
    b.append(note("Nenhuma passagem do plano casa com os termos deste tema. É leitura lexical: o tema pode ser tratado com outras palavras."));
    return b;
  }
  b.append(note(s.passages+" passagens sobre o tema"+(total?" ("+fmt(100*s.passages/total,1)+"% do plano de "+cand.plan_pages+" páginas)":"")+
    ". Destas, "+s.commitments+" têm linguagem de compromisso."));
  if(s.commitments){
    b.append(note("Entre os compromissos: "+s.with_number+" citam número ou meta, "+s.with_deadline+" citam prazo, "+
      s.with_funding+" citam fonte de recursos. Detecção lexical: descreve o texto, não avalia a proposta."));
    for(const pair of s.top_commitments)b.append(passage(data,cand,pair));
  }
  return b;
}
function disseFez(data,cand,theme){
  const b=block("claim","Diz que fez","Alegação do próprio plano");
  const s=(data.comparison.plans[cand.sq]||{})[theme];
  if(!cand.plan_document_id){b.append(note("Plano não importado."));return b}
  if(!s||!s.passages){b.append(note("Sem passagens sobre o tema."));return b}
  const g=s.cites_gov||{},who=[];
  if(g.bolsonaro)who.push("governo Bolsonaro (2019–2022) em "+g.bolsonaro);
  if(g.lula)who.push("governo Lula (a partir de 2023) em "+g.lula);
  if(who.length)b.append(note("Passagens do tema que citam governos: "+who.join("; ")+". Um plano pode reivindicar feitos de governos que a candidatura não exerceu, ou criticar governos anteriores."));
  if(!s.claims){b.append(note("O plano não traz balanço de realizações neste tema (detecção lexical)."));return b}
  b.append(note(s.claims+" passagem(ns) com linguagem de balanço. Não verificadas: são afirmações do próprio plano."));
  for(const pair of s.top_claims)b.append(passage(data,cand,pair,"alegação"));
  return b;
}
function registro(data,cand,theme){
  const b=block("record","Registro oficial","Câmara e Senado");
  const ex=data.comparison.execution[cand.sq];
  if(!ex||!cand.record){
    b.append(note("Registro de mandatos e proposições não coletado para esta candidatura. Isso não significa ausência de atuação pública."));
    return b;
  }
  b.append(note(cand.record.office+". "+cand.record.scope_note));
  const t=ex.summary.by_theme[theme]||{total:0};
  if(!t.total){b.append(note("Nenhuma proposição classificada neste tema no recorte coletado (de "+fmt(ex.summary.total)+" no total)."));return b}
  const L=data.comparison.stage_labels;
  const ORDER=["lei","aprovada","tramitando","encerrada","perdeu_eficacia"];
  const parts=ORDER.filter(k=>t[k]).map(k=>t[k]+" "+L[k].toLowerCase());
  b.append(el("p","layer-count",t.total+" proposições no tema (de "+fmt(ex.summary.total)+" coletadas): "+parts.join(" · ")+"."));
  if(cand.record.scope==="senado")b.append(note(t.principal+" como primeiro signatário e "+(t.total-t.principal)+" como coautor. Emendas à Constituição exigem muitas assinaturas, então coautoria é comum."));
  if(t.credito)b.append(note(t.credito+" delas abrem crédito orçamentário (ex.: crédito extraordinário): autorizam gasto, não instituem política nova."));
  if(t.perdeu_eficacia)b.append(note("Medida provisória que perde a eficácia não foi convertida em lei, mas pode ter produzido efeitos nos 120 dias de vigência, como gasto já realizado. Não é, por si, fracasso."));
  const rank=Object.fromEntries(ORDER.map((k,i)=>[k,i]));
  const rows=ex.records.filter(r=>r.t.includes(theme))
    .sort((x,y)=>rank[x.st]-rank[y.st]||(x.n==="credito")-(y.n==="credito")||y.d.localeCompare(x.d)).slice(0,5);
  const list=el("ul","record-mini");
  for(const r of rows){
    const li=el("li","");
    const head=el("div","mini-head");
    head.append(el("span","stage stage-"+r.st,L[r.st]),el("strong","",r.id),el("span","meta",r.d.slice(0,4)+(r.n==="credito"?" · crédito":"")));
    li.append(head,el("p","",r.e.length>210?r.e.slice(0,207)+"…":r.e),link(r.u,r.b+" ↗"));
    list.append(li);
  }
  b.append(list);
  if(t.total>rows.length)b.append(note("Mostrando "+rows.length+" de "+t.total+", priorizando as que viraram norma. Proposta apresentada não é lei; lei sancionada não é resultado."));
  return b;
}

function studyCard(study,citedBy){
  const c=el("article","study");
  const h=el("div","study-head");
  h.append(el("span","label-pill",TYPE_LABEL[study.type]||study.type));
  if(citedBy&&citedBy.length)h.append(el("span","cited","Política semelhante à citada no plano de "+citedBy.join(" e ")));
  c.append(h,el("h5","",study.policy));
  const rows=[["Desfecho",study.outcome],["Estimativa",study.estimate],["Período e população",study.period+" · "+study.population],
    ["Método",study.method],["Limites",study.limits]];
  const dl=el("dl","study-fields");
  for(const[k,v]of rows){dl.append(el("dt","",k),el("dd","",v))}
  c.append(dl,link(study.source_url,study.source_title+" ↗"));
  return c;
}
function impacto(data,studies,theme,pair){
  const b=block("impact","Impacto possível","Avaliações de políticas, não dos candidatos");
  b.append(note("Estudos estimam efeitos de políticas passadas, em contextos e períodos específicos. Não medem o que uma candidatura fará nem o que fez."));
  const label=(data.themes.find(t=>t.key===theme)||{}).label;
  const mine=studies.filter(s=>s.themes.some(x=>norm(x)===norm(label)));
  const cited=new Map();
  for(const cand of pair){
    const plan=((data.comparison.plans[cand.sq]||{})[theme])||{};
    for(const link of (plan.studies||[])){
      if(!cited.has(link.study))cited.set(link.study,[]);
      cited.get(link.study).push(cand.display_name||cand.ballot_name);
    }
  }
  const linked=mine.filter(s=>cited.has(s.id)),others=mine.filter(s=>!cited.has(s.id));
  if(linked.length){
    b.append(el("h5","sub","Políticas mencionadas nos planos comparados"));
    for(const s of linked)b.append(studyCard(s,cited.get(s.id)));
  }
  if(others.length){
    const d=el("details","more");
    d.append(el("summary","",(linked.length?"Outras avaliações":"Avaliações")+" sobre o tema ("+others.length+")"));
    for(const s of others)d.append(studyCard(s));
    b.append(d);
  }
  if(!mine.length)b.append(note("Nenhuma avaliação de impacto foi curada para este tema ainda. Isso é lacuna do acervo, não evidência de que a política não funciona."));
  return b;
}
function seriesTable(data,group){
  const rowsByCode={};
  for(const[name,code]of Object.entries(group.codes)){
    rowsByCode[name]=new Map(data.indicators.filter(r=>r.indicator_code===code).map(r=>[r.period,Number(r.value)]));
  }
  const names=Object.keys(group.codes);
  const first=rowsByCode[names[0]];
  const latest=[...first.keys()].sort((a,b)=>periodKey(b)-periodKey(a))[0];
  if(!latest)return null;
  const parts=periodParts(latest);
  const wrap=el("div","series");
  wrap.append(el("h5","",group.label));
  if(group.note)wrap.append(note(group.note));
  const table=el("table","series-table");
  const head=el("tr");
  head.append(el("th","",parts.kind==="q"?"Mesmo trimestre":"Mesmo mês"));
  for(const n of names)head.append(el("th","",n));
  if(group.ratio)head.append(el("th","","Mulheres ÷ Homens"));
  const thead=el("thead");
  thead.append(head);
  table.append(thead);
  const body=el("tbody");
  for(let y=parts.year;y>=parts.year-6;y--){
    const period=sameSlot(parts.kind,y,parts.slot);
    const vals=names.map(n=>rowsByCode[n].get(period));
    if(vals.every(v=>v===undefined))continue;
    const tr=el("tr");
    tr.append(el("td","",fmtPeriod(period)));
    for(const v of vals)tr.append(el("td","num",v===undefined?"—":fmt(v,v>=100?0:1)));
    if(group.ratio){const[w,h]=vals;tr.append(el("td","num",w!==undefined&&h?fmt(100*w/h,0)+"%":"—"))}
    body.append(tr);
  }
  table.append(body);
  wrap.append(table);
  const sample=data.indicators.find(r=>r.indicator_code===Object.values(group.codes)[0]);
  if(sample)wrap.append(link(sample.source_url,"Fonte: "+sample.source_issuer+" ↗"));
  return wrap;
}
function observado(data,theme){
  const b=block("observed","O que mudou no país","Observado, sem atribuição");
  const groups=(data.comparison.indicators_by_theme||{})[theme]||[];
  const tables=groups.map(g=>seriesTable(data,g)).filter(Boolean);
  if(!tables.length){
    b.append(note("Sem série oficial de resultado integrada para este tema. Próximas fontes a integrar: "+(GAP_SOURCES[theme]||"a definir")+"."));
    return b;
  }
  b.append(note("Valores nacionais no mesmo período de cada ano. Mostram trajetória do país, não efeito de governo ou de proposta; fatores externos, defasagens e mudanças de método não estão controlados."));
  for(const t of tables)b.append(t);
  if(!["mulheres","economia"].includes(theme))b.append(note("Séries de preços medem custo de vida. Para resultado do serviço público, as fontes ainda a integrar são: "+(GAP_SOURCES[theme]||"a definir")+"."));
  return b;
}
function lacunas(data,theme,pair){
  const items=["Execução orçamentária (despesa liquidada e paga) e entrega de serviços ainda não estão integradas; sem elas, “fez” cobre só o registro legislativo.",
    "Decretos, portarias e votos nominais não foram coletados."];
  const noRecord=pair.filter(c=>!data.comparison.execution[c.sq]).map(c=>c.display_name||c.ballot_name);
  if(noRecord.length)items.unshift("Sem registro oficial coletado para: "+noRecord.join(" e ")+".");
  const asym=pair.map(c=>c.record&&c.record.scope).filter(Boolean);
  if(asym.length===2&&asym[0]!==asym[1])items.unshift("Os registros não são equivalentes: um é de gestão executiva (propostas do Poder Executivo), o outro é legislativo (autorias no Senado). Não há como somá-los nem compará-los em quantidade.");
  const b=block("gaps","O que ainda não sabemos");
  const ul=el("ul","gaps");
  for(const t of items)ul.append(el("li","",t));
  b.append(ul);
  return b;
}
function column(data,cand,theme){
  const col=el("article","cand-col");
  const head=el("header","cand-head");
  head.append(el("h3","",cand.display_name||cand.ballot_name),el("p","meta",cand.party+" "+cand.number+(cand.in_runoff?" · 2º turno":"")+" · ordem pelo número na urna"));
  col.append(head,pretende(data,cand,theme),disseFez(data,cand,theme),registro(data,cand,theme));
  return col;
}
function render(root,data,studies,theme,pair){
  root.replaceChildren();
  const label=(data.themes.find(t=>t.key===theme)||{}).label||theme;
  root.append(el("div","answer","Comparação descritiva do tema "+label.toLowerCase()+". Não há pontuação, ordem de mérito nem recomendação: leia as camadas separadamente. Plano é promessa; registro legislativo não é entrega; estudo de impacto trata de políticas, não de pessoas."));
  if(pair.length<2){root.append(el("div","empty","Selecione duas candidaturas com plano importado."));return}
  const grid=el("div","compare-grid");
  for(const cand of pair)grid.append(column(data,cand,theme));
  root.append(grid,observado(data,theme),impacto(data,studies,theme,pair),lacunas(data,theme,pair));
}
function themeBrief(data,studies,theme){
  const label=(data.themes.find(t=>t.key===theme)||{}).label||theme;
  const withPlan=data.candidates.filter(c=>c.plan_document_id);
  const touching=withPlan.filter(c=>((data.comparison.plans[c.sq]||{})[theme]||{}).passages>0).length;
  const records=Object.values(data.comparison.execution).reduce((n,x)=>n+((x.summary.by_theme[theme]||{}).total||0),0);
  const n=studies.filter(s=>s.themes.some(x=>norm(x)===norm(label))).length;
  const box=el("section","axis-summary");
  box.append(el("h4","",label));
  box.append(el("p","evidence-status",touching+" de "+withPlan.length+" planos de 2026 têm passagens sobre o tema; "+records+
    " proposições oficiais classificadas nele nas duas candidaturas com registro coletado; "+n+" avaliação(ões) de impacto curada(s)."));
  const b=el("button","primary small","Comparar candidaturas neste tema ↗");
  b.type="button";b.dataset.theme=theme;b.dataset.action="compare";
  box.append(b);
  return box;
}
window.CivicaCompare={render,themeBrief,fmtPeriod,periodKey};
})();
