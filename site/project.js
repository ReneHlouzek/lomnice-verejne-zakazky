const root=document.querySelector('#detail');
const id=new URLSearchParams(location.search).get('id');

const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const money=v=>v==null?'—':new Intl.NumberFormat('cs-CZ',{style:'currency',currency:'CZK',maximumFractionDigits:0}).format(v);
const pct=v=>v==null?'—':`${v>=0?'+':''}${Number(v).toFixed(1)} %`;
const date=v=>v?new Intl.DateTimeFormat('cs-CZ').format(new Date(v+'T00:00:00')):'—';
const normalizeSource=s=>{const v=String(s||'').toLowerCase().trim();if(v==='vhodne-uverejneni'||v==='vhodné uveřejnění'||v==='vu')return 'vhodne-uverejneni';if(v==='registr-smluv'||v==='registr smluv'||v==='rs')return 'registr-smluv';return v;};

const statusLabels={
  'plneni-smlouvy':'Plnění smlouvy',
  'ukonceno-plneni':'Ukončeno plnění',
  'zruseno':'Zrušeno',
  'aktualni-uverejneni':'Aktuální uveřejnění',
  'unclassified':'Nezařazeno'
};
const typeLabels={
  procurement:'Veřejná zakázka',
  procurement_with_changes:'Veřejná zakázka se změnami',
  contract:'Smlouva',
  contract_with_changes:'Smlouva se změnami',
  other:'Jiný záznam'
};

