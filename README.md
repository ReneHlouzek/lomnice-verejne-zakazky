# Lomnice – veřejné zakázky

Datový archiv a analytický přehled veřejných zakázek, smluv a souvisejících dokumentů města Lomnice nad Popelkou.

Projekt spojuje veřejně dostupná data z profilu zadavatele na Vhodném uveřejnění a z Registru smluv. Uchovává zdrojové záznamy, normalizuje je, vytváří projektové celky a připravuje analytické výstupy pro webovou aplikaci.

- **Profil zadavatele:** https://www.vhodne-uverejneni.cz/profil/mesto-lomnice-nad-popelkou
- **Identifikátor města (IČO):** 00275905
- **Hlavní webové rozhraní:** `site/index.html` (publikované prostřednictvím GitHub Pages)

## Aktuální stav

Projekt již není ve fázi založení infrastruktury. Obsahuje funkční datovou a analytickou pipeline, archiv zdrojových záznamů, projektové JSON výstupy, kontrolní audity, webové rozhraní a automatizované workflow GitHub Actions.

Poslední kontrolovaný index byl vytvořen **1. 10. 2026**. V tomto snapshotu obsahuje:

| Ukazatel | Hodnota |
|---|---:|
| Projektové celky v indexu | 162 |
| Záznamy z Registru smluv | 109 |
| Záznamy Vhodného uveřejnění – seed | 79 |
| Ověřené webové záznamy Vhodného uveřejnění | 48 |
| Veřejné zakázky | 44 |
| Zakázky se změnami | 3 |
| Smlouvy se změnami | 15 |
| Smlouvy | 69 |
| Ostatní záznamy | 31 |

Počty zdrojových záznamů a projektových celků nejsou zaměnitelné. Záznamy z různých zdrojů se mohou týkat stejného případu a některé smlouvy či dodatky zatím zůstávají samostatně. Referenční počty na zdrojových portálech se mohou měnit; nejsou automaticky totožné s počty stažených, ověřených ani deduplikovaných záznamů.

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

- **Vazby dodatků:** část dodatků z Registru smluv je zatím vedena jako samostatný projektový celek. Resolver dnes obecně odděluje záznamy pocházející ze stejného zdroje; zvláštní výjimka pokrývá přesné propojení zadání a výsledné smlouvy, nikoli všechny typy dodatků.
- **Úplnost finanční historie:** pokud dodatek není propojen nebo u něj není dostupná cena, časová osa ani výpočet změny nemusí zachycovat úplný vývoj smluvní ceny.
- **Dokumenty:** počet dokumentů deklarovaný zdrojem nemusí odpovídat počtu stažených nebo textově zpracovaných dokumentů. Dostupnost souboru a úspěšná extrakce textu jsou odlišné skutečnosti.
- **Klasifikace:** smlouva z Registru smluv nemusí být veřejnou zakázkou. Typ záznamu, stav zakázky a signál možné souvislosti se zakázkou je proto nutné interpretovat odděleně.
- **Ruční ověření:** kandidátní vazby a nejednoznačné případy vyžadují dohledání v původních dokumentech. Automatické skóre není potvrzením právní ani věcné vazby.

Prioritou dalšího vývoje je spolehlivé hierarchické propojení základních smluv a jejich dodatků, zachování důkazů o každé vazbě, úplnější finanční časová osa a testy proti reálným případům.

## Testy a lokální spuštění

Projekt používá Python. Základní regresní testy lze spustit z kořene repozitáře:

```bash
python -m pip install requests beautifulsoup4 pypdf pytest
pytest -q tests
```

Hlavní kroky datového sestavení odpovídají pořadí ve workflow `sync.yml`. Při ručním spuštění je vhodné nejprve pracovat s kopií dat a ověřit výsledky auditů před nahrazením publikovaných výstupů.

## Zásada transparentnosti

Každý významný údaj a analytický signál má být dohledatelný ke zdrojovému záznamu, dokumentu nebo reprodukovatelnému výpočtu. Cílem je srozumitelný a kontrolovatelný archiv veřejných informací, nikoli automatické vynášení závěrů o jednotlivých smlouvách či osobách.
