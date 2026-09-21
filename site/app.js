const $=s=>document.querySelector(s);
let index=null,activeType="";
const money=v=>v==null?"—":new Intl.NumberFormat("cs-CZ",{style:"currency",currency:"CZK",maximumFractionDigits:0}).format(v);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[c]));
async function load(){
  try{index=await fetch("../data/index.json").then(r=>r.json());populate();render();}
  catch(e){$("#projects").innerHTML='<div class="empty">Data zatím nejsou dostupná.</div>'}
}
function populate(){
  const status=index.statuses||{}, types=index.project_types||{};
  $("#status").innerHTML='<option value="">Všechny stavy</option>'+Object.entries(status).map(([k,v])=>'<option value="'+esc(k)+'">'+esc(v.label||k)+'</option>').join("");
  $("#type").innerHTML='<option value="">Všechny typy</option>'+Object.entries(types).map(([k,v])=>'<option value="'+esc(k)+'">'+esc(v.label||k)+'</option>').join("");
}
function render(){
  const projects=index.projects||[], q=($("#search").value||"").toLowerCase().trim(), st=$("#status").value, typ=$("#type").value, sort=$("#sort").value;
  const cov=index.coverage||{}, counts=index.counts||{};
  $("#stats").innerHTML=[
    stat(index.total_projects||0,"propojených projektů"),
    stat(cov.vhodne_uverejneni_seed_loaded||0,"načtených z Vhodného uveřejnění"),
    stat(cov.registr_smluv_loaded||0,"záznamů z Registru smluv"),
    stat(counts["plneni-smlouvy"]||0,"záznamů ve stavu plnění")
  ].join("");
  let filtered=projects.filter(p=>{
    const hay=[p.title,p.id,p.supplier_ico,p.supplier_name].join(" ").toLowerCase();
    return (!st||p.status===st)&&(!typ||p.project_type===typ||p.type===typ||activeType===typ)&&(!q||hay.includes(q));
  });
  if(activeType) filtered=filtered.filter(p=>p.project_type===activeType||p.type===activeType);
  filtered.sort((a,b)=>{
    if(sort==="title") return String(a.title||"").localeCompare(String(b.title||""),"cs");
    if(sort==="sources") return (b.source_count||0)-(a.source_count||0);
    return String(b.date||"").localeCompare(String(a.date||""));
  });
  $("#result-count").textContent=filtered.length+" z "+projects.length;
  $("#projects").innerHTML=filtered.length?filtered.map(card).join(""):'<div class="empty">Žádný záznam neodpovídá zvoleným filtrům.</div>';
}
function stat(value,label){return '<div class="stat"><strong>'+esc(value)+'</strong><span>'+esc(label)+'</span></div>'}
function card(p){
  const labels=index.statuses||{}, status=labels[p.status]?.label||"Bez klasifikace";
  const type=index.project_types?.[p.project_type]?.label||"";
  const signal=p.procurement_signal?.label||"";
  return '<a class="card project-card" href="project.html?id='+encodeURIComponent(p.id)+'">'+
    '<h3>'+esc(p.title||"Bez názvu")+'</h3>'+
    '<div class="desc">'+esc(p.supplier_name||"Dodavatel není v dostupných zdrojích uveden")+'</div>'+
    '<div class="meta"><span class="badge '+(p.status==="plneni-smlouvy"?"gold":"")+'">'+esc(status)+'</span>'+
    (type?'<span class="badge">'+esc(type)+'</span>':"")+
    '<span class="source-count">'+esc(p.source_count||0)+" zdrojů</span></div>"+
    (signal?'<div class="meta" style="margin-top:9px"><span>'+esc(signal)+'</span></div>':"")+
  "</a>";
}
document.addEventListener("click",e=>{
  const b=e.target.closest("[data-filter],[data-type]");
  if(!b)return;
  e.preventDefault();
  if(b.dataset.filter!==undefined){activeType="";$("#status").value=b.dataset.filter;$("#type").value=""}
  if(b.dataset.type!==undefined){activeType=b.dataset.type;$("#type").value=b.dataset.type;$("#status").value=""}
  render();
});
$("#search").addEventListener("input",render);
$("#status").addEventListener("change",()=>{activeType="";render()});
$("#type").addEventListener("change",()=>{activeType=$("#type").value;render()});
$("#sort").addEventListener("change",render);
load();