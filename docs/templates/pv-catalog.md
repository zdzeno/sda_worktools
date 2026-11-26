# PV template catalog (first pass)

Category **PV** (Proces Verbal) — inventory from Google Drive folder **Templates PV** (`1hDrjjtWRCWihf8_uAoFvqu0DvOarRonp`), cross-linked to `apps/document_filler/templates/pv/manifest.yaml`.

## Converted in repo (docxtpl + schema)

| Template id | Romanian title (from file) | Sub-category | Unique keys | Review flags |
|-------------|-------------------------------|--------------|-------------|----------------|
| `ucmr-ada-internet-cerbul-de-aur` | PROCES VERBAL UCMR-ADA internet — Cerbul de Aur | document | 15 | 7 |
| `credidam-cfpd-internet-tvrplus` | Proces verbal CREDIDAM CFPD septembrie (TVR Plus) | document | 26 | 16 |
| `ucmr-ada-trim-iii-bmat` | PROCES verbal TRIM III UCMR ADA (+ BMAT) | document_set | 37 | 18 |

Sidecar schemas live beside each template: `fields.schema.yaml`. Entries with `human_review: true` need Zeno's pass on **field keys** (not only labels). Settings-backed defaults are marked `default_from_settings: true` when the analyzer sees contract/licență/PDG context (may include false positives — trim in review).

## Drive inventory not yet converted

| Group | File name | Notes |
|-------|-----------|--------|
| UCMR online | PROCES VERBAL UCMR-ADA internet septembrie 2026 tvr.plus.doc | Legacy `.doc` |
| UCMR set | PROCES verbal TRIM II 2026 UCMR ADA.docx | |
| UCMR set | PROCES verbal raportari TRIM II 2026_diferenta BMAT.docx | |
| CREDIDAM | Proces verbal CREDIDAM internet octombrie 2026 cerb.docx | |
| CREDIDAM | PV trim III 2026 CREDIDAM.docx | document_set |
| UPFR | PV Comision Copie Privată TRIM III 2026 UPFR.docx | |
| UPFR | PV DS receptie trim II 2026.docx | |
| UPFR | PV fact trim III 2026 UPFR.docx | |
| UPFR | PV Internet SEPTEMBRIE 2026 UPFR.docx | |
| Mediaforest | PV MEDIAFOREST - OCTOMBRIE 2026.docx | |
| COPYRO | PV trim III 2026 COPYRO.docx | |
| UNART | PV UNART RECEPTIE TRIM III 2026.docx | |
| Generic | PV trim III 2026.docx | |

## Field patterns (observed)

Across UCMR / CREDIDAM PVs, bold fill-ins usually include:

- **Număr PV** — `Nr. <SDA> din <dată>`
- **Data convocării** — data comisiei
- **Perioada servicii** — interval raportat (`01.09.-30.09.2026`, trimestre)
- **Valoare** — sumă în lei (TVA inclus)
- **Factură furnizor** — ex. `2025UCM-11699`, `CRD599328`
- **Referințe documente SDA** — perechi `nr./dată` în blocuri compuse (marked for review)
- **Concluzii** — propoziții lungi bold (single field vs split — needs editorial decision)

Trimestrial **document_set** templates add more reference blocks and BMAT percentage lines than single **document** internet PVs.

## Tooling

`scripts/analyze_pv_docx.py` — scan bold runs, propose keys, `--convert` to emit `template.docx` + `fields.schema.yaml`.

See also: `apps/document_filler/templates/pv/README.md`.