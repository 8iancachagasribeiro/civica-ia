"use strict";
/* Meu cenário: filtra os eixos de vida que se aplicam à pessoa e mostra, lado a lado, o que cada
   candidatura já tem como lei/ato, o que promete, dados nacionais, estudos e lacunas.
   As respostas existem só em memória: sem rede, sem armazenamento, sem pontuação ou ranking. */
(function(){
const C=window.CivicaCompare,{el,link,note,passage,seriesTable,studyCard,block}=C;
const STAGES=["lei","aprovada","tramitando","encerrada","perdeu_eficacia"];

function reasons(rule,profile,fields){
  if(rule.always)return["Aparece para todas as pessoas"];
  const out=[];
  for(const[key,value]of rule.any||[]){
    if(profile[key]!==value)continue;
    const field=fields.find(f=>f.key===key);
    out.push(value===true?field.label:field.label+": "+field.options.find(o=>o.value===value).label);
  }
  return out;
}
const applies=(rule,profile)=>!!rule.always||(rule.any||[]).some(([k,v])=>profile[k]===v);

function buildForm(form,fields,onChange){
  form.replaceChildren();
  for(const f of fields){
    const box=el("fieldset","sc-field");
    box.append(el("legend","",f.label));
    if(f.type==="radio"){
      for(const o of[{value:"",label:"Prefiro não informar"},...f.options]){
        const label=el("label","sc-opt"),input=el("input");
        input.type="radio";input.name=f.key;input.value=o.value;if(o.value==="")input.checked=true;
        label.append(input,el("span","",o.label));box.append(label);
      }
    }else{
      const label=el("label","sc-opt"),input=el("input");
      input.type="checkbox";input.name=f.key;
      label.append(input,el("span","",f.label));
      box.replaceChildren(label);
    }
    form.append(box);
  }
  form.addEventListener("change",onChange);
}
function readProfile(form,fields){
  const profile={};
  for(const f of fields){
    if(f.type==="radio"){const on=form.querySelector('input[name="'+f.key+'"]:checked');profile[f.key]=on&&on.value?on.value:null}
    else profile[f.key]=form.querySelector('input[name="'+f.key+'"]').checked;
  }
  return profile;
}

function planBlock(data,cand,axis){
  const b=block("plan","No plano 2026","Promessas e alegações");
  const entry=axis.cands[cand.sq]||{plan:[],plan_total:0};
  if(!cand.plan_document_id){b.append(note("Plano não importado."));return b}
  if(!entry.plan.length){b.append(note("O plano não trata deste eixo nos termos pesquisados. É leitura lexical: pode tratar com outras palavras."));return b}
  b.append(note(entry.plan_total+" passagem(ns) do plano tocam este eixo; mostrando "+entry.plan.length+", uma por página."));
  for(const pair of entry.plan){
    const row=data._byId&&data._byId.get(pair[0]);
    b.append(passage(data,cand,pair,row&&row.kind==="compromisso"?"compromisso":row&&row.kind==="balanco"?"alegação":""));
  }
  return b;
}
function recordBlock(data,cand,axis){
  const b=block("record","Registro oficial","Câmara e Senado");
  const ex=data.comparison.execution[cand.sq],rec=(axis.cands[cand.sq]||{}).records;
  if(!ex||!cand.record||!rec){b.append(note("Registro de proposições não coletado para esta candidatura. Isso não significa ausência de atuação."));return b}
  b.append(note(cand.record.office+"."));
  if(!rec.count){b.append(note("Nenhuma proposição deste eixo no recorte coletado."));return b}
  const L=data.comparison.stage_labels;
  const parts=STAGES.filter(k=>rec.by_stage[k]).map(k=>rec.by_stage[k]+" "+L[k].toLowerCase());
  b.append(el("p","layer-count",rec.count+" proposição(ões): "+parts.join(" · ")+"."));
  const list=el("ul","record-mini");
  for(const r of rec.items){
    const li=el("li",""),head=el("div","mini-head");
    head.append(el("span","stage stage-"+r.st,L[r.st]),el("strong","",r.id),el("span","meta",r.d.slice(0,4)));
    li.append(head,el("p","",r.e.length>210?r.e.slice(0,207)+"…":r.e),link(r.u,r.b+" ↗"));
    list.append(li);
  }
  b.append(list);
  if(rec.count>rec.items.length)b.append(note("Mostrando "+rec.items.length+" de "+rec.count+". Aberturas de crédito ficam de fora. Proposta apresentada não é lei; lei não é resultado."));
  return b;
}
function axisCard(data,studies,axis,profile,fields,pair){
  const card=el("article","axis-card");
  const head=el("header","axis-card-head");
  head.append(el("h3","",axis.title),el("p","axis-why",axis.why));
  const chips=el("p","axis-reasons");
  for(const r of reasons(axis.applies,profile,fields))chips.append(el("span","label-pill",r));
  head.append(chips);card.append(head);
  const grid=el("div","compare-grid");
  for(const cand of pair){
    const col=el("div","cand-col");
    const h=el("header","cand-head");
    h.append(el("h4","",cand.display_name||cand.ballot_name),el("p","meta",cand.party+" "+cand.number+(cand.in_runoff?" · 2º turno":"")));
    col.append(h,planBlock(data,cand,axis),recordBlock(data,cand,axis));
    grid.append(col);
  }
  card.append(grid);
  const shared=block("observed","Dado oficial do país","Sem atribuição a governo");
  const tables=(axis.series||[]).map(g=>seriesTable(data,g)).filter(Boolean);
  if(tables.length){shared.append(note("Mesmo período em cada ano. Mostra a trajetória nacional, não efeito de governo ou de proposta."));for(const t of tables)shared.append(t)}
  else shared.append(note("Sem série oficial integrada para este eixo."));
  card.append(shared);
  const evidence=block("impact","Estudos de impacto","Avaliam políticas, não candidaturas");
  const mine=(axis.studies||[]).map(id=>studies.find(s=>s.id===id)).filter(Boolean);
  if(mine.length)for(const s of mine)evidence.append(studyCard(s));
  else evidence.append(note("Nenhum estudo curado para este eixo. Isso é lacuna do acervo, não evidência de que uma política funciona ou deixa de funcionar."));
  card.append(evidence);
  const notes=block("gaps","Antes de decidir");
  const ul=el("ul","gaps");
  for(const c of axis.caveats)ul.append(el("li","",c));
  ul.append(el("li","","Confira você: "+axis.check));
  notes.append(ul);card.append(notes);
  return card;
}
function render(form,result,data,studies,pair){
  const personal=data.comparison.personal;
  if(!personal){result.replaceChildren(el("div","empty","Cenário indisponível neste acervo. Atualize os dados."));return}
  if(!form.dataset.built){
    buildForm(form,personal.profile,()=>render(form,result,data,studies,CivicaScenario.currentPair()));
    form.dataset.built="1";
  }
  if(!data._byId)data._byId=new Map(data.excerpts.map(row=>[row.id,row]));
  const profile=readProfile(form,personal.profile);
  result.replaceChildren();
  if(pair.length<2){result.append(el("div","empty","Escolha duas candidaturas com plano importado."));return}
  if(pair[0].sq===pair[1].sq){result.append(el("div","empty","Escolha duas candidaturas diferentes."));return}
  const shown=personal.axes.filter(a=>applies(a.applies,profile));
  result.append(el("div","answer","Mostrando "+shown.length+" de "+personal.axes.length+" eixos para o cenário que você marcou. "+
    "Cada eixo é independente: não há soma, nota nem ordem de mérito. A ordem dos eixos e das candidaturas é fixa (número na urna)."));
  for(const axis of shown)result.append(axisCard(data,studies,axis,profile,personal.profile,pair));
  const hidden=personal.axes.length-shown.length;
  if(hidden)result.append(note(hidden+" eixo(s) não aparecem porque não se aplicam às situações marcadas. Marque outras situações para ver mais."));
}
let getPair=()=>[];
window.CivicaScenario={render,setPairProvider(fn){getPair=fn},currentPair:()=>getPair()};
})();
