# Normalizované zdrojové záznamy

Sem se ukládají strojově zpracované záznamy z jednotlivých oficiálních zdrojů.

Doporučené podsložky:
- `vhodne-uverejneni/` – profil zadavatele a jeho dokumenty
- `vvz/` – Věstník veřejných zakázek
- `registr-smluv/` – smlouvy a dodatky
- `mesto/` – rozhodnutí, rozpočet a další veřejné podklady města

Resolver očekává JSON/JSONL. Preferovaná pole jsou:
`source_id`, `title`, `buyer_ico`, `supplier_ico`, `contract_number`,
`vvz_id`, `profile_id`, `procurement_id`, `contract_id`, `date`, `price`.

Záznamy se mezi zdroji automaticky spojí pouze při dostatečně silné shodě.
Slabší shody zůstávají v `data/link_candidates.json` k ručnímu ověření.
