"use strict";
const byId=(id)=>document.getElementById(id);
const state={data:null,view:"pesquisar",deferredInstall:null,backend:false};
const STOP=new Set(["de","da","do","das","dos","em","com","para","que","sao","sobre","qual","quais","como","que","foi","foram","por","uma","uns","no","na","nos","nas","os","as","um","a","o","e","ele","ela","plano","governo","proposta","propostas","documentos","dados"]);
const normalize=(value)=>String(value||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
const QUERY_NOISE=new Set(["lula","bolsonaro","candidato","candidatos","melhor","pior","voto","votar","progresso","politico","politicos"]);
const terms=(value)=>[...new Set(normalize(value).split(/[^a-z0-9]+/).filter(s=>s.length>2&&!STOP.has(s)&&!QUERY_NOISE.has(s)))].slice(0,12);
const e=(tag,cls,text)=>{const item=document.createElement(tag);if(cls)item.className=cls;if(text!==undefined)item.textContent=String(text);return item};
const official=(url)=>{try{const x=new URL(url);return x.protocol==="https:"&&/(\.gov\.br|\.jus\.br|\.leg\.br)$/.test(x.hostname)}catch{return false}};
const isVerdict=(q)=>/(melhor|pior|recomend|quem devo votar|em quem votar|qual candidato escolher|ranking|ranque|mais vantajos|pontuacao|nota eleitoral)/.test(normalize(q))&&/(lula|bolsonaro|candidat|president|politic|elei|partid|vot)/.test(normalize(q));
const getTopic=(text)=>{
  const s=normalize(text);
  const topics={
    economia:["econom","inflac","ipca","renda","emprego","salario","pobreza"],
    "saúde":["saude","sus","hospital","vacina","medicament","mortalidade"],
    "educação":["educa","escola","universidade","alfabet","ensino","estudant"],
    "segurança":["seguranca","violencia","homicid","policia"],
    "justiça":["justica","judici","tribunal","direito"],
    "habitação":["habita","moradia","aluguel","saneamento"],
    ambiente:["ambien","floresta","clima","desmat","energia"]
  };
  for(const [key,words] of Object.entries(topics)){if(words.some(w=>s.includes(w)))return key}
  return "geral";
};
function move(view){
  state.view=view;
  document.querySelectorAll(".view").forEach(item=>{const active=item.id==="view-"+view;item.hidden=!active;item.classList.toggle("active",active)});
  document.querySelectorAll("[data-view]").forEach(item=>{const active=item.dataset.view===view;item.classList.toggle("active",active);item.setAttribute("aria-current",active?"page":"false")});
  if(view==="documentos")renderDocuments();
  if(view==="cruzamentos")renderCross();
  window.scrollTo({top:0,behavior:"instant"});
}
function link(url,label){
  const a=e("a","source-link",label||"Consultar fonte original ↗");
  if(official(url)){a.href=url;a.target="_blank";a.rel="noopener noreferrer"}
  else {a.textContent="Origem não verificada";a.removeAttribute("href")}
  return a;
}
function empty(message){return e("div","empty",message)}
function card(row,kind){
  const box=e("article","record");
  const head=e("div","record-head");
  head.append(e("span","label-pill",kind),e("span","meta",row.page?"Página "+row.page:""));
  box.append(head);
  box.append(e("h3","",row.title||row.indicator_name||"Registro público"));
  if(row.body)box.append(e("p","reading",row.body));
  if(row.value!==undefined)box.append(e("p","","Valor publicado: "+Number(row.value).toLocaleString("pt-BR")+" "+(row.unit||"")+" · "+row.period));
  if(row.population)box.append(e("p","meta",row.population+" · "+row.territory+" · "+row.period));
  if(row.person)box.append(e("p","meta","Documento registrado: "+row.person));
  if(row.sha256)box.append(e("div","hash","SHA-256: "+row.sha256));
  box.append(link(row.source_url));
  return box;
}
function section(container,title,items,kind){
  const h=e("div","group-title");h.append(e("span","",title),e("small","",items.length+" registros"));
  container.append(h);
  const list=e("div","record-list");
  if(items.length){for(const item of items)list.append(card(item,kind))}
  else list.append(empty("Nenhum registro disponível nesta categoria do acervo atual. Isso não demonstra ausência de ações ou dados na realidade."));
  container.append(list);
}
function findRecords(query){
  if(!state.data)return {excerpts:[],indicators:[]};
  const words=terms(query);
  if(words.length===0)return {excerpts:[],indicators:[]};
  const ranked=[];
  for(const row of state.data.excerpts){
    const hay=normalize((row.title||"")+" "+(row.person||"")+" "+(row.theme||"")+" "+(row.body||""));
    const score=words.reduce((n,w)=>n+(hay.includes(w)?1:0),0);
    if(score>0)ranked.push({row,score});
  }
  ranked.sort((a,b)=>b.score-a.score||a.row.document_id-b.row.document_id||a.row.page-b.row.page);
  // Fair source diversity: show a first relevant excerpt per document before repeats.
  const used=new Set(),excerpts=[];
  for(const pass of [1,2]){
    for(const item of ranked){
      if(excerpts.length>=10)break;
      if(pass===1&&used.has(item.row.document_id))continue;
      if(pass===2&&!used.has(item.row.document_id))continue;
      if(pass===1)used.add(item.row.document_id);
      if(!excerpts.some(x=>x.id===item.row.id))excerpts.push(item.row);
    }
  }
  const indicators=state.data.indicators.filter(row=>{
    const hay=normalize(row.indicator_name+" "+row.indicator_code+" "+row.population+" "+row.territory);
    return words.some(w=>hay.includes(w));
  }).slice(0,12);
  return {excerpts,indicators};
}
const EVIDENCE_AXES=[
  {label:"Mulheres",tokens:["mulher","feminin","feminic","genero","creche","maternidade","igualdade salarial"],query:/mulher|feminin|feminic|g[eê]nero|creche|maternidade/i},
  {label:"Economia",tokens:["econom","renda","emprego","inflac","ipca","salario","tribut","pobreza"],query:/econom|renda|emprego|infla|ipca|sal[aá]rio|tribut|pobreza/i},
  {label:"Saúde",tokens:["saude","sus","hospital","vacina"],query:/sa[uú]de|sus|hospital|vacina/i},
  {label:"Educação",tokens:["educa","escola","universid","alfabet"],query:/educa|escola|universid|alfabet/i},
  {label:"Segurança",tokens:["seguranca","violencia","homicid","policia"],query:/seguran|viol[eê]ncia|homic[ií]d|pol[ií]cia/i},
  {label:"Justiça",tokens:["justica","judici","tribunal"],query:/justi[cç]a|judici|tribunal/i},
  {label:"Habitação",tokens:["habitac","moradia","aluguel","saneamento"],query:/habitac|moradia|aluguel|saneamento/i},
  {label:"Meio ambiente",tokens:["ambient","florest","clima","desmat","energia"],query:/ambient|florest|clima|desmat|energia/i}
];
function monthlyIndex(period){
  const s=String(period||"");
  if(!/^[0-9]{6}$/.test(s))return NaN;
  const year=Number(s.slice(0,4)),month=Number(s.slice(4,6));
  return month>=1&&month<=12?year*12+month:NaN;
}
function recentYear(series){
  const ordered=series.slice().sort((a,b)=>monthlyIndex(b.period)-monthlyIndex(a.period));
  const last=ordered.slice(0,12);
  if(last.length!==12||last.some((row,i)=>!Number.isFinite(Number(row.value))||
      monthlyIndex(row.period)!==monthlyIndex(last[0].period)-i))return null;
  return {period:ordered[0].period,value:(last.reduce((factor,row)=>factor*(1+Number(row.value)/100),1)-1)*100};
}
function evidenceLine(parent,title,description,source){
  const row=e("div","evidence-line");
  row.append(e("strong","",title),e("p","",description));
  if(source)row.append(link(source.url,source.label));
  parent.append(row);
}
function evidenceOverview(question){
  const root=e("div","evidence-overview");
  const normalized=normalize(question);
  const axes=EVIDENCE_AXES.filter(axis=>axis.query.test(normalized));
  const fallback=terms(question).filter(word=>!["resultado","resultados","impacto","impactos","tema","temas","convergencia","cruzamento","comparar","comparativo"].includes(word));
  const selected=axes.length?axes:(fallback.length?[{label:"Tema pesquisado",tokens:fallback}]:[]);
  root.append(e("h3","","Evidências cruzadas por tema"));
  if(!selected.length)root.append(e("p","","Especifique um assunto para localizar documentos e indicadores relacionados."));
  for(const axis of selected){
    const matched=state.data.excerpts.filter(row=>{
      const body=normalize(row.body);
      return axis.tokens.some(token=>body.includes(normalize(token)));
    });
    const unique=rows=>[...new Map(rows.map(row=>[row.document_id,row])).values()];
    const plans=unique(matched.filter(row=>row.doc_type==="plano_eleitoral"));
    const proposals=unique(matched.filter(row=>row.doc_type==="proposicao_legislativa"));
    const others=unique(matched.filter(row=>row.doc_type!=="plano_eleitoral"&&row.doc_type!=="proposicao_legislativa"));
    const indicatorRows=state.data.indicators.filter(row=>{
      const descriptor=normalize(row.indicator_name+" "+row.indicator_code+" "+(row.population||""));
      return axis.tokens.some(token=>descriptor.includes(normalize(token)));
    });
    // Multiple months of one series are repeated measurements, not independent sources.
    const grouped=new Map();
    for(const row of indicatorRows){
      const origin=normalize(row.indicator_code+" "+row.indicator_name).includes("ipca")?"IBGE_IPCA":row.source_issuer;
      const key=[origin,row.territory,origin==="IBGE_IPCA"?"indice geral":row.population,row.unit].join("|");
      if(!grouped.has(key))grouped.set(key,[]);
      grouped.get(key).push(row);
    }
    const series=[...grouped.values()].map(rows=>{
      // IBGE and BCB may republish the same IPCA observation: count its origin once.
      const uniquePeriods=new Map();
      for(const row of rows){
        const current=uniquePeriods.get(row.period);
        if(!current||normalize(row.source_issuer).startsWith("ibge"))uniquePeriods.set(row.period,row);
      }
      return [...uniquePeriods.values()].sort((a,b)=>monthlyIndex(b.period)-monthlyIndex(a.period));
    });
    const origins=new Set(indicatorRows.map(row=>normalize(row.indicator_code+" "+row.indicator_name).includes("ipca")?"ibge":normalize(row.source_issuer)));
    const card=e("section","axis-summary");
    card.append(e("h4","",axis.label));
    card.append(e("p","evidence-status",
      "Convergência de resultados ainda não demonstrada. "+series.length+
      (series.length===1?" série observada":" séries observadas")+" de "+origins.size+
      (origins.size===1?" origem":" origens")+". Compatibilidade das medidas e vínculos com execução exigem verificação."));
    const representative=matched.map(row=>{
      const body=normalize(row.body);
      return {row,score:axis.tokens.reduce((n,t)=>n+(body.includes(normalize(t))?1:0),0)};
    }).sort((a,b)=>b.score-a.score)[0]?.row;
    const documentCount=plans.length+proposals.length+others.length;
    evidenceLine(card,"Documentos",documentCount?
      documentCount+" documento(s) com menção lexical ao tema: "+plans.length+" plano(s), "+proposals.length+" ementa(s) legislativa(s) e "+others.length+" outro(s). Menções não confirmam a mesma afirmação ou medida.":
      "Nenhum documento do acervo corresponde aos termos deste tema.",
      representative?{url:representative.source_url,label:"Abrir documento oficial · página "+representative.page+" ↗"}:null);
    if(representative){
      const clean=representative.body.replace(/\s+/g," ").trim();
      const positions=axis.tokens.map(token=>normalize(clean).indexOf(normalize(token))).filter(n=>n>=0);
      const at=positions.length?Math.min(...positions):0;
      const from=Math.max(0,at-70),to=Math.min(clean.length,at+180);
      card.append(e("p","source-excerpt","Trecho: "+(from?"…":"")+clean.slice(from,to)+(to<clean.length?"…":"")));
    }
    evidenceLine(card,"Execução","Ainda não há, neste acervo, atos concluídos, orçamento executado ou serviços entregues vinculados ao tema.");
    if(series.length){
      for(const rows of series.slice(0,4)){
        const latest=rows[0],annual=recentYear(rows);
        const context=latest.indicator_name+": "+Number(latest.value).toLocaleString("pt-BR")+" "+(latest.unit||"")+" em "+latest.period.slice(4,6)+"/"+latest.period.slice(0,4)+
          " · "+latest.territory+" · "+rows.length+" período(s) desta série.";
        const addition=annual?" Acumulado móvel de 12 meses, calculado a partir da série mensal: "+annual.value.toLocaleString("pt-BR",{maximumFractionDigits:2,minimumFractionDigits:2})+" %.":"";
        evidenceLine(card,"Resultado observado",context+addition+" Não mede, por si, a execução de uma proposta.",
          {url:latest.source_url,label:"Consultar série original ↗"});
      }
      if(series.length>4)card.append(e("p","", "Mais "+(series.length-4)+" série(s) no acervo."));
    }else evidenceLine(card,"Resultado observado","Nenhuma série de indicadores específica deste tema está integrada ao acervo.");
    evidenceLine(card,"Impacto","Não há estudo de atribuição causal ou contrafactual integrado para este tema. Variações observadas não demonstram o efeito de uma ação.");
    card.append(e("p","evidence-method","Critério: só tratar medidas como convergentes após checar fontes independentes, mesma definição, território, população, período e sentido do resultado. Documentos repetidos e meses da mesma série não contam como confirmação independente."));
    root.append(card);
  }
  return root;
}

async function liveQuery(question){
  const response=await fetch("./api/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question})});
  if(!response.ok)throw Error("API indisponível");
  return response.json();
}
async function search(){
  const question=byId("question").value.trim();
  if(question.length<3){byId("question").focus();return}
  const zone=byId("result-zone"),body=byId("results");
  zone.hidden=false;body.replaceChildren();
  const button=byId("search");button.disabled=true;
  const blocked=isVerdict(question);
  byId("answer").textContent="Consultando documentos indexados…";
  try{
    if(state.data){
      const result=findRecords(question);
      byId("answer").textContent=blocked?
        "A pergunta solicita um julgamento eleitoral. Abaixo está a evidência factual que o acervo possui sobre os assuntos citados, com suas lacunas; ela não estabelece uma escolha de voto.":
        "Resumo factual dos assuntos pesquisados, seguido dos registros originais. Menções em planos e indicadores agregados não comprovam implementação nem impacto.";
      body.append(evidenceOverview(question));
      section(body,"Trechos de documentos",result.excerpts,"DOCUMENTO");
      section(body,"Indicadores observados",result.indicators,"INDICADOR");
    }else{
      const result=await liveQuery(question);
      byId("answer").textContent=result.answer;
      section(body,"Documentos e passagens",result.sources.map(s=>({...s,body:s.body,title:s.title,sha256:s.sha256})),"DOCUMENTO");
      section(body,"Indicadores observados",result.indicators,"INDICADOR");
    }
  }catch{
    byId("answer").textContent="Não foi possível consultar o acervo neste momento. Abra o aplicativo online uma vez para obter uma cópia offline dos documentos.";
  }finally{button.disabled=false;zone.scrollIntoView({behavior:"smooth",block:"start"})}
}
function renderCross(){
  const root=byId("cross-result");
  root.replaceChildren();
  if(!state.data){root.append(empty("O acervo público ainda não está disponível neste dispositivo."));return}
  const topic=byId("theme").value;
  const excerpts=state.data.excerpts.filter(x=>x.theme===topic);
  const plans=[],laws=[];
  const planSeen=new Set(),lawsSeen=new Set();
  for(const row of excerpts){
    if(row.doc_type==="plano_eleitoral"&&!planSeen.has(row.document_id)){
      plans.push(row);planSeen.add(row.document_id);
    }
    if(row.doc_type==="proposicao_legislativa"&&!lawsSeen.has(row.document_id)){
      laws.push(row);lawsSeen.add(row.document_id);
    }
  }
  const indicators=state.data.indicators.filter(x=>getTopic(x.indicator_name)===topic).slice(0,12);
  root.append(evidenceOverview(topic));
  root.append(e("div","answer","Os registros abaixo ampliam a consulta documental. Coincidência de tema não demonstra execução ou impacto."));
  section(root,"Compromissos registrados",plans.slice(0,16),"PLANO ELEITORAL");
  section(root,"Proposições legislativas",laws.slice(0,16),"EMENTA");
  section(root,"Indicadores publicados",indicators,"DADO OBSERVADO");
}
function renderDocuments(){
  const container=byId("document-list");
  container.replaceChildren();
  if(!state.data){container.append(empty("A biblioteca será exibida depois da sincronização inicial."));return}
  const docs=state.data.documents.slice().sort((a,b)=>(b.election_year||0)-(a.election_year||0));
  section(container,"Documentos oficiais disponíveis",docs.map(d=>({...d,
    body:(d.doc_type==="plano_eleitoral"?"Plano eleitoral integral registrado. ":"Documento legislativo registrado. ")+
      "Arquivo vinculado à fonte original, com "+(d.page_count||"número de")+" página(s) e assinatura de integridade."
  })), "FONTE PÚBLICA");
}
async function loadData(){
  try{
    const res=await fetch("./data/evidence.json",{cache:"no-cache"});
    if(!res.ok)throw Error("No snapshot");
    const data=await res.json();
    if(data.schema_version!=="app-snapshot-1"||!Array.isArray(data.excerpts)||!Array.isArray(data.indicators))throw Error("Schema inválido");
    state.data=data;
    byId("doc-count").textContent=data.counts.documents.toLocaleString("pt-BR");
    byId("excerpt-count").textContent=data.counts.excerpts.toLocaleString("pt-BR");
    byId("indicator-count").textContent=data.counts.indicators.toLocaleString("pt-BR");
    byId("updated").textContent="Acervo gerado em "+new Date(data.generated_at).toLocaleDateString("pt-BR",{timeZone:"UTC"});
    byId("connection").textContent=navigator.onLine?"Acervo disponível":"Modo offline";
  }catch{
    byId("connection").textContent=navigator.onLine?"API ou acervo pendente":"Sem cópia offline";
    try{
      const result=await fetch("./api/documents");
      if(!result.ok)throw Error("API ausente");
      const docs=await result.json();
      state.backend=true;
      byId("doc-count").textContent=(docs.documents||[]).length.toLocaleString("pt-BR");
      byId("updated").textContent="API disponível · exportação offline ainda não gerada";
    }catch{
      byId("updated").textContent="Dados ainda não carregados neste dispositivo";
    }
  }
}
function installSupport(){
  byId("install").hidden=window.matchMedia("(display-mode: standalone)").matches;
  window.addEventListener("beforeinstallprompt",ev=>{
    ev.preventDefault();state.deferredInstall=ev;byId("install").hidden=false;
  });
  byId("install").addEventListener("click",async()=>{
    const prompt=state.deferredInstall;
    if(prompt){prompt.prompt();await prompt.userChoice;state.deferredInstall=null;byId("install").hidden=true;return}
    byId("install-tip").textContent="No navegador, abra o menu e selecione 'Adicionar à tela inicial'.";
    byId("install-tip").hidden=false;
  });
  window.addEventListener("appinstalled",()=>{byId("install").hidden=true;byId("install-tip").hidden=true});
}
function init(){
  document.querySelectorAll("[data-view]").forEach(el=>el.addEventListener("click",()=>move(el.dataset.view)));
  document.querySelectorAll("[data-example]").forEach(el=>el.addEventListener("click",()=>{move("pesquisar");byId("question").value=el.dataset.example;search()}));
  byId("search").addEventListener("click",search);
  byId("question").addEventListener("keydown",ev=>{if(ev.key==="Enter"&&(ev.ctrlKey||ev.metaKey))search()});
  byId("cross-search").addEventListener("click",renderCross);
  installSupport();
  if("serviceWorker" in navigator && (location.protocol==="https:"||location.hostname==="localhost")){
    navigator.serviceWorker.register("./sw.js").catch(()=>{});
  }
  window.addEventListener("offline",()=>{byId("connection").textContent="Modo offline"});
  window.addEventListener("online",()=>{byId("connection").textContent="Acervo disponível"});
  loadData();
}
document.addEventListener("DOMContentLoaded",init);
