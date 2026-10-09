# Lomnice – veřejné zakázky

Datový archiv a analytický přehled veřejných zakázek, smluv a souvisejících dokumentů města Lomnice nad Popelkou.

Projekt spojuje veřejně dostupná data z profilu zadavatele na Vhodném uveřejnění a z Registru smluv. Uchovává zdrojové záznamy, normalizuje je, vytváří projektové celky a připravuje analytické výstupy pro webovou aplikaci.

- **Profil zadavatele:** https://www.vhodne-uverejneni.cz/profil/mesto-lomnice-nad-popelkou
- **Identifikátor města (IČO):** 00275905
- **Hlavní webové rozhraní:** `site/index.html` (publikované prostřednictvím GitHub Pages)

## Aktuální stav

**Stav ověřený 9. 10. 2026 v 11:10 UTC.** Oprava extrakce starých dokumentů Word je v commitu `282ac53`; regresní testy v navazujícím běhu prošly a u záznamu `3861664` už je extrahovaný text (6 034 znaků). Nejnovější uložený manifest Registru smluv eviduje 64 zpracovaných dumpů a `history_complete=false`; historický import pokračuje po menších dávkách. Aktuální synchronizace může být při nasazení nové opravy nahrazena novým během.

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
| Potvrzené vazby mezi smlouvami a dodatky | 11 |
| Kandidátní vazby čekající na ruční ověření | 1 |

Počty 109 a 110 u Registru smluv popisují různé vrstvy pipeline: přehled pokrytí organizace a počet záznamů načtených do importu. Nejde o zaměnitelné metriky. Stejně tak počet projektových celků není počtem jednotlivých smluv nebo zakázek.

### Stav propojování smluv a dodatků

Vazby se potvrzují jen při explicitním identifikátoru návazné smlouvy nebo při dostatečně konkrétním čísle smlouvy. Podobnost názvu sama o sobě není důkazem a má vytvářet nanejvýš kandidáta k ruční kontrole.

Aktuálně je v `data/contract_links.json` **11 potvrzených vazeb** a **1 kandidát**:

- **Karavanové stání:** dodatky č. 1 a 2 jsou propojené se základní smlouvou přes explicitní ID; dodatek č. 3 přes číslo smlouvy.
- **Nájem nebytových prostor pro OOP:** dodatky č. 1 a 2 jsou propojené se základní smlouvou přes explicitní ID.
- **Obnova rybníka Matouš:** dodatek č. 1 je propojený přes explicitní ID.
- **Účelová dotace Libereckému kraji – havárie zdi:** dodatek č. 1 a dodatek č. 2 jsou propojené se základní smlouvou; mezi dodatky je rovněž zaznamenána explicitní návaznost.
- **Košov – obnova vodovodu:** záznam dodatku č. 1 (ID Registru smluv `32731945`) je pouze kandidátem vůči základní smlouvě `29417636`. Shoduje se název projektu, ale důkaz zatím stojí jen na názvu; vazbu **nepovyšovat na potvrzenou bez kontroly primárního dokumentu nebo metadat Registru smluv**.

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

- **Vazby dodatků:** implementace už propojuje explicitní návazná ID a konkrétní čísla smluv a zvlášť eviduje kandidáty k ručnímu ověření. Přesto je potvrzeno jen 9 vazeb; řada dodatků zůstává nepropojena, protože zdrojová metadata neobsahují jednoznačný odkaz na základní smlouvu.
- **Úplnost finanční historie:** pokud dodatek není propojen nebo u něj není dostupná cena, časová osa ani výpočet změny nemusí zachycovat úplný vývoj smluvní ceny.
- **Dokumenty:** počet dokumentů deklarovaný zdrojem nemusí odpovídat počtu stažených nebo textově zpracovaných dokumentů. Dostupnost souboru a úspěšná extrakce textu jsou odlišné skutečnosti.
- **Klasifikace:** smlouva z Registru smluv nemusí být veřejnou zakázkou. Typ záznamu, stav zakázky a signál možné souvislosti se zakázkou je proto nutné interpretovat odděleně.
- **Ruční ověření:** kandidátní vazby a nejednoznačné případy vyžadují dohledání v původních dokumentech. Automatické skóre není potvrzením právní ani věcné vazby.

