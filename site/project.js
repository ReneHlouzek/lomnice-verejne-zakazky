const root=document.querySelector('#detail');
const id=new URLSearchParams(location.search).get('id');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const money=v=>v==null?'—':new Intl.NumberFormat('cs-CZ',{style:'currency',currency:'CZK',maximumFractionDigits:0}).format(v);
const pct=v=>v==null?'—':`${v>=0?'+':''}${Number(v).toFixed(1)} %`;

function sourceRows(ss){
  return ss.map(s=>{
    const r=s.record||s;
    const url=r.source_url||s.source_url;
    const title=r.title||r.subject||'';
    const supplier=r.supplier_name||r.supplier_ico||'';
    return `<div class="source"><strong>${esc(r.source||s.source||'zdroj')}</strong><p>${esc(title)}</p>${supplier?`<p class="meta">Dodavatel: ${esc(supplier)}</p>`:''}${url?`<a href="${esc(url)}" target="_blank" rel="noopener">Otevřít zdroj →</a>`:''}</div>`;
  }).join('');
}

async function run(){
  if(!id){root.innerHTML='<div class="empty">Chybí identifikátor zakázky.</div>';return}
  try{
    const p=await fetch(`../data/projects/${encodeURIComponent(id)}.json`).then(r=>r.json());
    const c=p.canonical||{},f=c.financial||{},a=p.analysis||{},events=c.lifecycle?.events||[],ss=p.sources||[];
    const suppliers=[...new Map(ss.map(s=>{const r=s.record||s;const ico=r.supplier_ico||r.ico_dodavatele;return ico?[String(ico),r.supplier_name||ico]:null}).filter(Boolean)).values()];
    const addenda=events.filter(e=>e.type==='addendum').length;
    root.innerHTML=`
      <p class="eyebrow">DETAIL ZÁZNAMU</p>
      <h1>${esc(p.title||c.title)}</h1>
      <div class="stats">
        <div class="stat"><strong>${money(f.initial_contract_price)}</strong><span>výchozí pozorovaná cena</span></div>
        <div class="stat"><strong>${money(f.latest_observed_price)}</strong><span>poslední pozorovaná cena</span></div>
        <div class="stat"><strong>${addenda}</strong><span>dodatků / změnových záznamů</span></div>
        <div class="stat"><strong>${c.source_count||0}</strong><span>zdrojových záznamů</span></div>
      </div>
      <section class="card"><h2>Zařazení</h2><p><strong>${esc(p.status||'neuvedeno')}</strong></p><p class="meta">${esc(c.project_type||p.project_type||'')}</p>${c.procurement_signal?`<p class="meta">${esc(c.procurement_signal.label)} — ${esc(c.procurement_signal.reason)}</p>`:''}</section>
      <section class="card"><h2>Dodavatel</h2>${suppliers.length?suppliers.map(x=>`<p><strong>${esc(x)}</strong></p>`).join(''):'<p class="meta">Dodavatel zatím není ve zdrojových datech uveden.</p>'}</section>
      <section class="card"><h2>Finanční mapa</h2>${finance(f,events)}</section>
      <section class="card"><h2>Časová osa</h2>${timeline(events)}</section>
      <section class="card"><h2>Kontrolní signály</h2>${signals(a.signals||[])}</section>
      <section class="card"><h2>Zdroje a dokumentace</h2>${ss.length?sourceRows(ss):'<p class="meta">Zdroje zatím nejsou evidovány.</p>'}</section>`;
  }catch(e){root.innerHTML='<div class="empty">Detail se nepodařilo načíst.</div>'}
}
function finance(f,es){
  const prices=es.filter(e=>e.price!=null);
  if(!prices.length)return'<p class="meta">Pro finanční mapu zatím není k dispozici dostatek cenových údajů.</p>';
  return`<div class="finance-map">${prices.map((e,i)=>`<div class="finance-step"><span>${i===0?'Výchozí':esc(e.type||'Změna')}</span><strong>${money(e.price)}</strong><small>${esc(e.date||'Datum neuvedeno')}</small>${i?`<em>${change(prices[i-1].price,e.price)}</em>`:''}</div>`).join('')}</div><p class="meta">Mapa zobrazuje pouze ceny skutečně nalezené v evidovaných zdrojích. Nejde o právní ani účetní závěr.</p>`;
}
function change(a,b){if(a==null)return'';const d=b-a,p=a?d/a*100:0;return`${d>=0?'+':''}${money(d)} (${pct(p)})`}
function timeline(es){
  if(!es.length)return'<p class="meta">Časová osa zatím nemá dostatek dat.</p>';
  return'<div class="timeline">'+es.map(e=>`<div class="timeline-item"><div class="dot"></div><div><strong>${esc(e.date||'Datum neuvedeno')}</strong><span class="badge">${esc(e.type||'záznam')}</span><p>${esc(e.title||'')}${e.price!=null?` · <strong>${money(e.price)}</strong>`:''}</p></div></div>`).join('')+'</div>';
}
function signals(ss){
  if(!ss.length)return'<p class="meta">Žádný kontrolní signál.</p>';
  return ss.map(s=>`<div class="signal"><span class="badge">${esc(s.level||'info')}</span><strong>${esc(s.code||s.type||'kontrola')}</strong><p>${esc(s.message||s.description||'')}</p>${s.evidence?.length?`<p class="meta">Evidence: ${esc(JSON.stringify(s.evidence))}</p>`:''}</div>`).join('');
}
run();
