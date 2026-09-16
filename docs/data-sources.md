# Oficiální zdroje dat

Projekt používá více zdrojů a žádný jednotlivý zdroj není považován za jediný autoritativní záznam celé životní historie zakázky.

## 1. Profil zadavatele / Vhodné uveřejnění

Primární zdroj dokumentů a informací zveřejněných na profilu zadavatele Města Lomnice nad Popelkou.

- Zadavatel: Město Lomnice nad Popelkou
- IČO: 00275905
- Profil: https://www.vhodne-uverejneni.cz/profil/mesto-lomnice-nad-popelkou
- Profil je veden jako elektronický nástroj/profil zadavatele.
- Strukturovaná data profilu mají být poskytována ve stanovené XML struktuře.

## 2. Věstník veřejných zakázek (VVZ)

VVZ obsahuje formuláře k veřejným zakázkám, zejména oznámení o zahájení, výsledku, opravách a změnách závazku ze smlouvy. U nadlimitních zakázek existuje návaznost na evropský TED.

- VVZ: https://vvz.nipez.cz/
- Pro projekt je důležitý zejména identifikátor/evidenční číslo zakázky a vazby mezi navazujícími formuláři.

## 3. Registr veřejných zakázek (RVZ / NIPEZ)

RVZ je centrální komponenta NIPEZ určená k uchovávání a výdeji dat o veřejných zakázkách. Podle dokumentace MMR slouží také k publikaci otevřených dat. RVZ ale nemá vlastní veřejnou webovou stránku; proto ho nelze automaticky považovat za jednoduchou náhradu profilu zadavatele.

## 4. Registr smluv

Registr smluv používáme jako samostatný zdroj skutečně zveřejněných smluv a jejich metadat/příloh.

- Registr smluv: https://smlouvy.gov.cz/
- IČO města: 00275905
- Důležitá vazba: evidenční číslo zakázky z VVZ, pokud je u smlouvy uvedeno.

## 5. Město Lomnice nad Popelkou

Později doplníme veřejné zdroje města, zejména:

- usnesení rady města,
- usnesení zastupitelstva,
- rozpočty a rozpočtová opatření,
- zveřejněné objednávky,
- další dokumenty související s konkrétní investicí.

## Princip propojení

Zakázka se nebude identifikovat pouze názvem. Resolver bude používat kombinaci:

1. evidenční číslo / identifikátor VVZ,
2. identifikátor profilu a ID zakázky na elektronickém nástroji,
3. IČO zadavatele,
4. IČO dodavatele,
5. číslo smlouvy,
6. názvu a normalizovaného názvu zakázky,
7. data zadání / podpisu smlouvy,
8. ceny a dalších kontrolních atributů.

Pokud zdroje nelze bezpečně propojit, záznam se nesmí automaticky sloučit. Systém ho označí jako kandidáta na propojení a zachová původní zdrojové záznamy.

## Důležitá zásada

Rozdíl mezi dvěma oficiálními zdroji není automaticky chyba. Systém pouze zaznamená rozdíl, uvede oba zdroje a umožní následnou kontrolu dokumentů.