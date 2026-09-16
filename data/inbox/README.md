# Vstupní data

Tato složka je určena pro oficiální snapshoty dat z Vhodného uveřejnění, které se nepodaří automaticky získat z GitHub Actions.

## Podporovaný postup

1. V PVU získat XMLdataVZ pro požadované období.
2. Vložit původní XML soubor beze změn do této složky.
3. Zachovat zdrojové URL a datum získání v doprovodném manifestu, pokud je známe.
4. Zpracování následně vytvoří normalizovaná data v `data/projects/`, `data/companies/` a `data/changes/`.

Soubory zde považujeme za zdrojový materiál. Neměnit jejich obsah ručně.
