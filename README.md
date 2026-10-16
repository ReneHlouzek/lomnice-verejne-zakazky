# Lomnice – veřejné zakázky

Datový archiv a analytický přehled veřejných zakázek, smluv a souvisejících dokumentů města Lomnice nad Popelkou.

Projekt spojuje veřejně dostupná data z profilu zadavatele na Vhodném uveřejnění a z Registru smluv. Uchovává zdrojové záznamy, normalizuje je, vytváří projektové celky a připravuje analytické výstupy pro webovou aplikaci.

- **Profil zadavatele:** https://www.vhodne-uverejneni.cz/profil/mesto-lomnice-nad-popelkou
- **Identifikátor města (IČO):** 00275905
- **Hlavní webové rozhraní:** `site/index.html` (publikované prostřednictvím GitHub Pages)

## Aktuální stav

**Stav ověřený 16. 10. 2026, 06:05 UTC.** Synchronizace [běh 38851400956](https://github.com/ReneHlouzek/lomnice-verejne-zakazky/actions/runs/38851400956) skončila úspěšně; joby `fetch-registr`, `fetch-vu` a `build` mají `success`. Testy v build jobu hlásily **48 passed**. Datový index byl následně vygenerován 16. 10. v 05:06:53 UTC a web byl úspěšně nasazen v [běhu 38854095657](https://github.com/ReneHlouzek/lomnice-verejne-zakazky/actions/runs/38854095657). Počty zůstaly 163 projektových celků, 44 veřejných zakázek, 12 potvrzených vazeb a 0 kandidátů. Další změny extrakce a propojování jsou nyní ve frontě GitHub Actions a jejich testy zatím nejsou potvrzené.

| Ukazatel | Aktuální hodnota |
|---|---:|
| Projektové celky v indexu | 163 |
| Záznamy Registru smluv v přehledu pokrytí | 109 |
| Záznamy Registru smluv načtené do importu | 110 |
| Záznamy Vhodného uveřejnění – seed | 79 |
| Ověřené webové záznamy Vhodného uveřejnění | 48 |
| Veřejné zakázky | 44 |
| Zakázky se změnami | 3 |
| Smlouvy se změnami / dodatky | 16 |
| Smlouvy bez rozpoznané zakázky | 69 |
| Ostatní záznamy | 31 |
| Potvrzené vazby mezi smlouvami a dodatky | 12 |
| Kandidátní vazby čekající na ruční ověření | 0 |

Počty 109 a 110 u Registru smluv popisují různé vrstvy pipeline: přehled pokrytí organizace a počet záznamů načtených do importu. Nejde o zaměnitelné metriky. Stejně tak počet projektových celků není počtem jednotlivých smluv nebo zakázek. Údaje v tabulce odpovídají indexu vygenerovanému 16. 10. 2026 v 05:06:53 UTC.

### Stav propojování smluv a dodatků

Vazby se potvrzují jen při explicitním identifikátoru návazné smlouvy nebo při dostatečně konkrétním čísle smlouvy. Podobnost názvu sama o sobě není důkazem a má vytvářet nanejvýš kandidáta k ruční kontrole.

V posledním vygenerovaném `data/contract_links.json` je **12 potvrzených vazeb** a **0 kandidátů**. Tento výstup pochází z úspěšné synchronizace 16. 10. 2026 v 05:06 UTC; nové změny pro rozpoznání skloňovaných názvů a projektů v textu dodatků zatím čekají na ověření:

- **Karavanové stání:** dodatky č. 1 a 2 jsou propojené se základní smlouvou přes explicitní ID; dodatek č. 3 přes číslo smlouvy.
- **Nájem nebytových prostor pro OOP:** dodatky č. 1 a 2 jsou propojené se základní smlouvou přes explicitní ID.
- **Obnova rybníka Matouš:** dodatek č. 1 je propojený přes explicitní ID.
- **Účelová dotace Libereckému kraji – havárie zdi:** dodatek č. 1 a dodatek č. 2 jsou propojené se základní smlouvou; mezi dodatky je rovněž zaznamenána explicitní návaznost.
- **Košov – obnova vodovodu:** v primárním textu dodatku `32731945` je výslovně uvedeno, že původní smlouva byla uzavřena 11. 12. 2024; tento den odpovídá datu podpisu základní smlouvy `29417636`. Oba dokumenty uvádějí stejný projekt i smluvní strany. Do `scripts/build_contract_links.py` byla doplněna konzervativní kontrola této kombinace (datum z primárního dokumentu + shoda projektu + společné IČO strany) a regresní testy. Vazba je nyní zapsána v `data/contract_links.json` s důkazy `document_original_contract_date=2024-12-11` a `document_project_title_overlap=0.75`; potvrzení vyžaduje také shodu oficiálního IČO smluvní strany.

Relevantní implementace:
- `scripts/import_registr_smluv.py` – import metadat Registru smluv a získávání informací o návazných smlouvách.
- `scripts/build_contract_links.py` – sestavení potvrzených vazeb a kandidátů.
- `data/contract_links.json` – aktuální výsledek pro web.
- `site/project.js` – zobrazení potvrzených vazeb odděleně od kandidátů.
- `tests/test_contract_links.py` a `tests/test_pipeline.py` – regresní testy propojení a pipeline.

Poslední ověřený stav nasazení webu je úspěšný. Před tvrzením, že proběhla nová úplná synchronizace zdrojů nebo že všechny testy prošly v posledním běhu, je nutné ověřit příslušný běh workflow `sync.yml`; úspěšné nasazení webu samo o sobě tuto skutečnost nedokládá.

## Zdroje a datové vrstvy

1. **Sběr dat**
   - `scripts/scrape_vu.py` – získávání dat a exportů z Vhodného uveřejnění.
   - `scripts/import_registr_smluv.py` a `scripts/import_registr_smluv_dump.py` – import dat Registru smluv.
   - `scripts/import_vu_xml.py` – import metadat z XML exportu Vhodného uveřejnění.

2. **Archivace a normalizace**
   - `data/xml/` – archiv XML exportů a manifest.
   - `data/registr_smluv/` – importované záznamy a podklady Registru smluv.
   - `data/sources/` – normalizované zdrojové záznamy rozdělené podle zdroje.
   - `data/documents/` – metadata a dostupný textový obsah dokumentů.
   - `scripts/extract_vu_documents.py`, `scripts/extract_registr_documents.py` a `scripts/analyze_documents.py` – extrakce a analýza dokumentů.
   - `scripts/normalize_sources.py` – sjednocení zdrojových záznamů.
   - `scripts/audit_sources.py` – kontrola pokrytí a úplnosti zdrojů.

3. **Propojování a projektový model**
   - `scripts/resolve_projects.py` – klasifikace záznamů, párování, sestavení projektových celků a audit kandidátních vazeb.
   - `data/projects/` – detailní JSON záznamy jednotlivých projektových celků.
   - `data/link_candidates.json` a `data/resolution_audit.json` – podklady ke kontrole párování a jeho výsledků.

4. **Analýza a index**
   - `scripts/analyze_projects.py` – časové osy, finanční metriky a popisné kontrolní signály.
   - `scripts/build_index.py` – sestavení souhrnného indexu pro web.
   - `data/index.json` – aktuální přehled a souhrnné počty.
   - `data/source_audit.json` – audit zdrojových dat.

5. **Web**
   - `site/index.html`, `site/app.js`, `site/styles.css` – hlavní přehled, filtry a vzhled.
   - `site/project.html`, `site/project.js` – detail projektového celku.
   - `site/radar.html` – doplňkové rozhraní radaru.

## Automatizace

GitHub Actions zajišťují pravidelnou aktualizaci a publikaci:

- `.github/workflows/sync.yml` spouští sběr zdrojů, extrakci dokumentů, normalizaci, audity, párování, analýzu a tvorbu indexu. Plánované spuštění je denně ve 03:17 UTC; workflow lze spustit také ručně.
- `.github/workflows/pages.yml` připravuje a publikuje web na GitHub Pages po relevantních změnách nebo po úspěšné synchronizaci.

Pipeline obsahuje regresní testy v `tests/` a základní validační kontroly, které mají zabránit přepsání platných dat prázdným výstupem zdroje.

## Jak číst výstupy

Systém rozlišuje tři úrovně informací:

- **Zdrojová fakta** – údaje převzaté z veřejného zdroje nebo dokumentu, včetně identifikátorů a odkazů na původ.
- **Výpočty a normalizace** – například sjednocené datum, klasifikace události nebo rozdíl mezi pozorovanými cenami.
- **Kontrolní signály** – upozornění na neúplnost, rozdíly či okolnosti vhodné k ověření.

Kontrolní signál sám o sobě **není důkazem pochybení, nehospodárnosti ani příčinné souvislosti**. Výstupy je nutné ověřovat proti příslušným smlouvám, dodat­kům, zadávacím dokumentům a dalším primárním podkladům.

## Známá omezení a další rozvoj

Aktuální data a kontrola kódu ukazují zejména na tyto oblasti, které je potřeba dále rozvíjet:

- **Vazby dodatků:** implementace už propojuje explicitní návazná ID a konkrétní čísla smluv a zvlášť eviduje kandidáty k ručnímu ověření. V posledním vygenerovaném výstupu je potvrzeno 12 vazeb a 0 kandidátů; další dodatky mohou zůstávat nepropojené, protože zdrojová metadata neobsahují jednoznačný odkaz na základní smlouvu.
- **Úplnost finanční historie:** pokud dodatek není propojen nebo u něj není dostupná cena, časová osa ani výpočet změny nemusí zachycovat úplný vývoj smluvní ceny.
- **Dokumenty:** počet dokumentů deklarovaný zdrojem nemusí odpovídat počtu stažených nebo textově zpracovaných dokumentů. Dostupnost souboru a úspěšná extrakce textu jsou odlišné skutečnosti.
- **Klasifikace:** smlouva z Registru smluv nemusí být veřejnou zakázkou. Typ záznamu, stav zakázky a signál možné souvislosti se zakázkou je proto nutné interpretovat odděleně.
- **Ruční ověření:** kandidátní vazby a nejednoznačné případy vyžadují dohledání v původních dokumentech. Automatické skóre není potvrzením právní ani věcné vazby.

Prioritou dalšího vývoje je spolehlivé hierarchické propojení základních smluv a jejich dodatků, zachování důkazů o každé vazbě, úplnější finanční časová osa a testy proti reálným případům.


## Předání práce pro nový chat – aktuální úkoly

Následující seznam je průběžně aktualizovaný pracovní plán; starší záznamy níže zachovávají auditní historii. Za hotový úkol považuj pouze to, co je potvrzené v datech, primárním dokumentu nebo úspěšném běhu příslušného workflow.

1. **Ověřit nejnovější běh synchronizace.** V GitHub Actions otevřít workflow `.github/workflows/sync.yml`, zkontrolovat poslední běh, jednotlivé joby a testy. Nezaměňovat workflow publikace webu `pages.yml` za synchronizaci zdrojů.
2. **Opravit falešně pozitivní kontrolu přílohy `37367969`.** Aktuálně uložený text už není smlouva T-Mobile/Hodonín ani dokument o Košově. Výpis přílohy obsahuje dodatek na „Obnovu vodovodu v Želechách“, původní smlouvu uzavřenou 25. 6. 2026 a navýšení dotace o 462 151 Kč; to odpovídá základní smlouvě `36197262` (2 133 990 Kč, stejné datum a smluvní strany). Kontrola názvu souboru `Želechy` proti tvaru `Želechách` však dosud hlásí falešný nesoulad. Opravu skloňování a následné propojení podle data, názvu projektu a IČO právě testuje GitHub Actions; do úspěšného běhu zůstává současná vazba nepropojená.
3. **Košov:** vazba `32731945 → 29417636` je doložena primárním textem dodatku, který uvádí datum 11. 12. 2024, projekt obnovy vodovodu v Košově a stejné smluvní strany. Záznam `37367969` patří k jinému projektu — obnově vodovodu v Želechách — a nesmí být do košovského řetězce zařazen.
4. **Prověřit další nepropojené dodatky.** Prioritně projít záznamy `3861664`, `25099803`, `28586216` a `33854349` a jejich možné základní smlouvy. U obecných dotačních smluv existuje více podobných kandidátů, proto automaticky nevytvářet potvrzené vazby jen podle názvu nebo data.
5. **Zlepšit dohledávání důkazů.** Pokud metadata neobsahují návazné ID, ověřit, zda lze z oficiální detailní stránky Registru smluv spolehlivě získat přílohy a extrahovat text. Zaznamenávat zdroj důkazu tak, aby šlo u každé vazby vysvětlit, proč byla potvrzena.
6. **Udržet bezpečné rozlišení jistoty.** Explicitní ID nebo jednoznačné číslo smlouvy může založit potvrzenou vazbu; podobnost názvu zůstává kandidátem k ručnímu ověření. Nepřidávat vazby jen proto, aby počet propojení rostl.
7. **Doplnit regresní testy a ověřit výstupy.** Pro každou změnu přidat test konkrétního případu i test proti falešnému propojení. Spustit `pytest -q tests`, zkontrolovat `data/contract_links.json`, návazné projektové JSON soubory a zobrazení v detailu webu. Poté ověřit výsledek běhu `sync.yml` a následné publikace.
8. **Po dokončení aktualizovat tento README.** Uvést nové počty, konkrétní potvrzené vazby, otevřené kandidáty, výsledek testů a identifikátor/čas běhu workflow. Neuvádět jako hotové kroky, které byly pouze navrženy.

**Výchozí bod pro pokračování k 16. 10. 2026:** poslední ověřená synchronizace 38851400956 a nasazení 38854095657 uspěly; výstup stále obsahuje 12 potvrzených vazeb. Text přílohy `37367969` jednoznačně popisuje Želechy a odkazuje na původní smlouvu ze dne 25. 6. 2026, tedy na základní smlouvu `36197262`. Pracovní změny nyní: povolit české skloňování při kontrole názvu souboru, využít název projektu výslovně uvedený v textu dodatku a vyžadovat současně shodu data, významného překryvu projektu a oficiálního IČO. Poslední změny kódu a testů čekají na ověření GitHub Actions; po úspěšném běhu aktualizovat počty vazeb. Dále prověřit `3861664`, `25099803`, `28586216` a `33854349`.

## Testy a lokální spuštění

Projekt používá Python. Základní regresní testy lze spustit z kořene repozitáře:

```bash
python -m pip install requests beautifulsoup4 pypdf pytest
pytest -q tests
```

Hlavní kroky datového sestavení odpovídají pořadí ve workflow `sync.yml`. Při ručním spuštění je vhodné nejprve pracovat s kopií dat a ověřit výsledky auditů před nahrazením publikovaných výstupů.

## Zásada transparentnosti

Každý významný údaj a analytický signál má být dohledatelný ke zdrojovému záznamu, dokumentu nebo reprodukovatelnému výpočtu. Cílem je srozumitelný a kontrolovatelný archiv veřejných informací, nikoli automatické vynášení závěrů o jednotlivých smlouvách či osobách.


## Průběžný audit – 16. 10. 2026, 04:35 UTC

- **Synchronizace a testy potvrzeny:** [běh #335](https://github.com/ReneHlouzek/lomnice-verejne-zakazky/actions/runs/38789033050) skončil úspěšně. Joby `fetch-vu`, `fetch-registr` i `build` mají `success`. `pytest -q tests` prošel v obou testovacích jobech: 48 testů v importním jobu a 48 v build jobu. Následná publikace webu [#177](https://github.com/ReneHlouzek/lomnice-verejne-zakazky/actions/runs/38796827060) také uspěla.
- **Aktuální výstupy:** index vygenerován 15. 10. v 19:47:59 UTC; 163 projektových celků, 44 zakázek, 3 zakázky se změnami, 16 smluv se změnami, 69 smluv bez rozpoznané zakázky, 31 ostatních záznamů. `data/contract_links.json` má 12 potvrzených vazeb a 0 kandidátů. Manifest dokumentů eviduje 117 příloh a 112 textů; v běhu bylo staženo 15 dokumentů.
- **Příloha `37367969` – starý chybný text odstraněn, rozpor ale trvá.** Nový běh stáhl z oficiální URL [přílohu záznamu](https://smlouvy.gov.cz/smlouva/39741021) a nahradil předchozí text o T-Mobile/Hodonín. Nový text popisuje dodatek k dotaci na „Košov, obnova vodovodu“ a smluvní strany Město Lomnice nad Popelkou a Vodohospodářské sdružení Turnov. Soubor je však pojmenován `Želechy - Dodatek č. 1.docx`, proto manifest správně ponechává `content_mismatch_review`. Příloha není použita jako důkaz pro propojování; nutné je rozhodnout, zda je špatně pojmenovaná, nebo připojená k nesprávnému záznamu.
- **Košov `32731945 → 29417636`:** potvrzeno z primárního textu dodatku `32731945`, který výslovně uvádí původní smlouvu uzavřenou 11. 12. 2024, projekt Košov – obnova vodovodu a obě smluvní strany. Tato vazba nezávisí na problematické příloze `37367969`.
- **Další krok:** vyřešit nesoulad přílohy `37367969` bez odstranění bezpečnostní karantény na základě pouhé podobnosti názvu či projektu; poté prověřit nepropojené dodatky `3861664`, `25099803`, `28586216` a `33854349`. U každé nové vazby zachovat konkrétní doklad a test proti falešnému propojení.

---
## Průběžný audit při navázání práce – 9. 10. 2026, 06:23 UTC

Tento záznam doplňuje předávací plán; nejde o potvrzení dokončení celé synchronizace ani všech navazujících úkolů.

- **Stav synchronizace:** poslední nalezený datový commit je `be0cf221325a0532373715187faaf2e2c93c7cb5` z 9. 10. 2026 v 06:13:01 UTC. Následný commit s předáním práce je `f5a501eab455d784ddbae5b8f4b1b97cb26c5509` z 06:22:07 UTC. Samotné commity nepotvrzují výsledek všech jobů workflow `sync.yml`; stav běhu je třeba ještě ověřit v GitHub Actions.
- **Dokument `37367969`: potvrzený nesoulad obsahu a názvu přílohy.** Manifest `data/documents/registr-smluv/manifest.json` označuje přílohu `Želechy - Dodatek č. 1.docx` jako `content_mismatch_review`. Archivovaný text `data/documents/registr-smluv/37367969/001.txt` začíná smlouvou T-Mobile a Města Hodonín a uvádí katastrální území Hodonín. To není důkaz, že dokument patří k záznamu v Lomnici; text se nesmí používat jako důkaz pro propojení lomnických smluv. Zatím je zachována auditní stopa a příznak kontroly, nikoli potvrzení správnosti přílohy. Oficiální záznam: https://smlouvy.gov.cz/smlouva/39741021
- **Košov – obnova vodovodu:** oficiální záznam základní smlouvy je [ID 29417636, verze 31432352](https://smlouvy.gov.cz/smlouva/31432352), uzavřená 11. 12. 2024, zveřejněná 16. 12. 2024, hodnota 2 880 000 Kč bez DPH. Oficiální záznam dodatku je [ID 32731945, verze 34905225](https://smlouvy.gov.cz/smlouva/34905225), uzavřený 22. 9. 2025, zveřejněný 23. 9. 2025, hodnota 1 323 950,25 Kč bez DPH. Oba záznamy uvádějí Vodohospodářské sdružení Turnov jako publikující subjekt, Město Lomnice nad Popelkou jako smluvní stranu a výslovně se týkají Košova a obnovy vodovodu. Oficiální stránky nyní potvrzují konkrétní přílohy: [základní smlouva – LOM_PD_Veřejnoprávní s. in. dotace.doc](https://smlouvy.gov.cz/smlouva/soubor/38388380/LOM_PD_Ve%C5%99ejnopr%C3%A1vn%C3%AD%20s.%20in.%20dotace.doc) a [dodatek – Dodatek č. 1 k veřejnoprávní smlouvě.doc](https://smlouvy.gov.cz/smlouva/soubor/42395429/Dodatek%20%C4%8D.%201%20k%20ve%C5%99ejnopr%C3%A1vn%C3%AD%20smlouv%C4%9B.doc). Metadata dodatku přesto uvádějí prázdné pole „ID návazné smlouvy“, proto vazba zůstává kandidátem do extrakce a kontroly textu dodatku.
- **Další záznam `37367969` není doložen jako součást řetězce Košov.** Jeho obecný název sám nestačí a příloha vykazuje výše popsaný nesoulad. Nepoužívat jej jako důkaz pro Košov.
- **Další krok:** nejprve ověřit poslední běh `sync.yml` a jeho testy v GitHub Actions; pak dohledat a získat oficiální přílohy pro oba záznamy Košov, ověřit text dodatku a jeho návaznost. Poté pokračovat záznamy `3861664`, `25099803`, `28586216` a `33854349`. Po změnách spustit `pytest -q tests`, ověřit výsledné JSON soubory a teprve pak aktualizovat potvrzené počty.


## Průběžný audit – 9. 10. 2026, 09:40 UTC

- **Synchronizace potvrzena:** [běh 37900330296](https://github.com/ReneHlouzek/lomnice-verejne-zakazky/actions/runs/37900330296) skončil úspěšně. Joby `fetch-vu`, `fetch-registr` i `build` mají `success`. Regresní testy prošly: 35 testů v importním jobu a následně znovu v build jobu.
- **Historický import není kompletní:** `data/registr_smluv/manifest.json` uvádí `filter_version=city-party-v2`, 110 záznamů, 38 zpracovaných dumpů z 124 a `history_complete=false`. V tomto běhu se zpracovalo 36 historických měsíců od 2016-07 do 2019-06 a obnovily se 2026-09 a 2026-10. Zbývající historie se musí doplnit dalšími běhy; úspěch workflow neznamená dokončenou historii.
- **Propojování smluv:** `data/contract_links.json` nyní obsahuje 11 potvrzených vazeb a 1 kandidáta. Košov zůstává kandidátem `32731945 → 29417636`; vazbu nepovyšovat pouze na základě podobnosti názvů.
- **Audit příloh:** manifest obsahuje 44 deklarovaných a objevených příloh, 40 stažených souborů a 38 extrahovaných textů. U záznamu `37367969` je příloha s názvem Želechy stále označená `content_mismatch_review`; archivovaný text se týká Hodonína a T-Mobile. Není přípustné použít tento text jako důkaz pro smlouvu v Lomnici.
- **Oprava extrakce starých Word dokumentů:** u záznamu `3861664` selhala extrakce souboru `.doc`, protože v runneru nebyl nainstalovaný `antiword`. Doplnil jsem fallback na LibreOffice a instalaci obou převodníků do build jobu. Regresní test ověřuje fallback při chybějícím `antiword`; jeho výsledek bude potvrzen následujícím během workflow.
- **Další kroky:** ověřit novou synchronizaci a extrakci dokumentů po této opravě; zkontrolovat, zda se text pro `3861664` podařilo získat; pak dohledat primární dokumenty pro Košov (`29417636`, `32731945`) a pokračovat dalšími nepropojenými dodatky (`25099803`, `28586216`, `33854349`). Po každém běhu aktualizovat počty jen podle aktuálních dat.


## Aktualizace – 9. 10. 2026, 11:10 UTC

- **Extrakce `.doc`:** oprava z commitu `282ac53` je ověřena na reálném souboru `3861664`; text se extrahoval úspěšně. Nový test pokrývá i fallback na LibreOffice.
- **Košov – doplněné primární soubory:** do `data/registr_smluv/contracts.json` jsem doplnil přesné odkazy na oficiální přílohu základní smlouvy (`29417636`, verze `31432352`) a dodatku (`32731945`, verze `34905225`). Zdrojem jsou oficiální stránky Registru smluv; obě přílohy jsou ve formátu `.doc`. Import nově zachová tyto ověřené odkazy, pokud XML obnoví stejnou verzi bez URL přílohy, a z detailní stránky získává přílohy různých podporovaných formátů.
- **Opatrnost při propojování:** metadata dodatku stále nemají vyplněné „ID návazné smlouvy“. Vazba Košov zůstává kandidátem, dokud nebude prohlédnut extrahovaný text dodatku; pouhá shoda názvu nestačí.
- **Historický import:** dávku jsem snížil z 36 na 12 měsíců, protože dlouhý běh se blížil limitu jobu. Poslední uložený stav je 64 zpracovaných dumpů z 124 a `history_complete=false`. Další synchronizace má pokračovat od nejstaršího nezpracovaného měsíce.
- **Kontrola příloh:** záznam `37367969` zůstává `content_mismatch_review`; nesoulad názvu Želechy a obsahu je nevyřešený a nesmí být považován za důkaz pro tento projekt.

## Předání práce – 12. 10. 2026

- **Poslední ověřená synchronizace:** běh [#308](https://github.com/ReneHlouzek/lomnice-verejne-zakazky/actions/runs/38130332993) skončil úspěšně 11. 10. 2026. Historický import ale není kompletní: 100/124 dumpů, `history_complete=false`.
- **Přílohy:** manifest aktualizovaný 11. 10. 2026 uvádí 110 záznamů zkontrolovaných, 92 příloh deklarovaných/objevených, 23 souborů stažených a 87 textů extrahovaných. Extrahovaný text `3861664` je k dispozici.
- **Nová oprava pro vazby:** u dodatku Košov `32731945` obsah primárního dokumentu odkazuje na původní smlouvu uzavřenou 11. 12. 2024, což odpovídá základní smlouvě `29417636`. Doplněna kontrola, která vyžaduje současně shodu data původní smlouvy, významného překryvu názvu projektu a alespoň jednoho společného oficiálního IČO. Doplňující regresní testy pokrývají pozitivní i negativní případ.
- **Co udělat dál, v tomto pořadí:**
  1. Ověřit výsledek nového běhu `sync.yml` spuštěného změnou kódu: oba joby s testy musí projít; zkontrolovat, že Košov `32731945` → `29417636` přibyl mezi potvrzené vazby a v `evidence` má `document_original_contract_date=2024-12-11`.
  2. Zkontrolovat, zda se do `data/documents/registr-smluv/manifest.json` dostaly nové či chybějící přílohy. Zejména `28586216` a `33854349` zatím nemají v aktuálním manifestu extrahovaný text; `25099803` text má, ale jeho rodičovská smlouva ještě není doložena.
  3. Projít texty `25099803`, `28586216` a `33854349` a potvrzovat vztahy jen z explicitního ID, čísla smlouvy nebo jednoznačné identifikace původní smlouvy v dokumentu. Obecný název „dodatek k veřejnoprávní smlouvě“ nestačí.
  4. Zachovat `37367969` jako případ s `content_mismatch_review`; archivovaný text přílohy se týká Hodonína/T-Mobile a nesmí být použit jako důkaz pro lomnický projekt, dokud se nezíská správná příloha.
  5. Pokračovat v historickém importu Registru smluv, dokud manifest nepotvrdí všech 124 dumpů; po každém běhu zaznamenat skutečný počet a stav, ne odvozovat dokončení pouze z úspěšného workflow.
  6. Po ověření výstupů aktualizovat tabulku aktuálního stavu a tento předávací blok. Nezaměňovat úspěšné nasazení webu za úspěšnou synchronizaci dat.


## Průběžný audit – 12. 10. 2026, 20:30 UTC

- **Zjištěná chyba workflow:** běh [#38297227184](https://github.com/ReneHlouzek/lomnice-verejne-zakazky/actions/runs/38297227184) selhal v obou testovacích jobech na testu `test_document_original_contract_date_is_extracted_from_text` (41 passed, 1 failed). Test odhalil, že regulární výraz nepokrýval tvar „smlouvě“. Oprava v `scripts/build_contract_links.py` je v commitu `3c373849a6f6c1070b0018bace1d6e026ad2c403`; po pushi ověřit nový běh a nepovažovat chybu za vyřešenou, dokud testy neprojdou.
- **Poslední úspěšná synchronizace:** [#38238628126](https://github.com/ReneHlouzek/lomnice-verejne-zakazky/actions/runs/38238628126), úspěch 12. 10. 2026 v 11:53 UTC. Manifest Registru smluv hlásí 110 záznamů a `history_complete=true`.
- **Vazby:** aktuálně uložený `data/contract_links.json` má 12 potvrzených vazeb a 0 kandidátů. Vazba Košov `32731945` → `29417636` má důkazy `document_original_contract_date=2024-12-11` a `document_project_title_overlap=0.75`; sdílená identita smluvní strany se ověřuje z oficiálních IČO. Výstup bude znovu přepočítán až v úspěšném běhu po opravě.
- **Dokumenty:** manifest `data/documents/registr-smluv/manifest.json` uvádí 117 objevených příloh a 112 dostupných textů. Dokumenty `25099803` a `28586216` výslovně uvádějí původní investiční dotační smlouvu uzavřenou 22. 9. 2023 a projekt „Obnova vodovodu a kanalizace Jilemnická ulice“; záznam `33854349` odkazuje na smlouvu uzavřenou 5. 5. 2025 pro projekt BM 8. Následná synchronizace má ověřit, zda jsou příslušné základní smlouvy dostupné a zda je propojí důkaz data + projektu + IČO.
- **Další kroky:** (1) ověřit nový běh `sync.yml` a testy; (2) zkontrolovat nové `data/contract_links.json` a projekty; (3) ověřit vztahy dodatků `25099803`, `28586216` a `33854349` k odpovídajícím základním smlouvám; (4) zachovat `37367969` jako `content_mismatch_review`, protože jeho archivovaný text se týká Hodonína/T-Mobile; (5) až po úspěšném běhu aktualizovat čísla a datum stavu v tomto README.


## Průběžný audit a předání – 15. 10. 2026, 17:40 UTC

- **Synchronizace:** [běh #319 / 38704625526](https://github.com/ReneHlouzek/lomnice-verejne-zakazky/actions/runs/38704625526) dokončen 15. 10. 2026 v 08:45:06 UTC se stavem `success`. Joby `fetch-registr`, `fetch-vu` a `build` jsou úspěšné. Starší selhání testu extrakce data smlouvy z 12. 10. je překonáno úspěšným navazujícím během.
- **Aktuální datové výstupy:** `data/index.json` byl vytvořen 15. 10. v 08:45:01 UTC; uvádí 163 projektových celků, 44 veřejných zakázek, 3 zakázky se změnami, 16 smluv se změnami, 69 smluv bez rozpoznané zakázky a 31 ostatních záznamů. Přehled pokrytí obsahuje 109 záznamů Registru smluv; import načetl 110 záznamů. Nejde o zaměnitelné počty.
- **Registr smluv:** `data/registr_smluv/manifest.json` byl aktualizován 15. 10. v 08:27 UTC; uvádí 110 záznamů a `history_complete=true` pro 124 historických dumpů.
- **Přílohy:** `data/documents/registr-smluv/manifest.json` byl aktualizován 15. 10. v 08:44:45 UTC: 110 záznamů zkontrolováno, 117 příloh deklarováno a objeveno, 5 dokumentů staženo v tomto běhu a 112 textů je dostupných. Záznam `37367969` a jeho nesoulad přílohy s textem je stále nutné považovat za kontrolní problém; jeho text nesmí být použit jako důkaz pro lomnickou smlouvu, dokud nebude ověřena správná příloha.
- **Vazby smluv:** `data/contract_links.json` obsahuje 12 potvrzených vazeb a 0 kandidátů. Košov `32731945` → `29417636` je potvrzen přes datum původní smlouvy 11. 12. 2024, shodu projektu a ověření společného oficiálního IČO. Další zapsané vazby zahrnují karavanové stání (dodatky 1–3), nájem nebytových prostor pro OOP (dodatky 1–2), obnovu rybníka Matouš, dotaci Libereckému kraji na havárii zdi (smlouvu a dodatky 1–2) a další explicitní návaznosti dotačních smluv.
- **Další postup:**
  1. Prověřit, zda jsou všechny potvrzené vazby věcně správné a jejich důkazy dostatečně konkrétní; zejména zachovat testy proti falešnému propojení na základě podobných názvů.
  2. Prověřit nepropojené dodatky a jejich texty v manifestu; u každého hledat explicitní ID, číslo smlouvy nebo kombinaci data původní smlouvy, názvu projektu a oficiálního IČO. Pokud důkaz chybí, nepřidávat automaticky potvrzenou vazbu.
  3. Vyřešit přílohu `37367969` označenou jako nesoulad obsahu a názvu: dohledat správný soubor z oficiálního Registru smluv, nebo případ jasně ponechat jako neověřený.
  4. Zkontrolovat aktuální webový detail projektu a zda se všech 12 vazeb zobrazuje srozumitelně; interní technické názvy důvodů vazby by neměly být matoucí pro běžného uživatele.
  5. Při další změně spustit `pytest -q tests`, ověřit všechny joby `sync.yml`, porovnat nově vytvořené JSON soubory a následně aktualizovat tento README. Úspěšné nasazení `pages.yml` samo o sobě není důkazem úspěšné synchronizace.
