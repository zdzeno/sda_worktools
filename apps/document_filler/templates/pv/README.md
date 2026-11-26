# PV templates (`templates/pv/`)

Proces-verbal (PV) Word templates for **SDA Document Filler**, prepared for [docxtpl](https://docxtpl.readthedocs.io/) rendering.

## Layout

```text
templates/pv/
├── README.md                 # this file
├── manifest.yaml             # category, groups, template ids, Drive mapping
├── _sources/                 # unmodified downloads from Drive (reference)
│   └── *.docx
└── <template_id>/
    ├── template.docx         # docxtpl-ready ({{ field_key }} in bold positions)
    └── fields.schema.yaml    # sidecar field definitions for the GUI (later)
```

## Conventions

| Source signal | Repo representation |
|---------------|---------------------|
| **Bold** text in Word | Jinja placeholder `{{ key }}` in `template.docx` |
| Rare / stable values (contract nr., PDG/DGI decision, licență) | `default_from_settings: true` in `fields.schema.yaml` (overridable per run) |
| Human uncertain extractions | `human_review: true` + `review_reason` in schema |

**Sub-categories** (see `manifest.yaml`):

- `document` — single PV for a month/channel/internet delivery
- `document_set` — trimestrial packages (TRIM II/III, BMAT diferențe, facturare)

## Regenerating templates

From the repository root (requires `python-docx` and `pyyaml`):

```bash
python scripts/analyze_pv_docx.py apps/document_filler/templates/pv/_sources/<file>.docx
python scripts/analyze_pv_docx.py --convert \
  --template-id <id> \
  --label "Titlu în română" \
  --out-dir apps/document_filler/templates/pv/<template_id> \
  apps/document_filler/templates/pv/_sources/<file>.docx
```

Analysis prints bold-run counts and flags ambiguous keys for review. Use `--json` for machine-readable proposals.

## Status (first pass)

Three templates are converted under their `<template_id>/` folders. Remaining Drive files are listed in `manifest.yaml` with `status: inventory_only` until reviewed.

Source folder on Drive: `04/documente munca/Templates PV` (folder id `1hDrjjtWRCWihf8_uAoFvqu0DvOarRonp`).