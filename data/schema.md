# Datový model

Projekt je evidován jako jeden propojený životní cyklus veřejné zakázky:

`zadání → účastníci → výběr → smlouva → dodatky → změny → ukončení`

## `data/index.json`

Souhrnný index všech nalezených položek. Obsahuje stav parseru, čas poslední synchronizace, počty podle stavů a odkazy na jednotlivé projekty.

## Projekt

Každý projekt má vlastní složku `data/projects/<project_id>/` a minimálně soubor `project.json`.

```json
{
  "project_id": "stable-id",
  "title": "Název zakázky",
  "status": "plneni-smlouvy",
  "source": {
    "profile_url": "https://www.vhodne-uverejneni.cz/profil/mesto-lomnice-nad-popelkou",
    "detail_url": null,
    "retrieved_at": null,
    "source_sha256": null
  },
  "dates": {
    "published": null,
    "submission_deadline": null,
    "award": null,
    "contract": null,
    "completion": null,
    "cancelled": null
  },
  "financials": {
    "estimated_value": null,
    "winning_bid": null,
    "contract_value": null,
    "current_value": null,
    "currency": "CZK",
    "changes": []
  },
  "participants": [],
  "winner": null,
  "documents": [],
  "timeline": [],
  "signals": []
}
```

## Finanční změny

Každá změna ceny musí být dohledatelná na konkrétní smlouvě, dodatku, změnovém listu nebo jiném zdroji. U změny ukládáme původní hodnotu, novou hodnotu, rozdíl v Kč, procentní změnu a zdroj.

## Účastníci a dodavatelé

Dodavatelům bude později přidělen stabilní identifikátor podle IČO. To umožní vytvořit přehled opakovaných dodavatelů napříč zakázkami bez toho, aby se jejich četnost interpretovala jako důkaz pochybení.

## Kontrolní signály

Signály jsou pouze analytické podněty k ověření. Nejsou automatickým závěrem o pochybení.

Příklady typů:

- `price_change` – změna ceny
- `deadline_change` – změna termínu
- `scope_change` – změna rozsahu
- `participant_count` – počet účastníků
- `missing_document` – očekávaný dokument není nalezen
- `date_order_anomaly` – časová posloupnost vyžaduje kontrolu
- `repeated_supplier` – dodavatel se opakuje
- `tender_cancelled` – řízení bylo zrušeno
- `addendum_timing` – dodatek vyžaduje kontrolu časové návaznosti

Každý signál musí obsahovat popis, výpočet nebo pravidlo, úroveň (`info`, `watch`, `review`) a zdrojový dokument nebo URL.