function documentsSection(ss,analysis){
  const ids=new Set(), urls=new Set();
  const sourceDocs=[];
  ss.forEach(s=>{
    const r=s.record||s;
    if(r.source_id)ids.add(String(r.source_id));
    if(r.source_url)urls.add(String(r.source_url));
    const xmlDocs=Array.isArray(r.xml_documents)?r.xml_documents.filter(d=>d&&d.url):[];
    xmlDocs.forEach(d=>sourceDocs.push({
      ...d,
      source:r.source||s.source,
      source_id:r.source_id,
      source_title:r.title||r.subject||'Zdrojový záznam'
    }));
  });
  const docs=(analysis?.documents||[]).filter(d=>
    (d.source_id!=null && ids.has(String(d.source_id))) ||
    (d.source_url && urls.has(String(d.source_url)))
  );
  const analyzed=[...new Map(docs.map(d=>[
    [d.source_id||'',d.document_name||d.text_file||''].join('|'),
    d
  ])).values()];
  const linked=[...new Map(sourceDocs.map(d=>[
    String(d.url),
    d
  ])).values()];
  if(!analyzed.length&&!linked.length)return '';
  const typeLabels={contract:'smlouva',addendum:'dodatek',budget:'rozpočet',change_sheet:'změnový list',grant:'dotace',tender:'zakázka',deadline:'termíny'};
  return `<section id="documents" class="card">
    <div class="section-title"><div><p class="eyebrow dark">DOKUMENTY</p><h2>Dokumenty a přílohy</h2></div><span>${linked.length+analyzed.length} položek</span></div>
    <p class="method-note">Rozlišujeme dokumenty pouze uvedené ve zdrojovém záznamu a dokumenty, jejichž PDF bylo lokálně staženo a automaticky analyzováno. Absence v jedné skupině neznamená, že dokument neexistuje.</p>
    ${linked.length?`<div class="document-subsection"><h3>Dokumenty uvedené v oficiálním PVU XML</h3><div class="document-links">${linked.map((d,j)=>`<a href="${esc(d.url)}" target="_blank" rel="noopener"><span>${esc(d.label||('Dokument '+(j+1)))}</span><small>${esc(sourceLabel(d.source))}${d.source_id?' · '+esc(d.source_id):''}</small> →</a>`).join('')}</div></div>`:''}
    ${analyzed.length?`<div class="document-subsection"><h3>Lokálně analyzované PDF</h3><div class="document-list">${analyzed.map(d=>`<article class="source document-item">
      <div class="source-head"><span class="source-no">PDF</span><strong>${esc(d.document_name||'Dokument')}</strong></div>
      <div class="badges">${(d.document_types||[]).map(t=>`<span class="badge">${esc(typeLabels[t]||t)}</span>`).join('')}</div>
      <div class="source-grid">
        <span><small>Text</small><b>${Number(d.text_chars||0).toLocaleString('cs-CZ')} znaků</b></span>
        <span><small>Částky</small><b>${d.amounts_czk?.length?d.amounts_czk.map(money).join(', '):'—'}</b></span>
        <span><small>Data</small><b>${d.dates?.length?d.dates.slice(0,5).map(date).join(', '):'—'}</b></span>
      </div>
      ${d.snippets?.length?`<details><summary>Ukázky nalezeného textu</summary><div class="document-snippets">${d.snippets.map(x=>`<p>${esc(x)}</p>`).join('')}</div></details>`:''}
    </article>`).join('')}</div></div>`:''}
  </section>`;
}
function sourceRows(ss){
  return ss.map((s,i)=>{
    const r=s.record||s;
    const url=r.source_url||s.source_url;
    const title=r.title||r.subject||'Zdrojový záznam';
    const supplier=r.supplier_name||r.supplier_ico||'';
    const verified=r.verified_web===true;
    const officialXml=r.verification_level==='official_xml' || r.official_xml_available===true;
    const xmlDocs=Array.isArray(r.xml_documents)?[...new Map(r.xml_documents.filter(d=>d&&d.url).map(d=>[d.url,d])).values()]:[];
    return `<article class="source">
      <div class="source-head"><span class="source-no">${i+1}</span><strong>${esc(sourceLabel(r.source||s.source))}</strong>${officialXml?'<span class="badge green">oficiální PVU XML</span>':verified?'<span class="badge green">ověřeno na webu</span>':''}</div>
      <h3>${esc(title)}</h3>
      <div class="source-grid">
        ${r.date?`<span><small>Datum</small><b>${date(r.date)}</b></span>`:''}
        ${supplier?`<span><small>Dodavatel</small><b>${esc(supplier)}</b></span>`:''}
        ${r.price!=null?`<span><small>Cena bez DPH</small><b>${money(r.price)}</b></span>`:''}
        ${r.price_vat_included!=null?`<span><small>Cena vč. DPH</small><b>${money(r.price_vat_included)}</b></span>`:''}
        ${r.contract_number?`<span><small>Číslo smlouvy</small><b>${esc(r.contract_number)}</b></span>`:''}
        ${r.participant_count!=null?`<span><small>Účastníků</small><b>${esc(r.participant_count)}</b></span>`:''}
        ${r.bid_count!=null?`<span><small>Nabídek</small><b>${esc(r.bid_count)}</b></span>`:''}
        ${r.procurement_regime?`<span><small>Režim</small><b>${esc(r.procurement_regime)}</b></span>`:''}
        ${r.procurement_procedure?`<span><small>Postup</small><b>${esc(r.procurement_procedure)}</b></span>`:''}
        ${r.document_count!=null?`<span><small>Dokumentů</small><b>${esc(r.document_count)}</b></span>`:''}
      </div>
      ${r.description?`<p class="meta source-description">${esc(r.description)}</p>`:''}
      ${xmlDocs.length?`<details><summary>Dokumenty z oficiálního PVU XML (${xmlDocs.length})</summary><div class="document-links">${xmlDocs.map((d,j)=>`<a href="${esc(d.url)}" target="_blank" rel="noopener">${esc(d.label||('Dokument '+(j+1)))} →</a>`).join('')}</div></details>`:''}
      <div class="source-actions">
        ${r.source_id?`<span class="meta">ID: ${esc(r.source_id)}</span>`:''}
        ${url?`<a href="${esc(url)}" target="_blank" rel="noopener">Otevřít zdroj →</a>`:''}
      </div>
    </article>`;
  }).join('');
}
function sourceLabel(v){
  return ({'vhodne-uverejneni':'Vhodné uveřejnění','registr-smluv':'Registr smluv'}[v]||v||'Zdroj');
}

async function run(){
  if(!id){root.innerHTML='<div class="empty">Chybí identifikátor zakázky.</div>';return}
  try{
    const p=await fetch(`./data/projects/${encodeURIComponent(id)}.json`).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()});
    let documentAnalysis={documents:[]};
    try{ documentAnalysis=await fetch('./data/documents/analysis.json').then(r=>r.ok?r.json():({documents:[]})); }catch(_){ }
    render(p,documentAnalysis);
  }catch(e){
    console.error(e);
    root.innerHTML='<div class="empty"><strong>Detail se nepodařilo načíst.</strong><br><span class="meta">Záznam nemusí být dostupný nebo došlo k chybě při načtení dat.</span></div>';
  }
}

