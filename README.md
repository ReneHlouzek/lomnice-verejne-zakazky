# Lomnice – veřejné zakázky

Datový a analytický archiv veřejných zakázek města Lomnice nad Popelkou.

## Cíl

Projekt postupně stahuje veřejně dostupná data z profilu zadavatele města na Vhodném uveřejnění, uchovává historické snapshoty, dokumenty a vazby mezi zakázkami, smlouvami a dodatky a nad nimi vytváří přehledovou webovou aplikaci.

Zdrojový profil: https://www.vhodne-uverejneni.cz/profil/mesto-lomnice-nad-popelkou

## Hlavní vrstvy

1. **Sběr dat** – crawler profilu a detailů zakázek.
2. **Archiv** – metadata, dokumenty, kontrolní součty a historie změn.
3. **Databáze** – projekty, firmy, účastníci, smlouvy, dodatky a finanční změny.
4. **Analýza** – časové, finanční a procesní kontrolní signály podložené zdroji.
5. **Web** – vyhledávání, filtry, detail projektu, časová osa a dokumenty.

## Zásada

Systém má oddělovat zdrojová fakta od automatických výpočtů a od kontrolních signálů. Kontrolní signál není závěr o pochybení; vždy musí být dohledatelný ke konkrétnímu dokumentu nebo výpočtu.

## Stav

Projekt je ve fázi založení infrastruktury. Další krok je implementace crawleru proti skutečné struktuře profilu a detailů Vhodného uveřejnění.


<!-- Data refresh marker: PVU archive expanded with organization contracts 2026-09-21. -->


<!-- archive-refresh-2026-09-21-2 -->