Prioritou dalšího vývoje je spolehlivé hierarchické propojení základních smluv a jejich dodatků, zachování důkazů o každé vazbě, úplnější finanční časová osa a testy proti reálným případům.


## Předání práce pro nový chat – aktuální úkoly

Následující seznam je pracovní plán navázaný na stav k 9. 10. 2026. Za hotový úkol považuj pouze to, co je potvrzené v datech, primárním dokumentu nebo úspěšném běhu příslušného workflow.

1. **Ověřit nejnovější běh synchronizace.** V GitHub Actions otevřít workflow `.github/workflows/sync.yml`, zkontrolovat poslední běh, jednotlivé joby a testy. Nezaměňovat workflow publikace webu `pages.yml` za synchronizaci zdrojů.
2. **Prověřit archiv textů dokumentů.** Zkontrolovat `data/documents/registr-smluv/`, manifesty a vazbu každého textu na ID zdrojového záznamu. V dosud nalezeném archivu je soubor `data/documents/registr-smluv/37367969/001.txt`; jeho obsah se podle rychlé kontroly týká smlouvy T-Mobile v Hodoníně, nikoli zjevně případu v Lomnici. Ověřit proto, zda jde o správně přiřazenou přílohu, a zkontrolovat filtr i párování dokumentů se zdrojovými ID.
3. **Pokračovat od dodatku Košov – obnova vodovodu.** Prověřit záznamy `32731945` a `29417636` v oficiálním Registru smluv, jejich dostupné přílohy a metadata. Zjistit také, zda další záznamy ke Košovu, včetně `37367969`, věcně patří k témuž smluvnímu řetězci. Vazbu potvrdit pouze na základě konkrétního dokladu; samotná podobnost názvů nestačí.
4. **Prověřit další nepropojené dodatky.** Prioritně projít záznamy `3861664`, `25099803`, `28586216` a `33854349` a jejich možné základní smlouvy. U obecných dotačních smluv existuje více podobných kandidátů, proto automaticky nevytvářet potvrzené vazby jen podle názvu nebo data.
5. **Zlepšit dohledávání důkazů.** Pokud metadata neobsahují návazné ID, ověřit, zda lze z oficiální detailní stránky Registru smluv spolehlivě získat přílohy a extrahovat text. Zaznamenávat zdroj důkazu tak, aby šlo u každé vazby vysvětlit, proč byla potvrzena.
6. **Udržet bezpečné rozlišení jistoty.** Explicitní ID nebo jednoznačné číslo smlouvy může založit potvrzenou vazbu; podobnost názvu zůstává kandidátem k ručnímu ověření. Nepřidávat vazby jen proto, aby počet propojení rostl.
7. **Doplnit regresní testy a ověřit výstupy.** Pro každou změnu přidat test konkrétního případu i test proti falešnému propojení. Spustit `pytest -q tests`, zkontrolovat `data/contract_links.json`, návazné projektové JSON soubory a zobrazení v detailu webu. Poté ověřit výsledek běhu `sync.yml` a následné publikace.
8. **Po dokončení aktualizovat tento README.** Uvést nové počty, konkrétní potvrzené vazby, otevřené kandidáty, výsledek testů a identifikátor/čas běhu workflow. Neuvádět jako hotové kroky, které byly pouze navrženy.

**Výchozí bod pro pokračování:** `data/contract_links.json` má 9 potvrzených vazeb a 1 kandidáta (`32731945` → `29417636`). Další prioritou není bezhlavě zvyšovat počet vazeb, ale ověřit dostupnost a správné přiřazení dokumentů a dohledat důkaz pro jednotlivé dosud nepropojené dodatky.

## Testy a lokální spuštění

Projekt používá Python. Základní regresní testy lze spustit z kořene repozitáře:

```bash
python -m pip install requests beautifulsoup4 pypdf pytest
pytest -q tests
```

Hlavní kroky datového sestavení odpovídají pořadí ve workflow `sync.yml`. Při ručním spuštění je vhodné nejprve pracovat s kopií dat a ověřit výsledky auditů před nahrazením publikovaných výstupů.

## Zásada transparentnosti

Každý významný údaj a analytický signál má být dohledatelný ke zdrojovému záznamu, dokumentu nebo reprodukovatelnému výpočtu. Cílem je srozumitelný a kontrolovatelný archiv veřejných informací, nikoli automatické vynášení závěrů o jednotlivých smlouvách či osobách.


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