function render(p,documentAnalysis={documents:[]}){
  const c=p.canonical||{},f=c.financial||{},a=p.analysis||{},events=c.lifecycle?.events||[],ss=p.sources||[];
  const procurement=c.procurement||{}, verification=c.verification||{};
  const analysisFinancial=a.financial||{};
  const suppliers=[...new Map(ss.map(s=>{
    const r=s.record||s,ico=r.supplier_ico||r.ico_dodavatele;
    return ico?[String(ico),{name:r.supplier_name||'Neuvedený název',ico}]:null
  }).filter(Boolean)).values()];
  const declaredAddenda=new Set((procurement.known_addenda_numbers||[]).map(String));
  const addenda=events.filter(e=>e.type==='addendum').length;
  const firstDate=c.dates?.first_observed||events[0]?.date;
  const lastDate=c.dates?.last_observed||events[events.length-1]?.date;
  const change=analysisFinancial.absolute_change ?? (f.latest_observed_price!=null&&f.initial_contract_price!=null?f.latest_observed_price-f.initial_contract_price:null);
  const changePct=analysisFinancial.percent_change ?? (f.initial_contract_price&&change!=null?change/f.initial_contract_price*100:null);
  const sourceCount=c.source_count||ss.length||0;
  const verificationLevels=verification.levels||[];
  const certainty=verificationLevels.length?'Evidence ze zdrojových záznamů':'Omezené ověření';

  root.innerHTML=`
    <header class="detail-head">
      <p class="eyebrow">DETAIL ZÁZNAMU</p>
      <div class="detail-title-row">
        <div>
          <h1>${esc(p.title||c.title)}</h1>
          <div class="badges">
            <span class="badge gold">${esc(statusLabels[p.status]||p.status||'Stav neuveden')}</span>
            <span class="badge">${esc(typeLabels[p.project_type]||p.project_type||'Typ neuveden')}</span>
            ${c.procurement_signal?'<span class="badge green">'+esc(c.procurement_signal.label)+'</span>':''}
          </div>
        </div>
        <div class="detail-id"><small>Projekt</small><code>${esc(p.id||id)}</code></div>
      </div>
    </header>

    <section class="stats detail-stats">
      <div class="stat"><strong>${money(f.initial_contract_price)}</strong><span>výchozí pozorovaná cena bez DPH</span></div>
      <div class="stat"><strong>${money(f.latest_observed_price)}</strong><span>poslední pozorovaná cena bez DPH</span></div>
      <div class="stat"><strong>${addenda||declaredAddenda.size}</strong><span>${addenda?'zachycených':'doložených'} dodatků / změnových záznamů</span></div>
      <div class="stat"><strong>${sourceCount}</strong><span>zdrojových záznamů</span></div>
    </section>

    <nav class="detail-nav">
      <a href="#overview">Přehled</a><a href="#procurement">Zakázka</a><a href="#coverage">Data</a><a href="#provenance">Provenience</a><a href="#finance">Finance</a><a href="#timeline">Časová osa</a><a href="#checks">Kontroly</a><a href="#documents">Dokumenty</a><a href="#sources">Zdroje</a>
    </nav>

    <section id="overview" class="card detail-summary">
      <div>
        <p class="eyebrow dark">RYCHLÝ PŘEHLED</p>
        <h2>Co o záznamu skutečně víme</h2>
        <p>${summaryText(c,p,events)}</p>
      </div>
      <div class="summary-facts">
        <div><small>První pozorování</small><strong>${date(firstDate)}</strong></div>
        <div><small>Poslední pozorování</small><strong>${date(lastDate)}</strong></div>
        <div><small>Úroveň ověření</small><strong>${esc(certainty)}</strong></div>
      </div>
    </section>

    <section id="procurement" class="card">
      <div class="section-title"><div><p class="eyebrow dark">ZADÁNÍ A OVĚŘENÍ</p><h2>Jak je zakázka doložena</h2></div></div>
      <div class="fact-grid">
        ${fact('Režim',procurement.regimes?.join(', '))}
        ${fact('Postup',procurement.procedures?.join(', '))}
        ${fact('Předpokládaná hodnota',f.expected_values?.length?money(f.expected_values[0]):null)}
        ${fact('Identifikátor zakázky',c.identifiers?.join(', '))}
        ${fact('Datum podpisu',contractSignedDate(ss))}
        ${fact('Počet zdrojů',sourceCount)}
      </div>
      ${c.procurement_signal?'<div class="evidence-note"><strong>'+esc(c.procurement_signal.label)+'</strong><span>'+esc(c.procurement_signal.reason)+'</span></div>':''}
      ${declaredAddenda.size?'<div class="evidence-note warning"><strong>Dodatky uvedené ve zdrojovém záznamu</strong><span>Čísla: '+esc([...declaredAddenda].join(', '))+'. Samotné uvedení počtu dodatků zde neznamená, že jsou všechny dodatky samostatně načtené a oceněné.</span></div>':''}
    </section>

    <section class="card">
      <div class="section-title"><div><p class="eyebrow dark">DODAVATEL</p><h2>Kdo je ve zdrojích uveden</h2></div></div>
      ${suppliers.length?`<div class="supplier-list">${suppliers.map(s=>`<div class="supplier"><strong>${esc(s.name)}</strong><span>IČO ${esc(s.ico)}</span></div>`).join('')}</div>`:'<p class="meta">Dodavatel zatím není ve zdrojových datech uveden.</p>'}
    </section>

    <section id="coverage" class="card">
      <div class="section-title"><div><p class="eyebrow dark">ÚPLNOST DAT</p><h2>Co je a není v evidenci</h2></div></div>
      ${coverage(c,p,ss,events,f)}
    </section>

    <section id="provenance" class="card">
      <div class="section-title"><div><p class="eyebrow dark">PROVENIENCE</p><h2>Odkud informace pocházejí</h2></div></div>
      ${provenance(ss,c)}
    </section>

    <section id="finance" class="card">
      <div class="section-title"><div><p class="eyebrow dark">PENÍZE</p><h2>Finanční mapa</h2></div></div>
      ${finance(f,events,change,changePct)}
    </section>

    <section id="timeline" class="card">
      <div class="section-title"><div><p class="eyebrow dark">CHRONOLOGIE</p><h2>Časová osa</h2></div><span>${events.length} událostí</span></div>
      ${timeline(events,ss,documentAnalysis)}
    </section>

    <section id="checks" class="card">
      <div class="section-title"><div><p class="eyebrow dark">KONTROLA</p><h2>Kontrolní signály</h2></div></div>
      <p class="method-note">Signály jsou popisné kontroly dat. Samy o sobě neprokazují pochybení ani nezákonnost.</p>
      ${signals(a.signals||[])}
    </section>

    ${documentsSection(ss,documentAnalysis)}

    <section id="sources" class="card">
      <div class="section-title"><div><p class="eyebrow dark">DOKUMENTACE</p><h2>Zdrojové záznamy</h2></div><span>${sourceCount} ${sourceCount===1?'záznam':'záznamů'}</span></div>
      ${ss.length?sourceRows(ss):'<p class="meta">Zdroje zatím nejsou evidovány.</p>'}
    </section>
    <p class="detail-footnote">Data jsou automaticky skládána z evidovaných zdrojů. Pokud údaj ve zdrojích není, detail ho záměrně nedoplňuje odhadem.</p>
  `;
}
function summaryText(c,p,events){
  const parts=[];
  parts.push(`Záznam je veden jako „${statusLabels[p.status]||p.status||'stav neuveden'}“ a jako „${typeLabels[p.project_type]||p.project_type||'typ neuveden'}“.`);
  if(c.supplier_ico)parts.push(`Ve zdrojích je uveden dodavatel s IČO ${c.supplier_ico}.`);
  if(events.length)parts.push(`Časová osa obsahuje ${events.length} evidované události od ${date(events[0].date)} do ${date(events[events.length-1].date)}.`);
  if(c.procurement_signal?.level==='explicit')parts.push('Zdrojová data obsahují výslovnou vazbu na veřejnou zakázku.');
  else if(c.procurement_signal?.level==='likely')parts.push('Záznam pravděpodobně souvisí se zakázkou, ale zdrojová data sama o sobě nepotvrzují konkrétní postup výběru.');
  return parts.join(' ');
}
function fact(label,value){return value!=null&&value!==''?`<div class="fact"><small>${esc(label)}</small><strong>${esc(value)}</strong></div>`:''}
function contractSignedDate(ss){const d=ss.map(s=>(s.record||s).contract_signed_date).find(Boolean);return d?date(d):null}
function provenance(ss,c){
  const hasVU=ss.some(s=>normalizeSource(s.record?.source||s.source)==='vhodne-uverejneni');
  const hasRS=ss.some(s=>normalizeSource(s.record?.source||s.source)==='registr-smluv');
  const xml=ss.filter(s=>(s.record||s).official_xml_available===true || (s.record||s).verification_level==='official_xml').length;
  const web=ss.filter(s=>(s.record||s).verified_web===true).length;
  const row=(label,yes,note)=>`<div class="provenance-row"><strong>${esc(label)}</strong><span class="badge ${yes?'green':''}">${yes?'Doloženo':'Nenalezeno'}</span><small>${esc(note)}</small></div>`;
  return `<div class="provenance-list">
    ${row('Vhodné uveřejnění',hasVU,'Zdroj zadavatele / profilu veřejných zakázek.')}
    ${row('Registr smluv',hasRS,'V tomto projektu nebyl nalezen odpovídající záznam v načteném registru.')}
    ${row('Oficiální PVU XML',xml>0,`${xml} zdrojový záznam obsahuje metadata z oficiálního XML exportu PVU.`)}
    ${row('Ověření webem',web>0,`${web} zdrojový záznam je označen jako ověřený na webu.`)}
  </div>
  <p class="method-note">„Nenalezeno“ znamená pouze to, že odpovídající údaj nebyl v aktuálně načtených zdrojích nalezen. Neznamená to, že dokument nebo záznam neexistuje.</p>`;
}
function coverage(c,p,ss,events,f){
  const records=ss.map(s=>s.record||s);
  const uniq=(key,normal=v=>String(v||''))=>[...new Set(records.map(r=>r[key]).filter(v=>v!=null&&v!=='').map(normal))];
  const titles=uniq('title');
  const suppliers=uniq('supplier_ico');
  const prices=uniq('price',v=>Number(v).toFixed(2));
  const dates=uniq('date');
  const gaps=[];
  if(!f.expected_values?.length)gaps.push('Předpokládaná hodnota není ve zdrojových datech doložena.');
  if(!c.procurement?.procedures?.length)gaps.push('Konkrétní postup zadání není ve zdrojových datech doložen.');
  if(!c.procurement?.regimes?.length)gaps.push('Zadávací režim není ve zdrojových datech doložen.');
  if(!records.some(r=>r.participant_count!=null))gaps.push('Počet účastníků není ve zdrojových datech doložen.');
  if(!records.some(r=>r.bid_count!=null))gaps.push('Počet nabídek není ve zdrojových datech doložen.');
  if(!records.some(r=>r.award_date))gaps.push('Datum výběru dodavatele není ve zdrojových datech doloženo.');
  const consistency=[];
  consistency.push({label:'Název',value:titles.length<=1?'shoda':`${titles.length} variant`});
  consistency.push({label:'Dodavatel',value:suppliers.length<=1?'shoda':`${suppliers.length} IČO`});
  consistency.push({label:'Cena bez DPH',value:prices.length<=1?'shoda':`${prices.length} hodnot`});
  consistency.push({label:'Datum',value:dates.length<=1?'shoda':`${dates.length} hodnot`});
  return `
    <div class="fact-grid">
      ${fact('Zdrojové záznamy',ss.length)}
      ${fact('Události v časové ose',events.length)}
      ${fact('Varianty názvu',titles.length||0)}
      ${fact('Varianty dodavatele',suppliers.length||0)}
      ${fact('Varianty ceny bez DPH',prices.length||0)}
      ${fact('Úrovně ověření',(c.verification?.levels||[]).join(', ')||null)}
    </div>
    <div class="evidence-note">
      <strong>Shoda mezi zdroji</strong>
      <span>${consistency.map(x=>`${esc(x.label)}: <b>${esc(x.value)}</b>`).join(' · ')}</span>
    </div>
    ${gaps.length?`<div class="evidence-note warning"><strong>Co v dostupných datech chybí</strong><span>${gaps.map(g=>`• ${esc(g)}`).join('<br>')}</span></div>`:'<div class="evidence-note"><strong>Základní pole jsou pokryta.</strong><span>V dostupných zdrojích nebyla nalezena žádná z uvedených mezer.</span></div>'}
  `;
}
function finance(f,es,change,changePct){
  const prices=es.filter(e=>e.price!=null);
  if(!prices.length){
    const vat=f.observed_vat_included_prices||[];
    if(vat.length){
      return `<div class="finance-head"><div><small>Poslední pozorovaná cena vč. DPH</small><strong>${money(vat[vat.length-1])}</strong><span>Cena bez DPH nebyla ve zdrojovém záznamu dostupná.</span></div><div><small>Cena bez DPH</small><strong>—</strong><span>údaj není doložen</span></div></div><p class="meta">Finanční mapa je omezená na hodnotu skutečně uvedenou ve zdroji.</p>`;
    }
    return'<p class="meta">Pro finanční mapu zatím není k dispozici žádná pozorovaná cena.</p>';
  }
  return`<div class="finance-head"><div><small>Rozdíl mezi první a poslední pozorovanou cenou</small><strong>${change==null?'—':money(change)}</strong><span>${changePct==null?'Procentní změnu nelze spolehlivě spočítat.':pct(changePct)}</span></div><div><small>DPH</small><strong>${f.observed_vat_included_prices?.length?money(f.observed_vat_included_prices[f.observed_vat_included_prices.length-1]):'—'}</strong><span>poslední pozorovaná cena vč. DPH</span></div></div>
  <div class="finance-map">${prices.map((e,i)=>`<div class="finance-step"><span>${i===0?'Výchozí':esc(eventLabel(e.type))}</span><strong>${money(e.price)}</strong><small>${date(e.date)}</small>${i?'<em>'+changeMoney(prices[i-1].price,e.price)+'</em>':''}</div>`).join('')}</div>
  <p class="meta">Mapa zobrazuje pouze ceny skutečně nalezené v evidovaných zdrojích. Uvedené částky nejsou samy o sobě účetní závěrkou.</p>`;
}
function changeMoney(a,b){if(a==null)return'';const d=b-a,p=a?d/a*100:null;return`${d>=0?'+':''}${money(d)} ${p==null?'':`(${pct(p)})`}`}
function eventLabel(v){return({tender:'Zakázka',contract:'Smlouva',addendum:'Dodatek',award:'Výběr dodavatele'}[v]||v||'Záznam')}
function timeline(es,ss=[],analysis={documents:[]}){
  if(!es.length)return'<p class="meta">Časová osa zatím nemá dostatek dat.</p>';
  const sources=ss.map(s=>s.record||s);
  const analyzed=analysis?.documents||[];
  return'<div class="timeline">'+es.map((e,i)=>{
    const src=sources.find(s=>(e.source_id&&String(s.source_id)===String(e.source_id)) || (e.source&&normalizeSource(s.source)===normalizeSource(e.source)));
    const docs=src?.xml_documents?.filter(d=>d&&d.url)||[];
    const pdfs=analyzed.filter(d=>(e.source_id&&String(d.source_id)===String(e.source_id)) || (src?.source_url&&d.source_url===src.source_url));
    const evidence=[];
    if(src?.source_url)evidence.push('<a href="'+esc(src.source_url)+'" target="_blank" rel="noopener">zdrojový záznam →</a>');
    if(docs.length)evidence.push('<span>'+docs.length+' dokumenty v XML</span>');
    if(pdfs.length)evidence.push('<span>'+pdfs.length+' analyzované PDF</span>');
    return \`<div class="timeline-item"><div class="timeline-marker"><span>\${i+1}</span></div><div><div class="timeline-top"><strong>\${date(e.date)}</strong><span class="badge">\${esc(eventLabel(e.type))}</span></div><p>\${esc(e.title||'Bez názvu')}\${e.price!=null?' · <strong>'+money(e.price)+'</strong>':''}</p><div class="timeline-evidence">\${e.source?'<span class="meta">'+esc(sourceLabel(e.source))+(e.source_id?' · ID '+esc(e.source_id):'')+'</span>':''}\${evidence.length?evidence.join(' · '):'<span class="meta">Bez přímé vazby na další dokument v načtených datech.</span>'}</div></div></div>\`;
  }).join('')+'</div>';
}
function signals(ss){
  if(!ss.length)return'<div class="clean-state"><strong>Žádný kontrolní signál.</strong><span>V dostupných datech nebyla nalezena definovaná kontrola, která by vyžadovala pozornost.</span></div>';
  return ss.map(s=>`<div class="signal"><div><span class="badge ${s.level==='warning'||s.level==='alert'?'warn':'blue'}">${esc(s.level||'info')}</span> <strong>${esc(s.code||s.type||'kontrola')}</strong></div><p>${esc(s.message||s.description||'')}</p>${s.evidence?.length?`<details><summary>Zobrazit evidenci</summary><pre>${esc(JSON.stringify(s.evidence,null,2))}</pre></details>`:''}</div>`).join('');
}
run();
