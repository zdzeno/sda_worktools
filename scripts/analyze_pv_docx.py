#!/usr/bin/env python3
"""Scan PV Word templates for bold fill-in runs and propose docxtpl field keys.

Bold text in source PV documents marks values that change per issuance. Headers,
table labels, concluzii boilerplate, and list markers are skipped.

Usage:
    python scripts/analyze_pv_docx.py apps/document_filler/templates/pv/_sources/foo.docx
    python scripts/analyze_pv_docx.py --convert --template-id my-id path/to.docx --out-dir ...
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document
from docx.document import Document as DocumentType
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

# Stable values that may live in app settings (only when they appear in the bold run text).
SETTINGS_TEXT_MARKERS = (
    "deciziei pdg",
    "deciziei dgi",
    "decizie pdg",
    "decizie dgi",
    "hotărârea consiliului",
    "hotararea consiliului",
    "licenţei neexclusive",
    "licentei neexclusive",
    "contract nr",
    "mediaforest",
)

DATE_RE = re.compile(r"^\d{1,2}\.\d{2}\.\d{4}\.?$")
PERIOD_RE = re.compile(
    r"^\d{1,2}\.\d{1,2}\.?\s*-\s*\d{1,2}\.\d{1,2}\.?\s*-\s*\d{4}$|"
    r"^\d{1,2}\.\d{1,2}\.?\s*-\s*\d{1,2}\.\d{1,2}\.\d{4}$|"
    r"^\d{1,2}-\d{1,2}\.\d{1,2}\.\d{4}$"
)
AMOUNT_LEI_RE = re.compile(r"^\d[\d.,\s]*\s*lei", re.I)
AMOUNT_PLAIN_RE = re.compile(r"^\d{1,3}(\.\d{3})+,\d{2}$")
PV_NR_RE = re.compile(r"^Nr\.?\s*", re.I)
PV_NR_FULL_RE = re.compile(
    r"^Nr\.?\s*(?:SDA\s*)?\d+\s+din\s+\d{1,2}\.\d{2}\.\d{4}", re.I
)
PV_NR_BODY_RE = re.compile(r"^\d+\s+din\s+\d{1,2}\.\d{2}\.\d{4}$", re.I)
SDA_REF_RE = re.compile(r"\d{3,}/\d{1,2}\.\d{1,2}\.\d{4}")
INVOICE_UCM_RE = re.compile(r"\d{4}UCM-\d+", re.I)
INVOICE_CRD_RE = re.compile(r"CRD\d+", re.I)
INVOICE_WITH_DATE_RE = re.compile(
    r"(?P<nr>(?:\d{4}UCM-\d+|CRD\d+))\s+din\s+(?P<dt>\d{1,2}\.\d{2}\.\d{4})",
    re.I,
)
PCT_RE = re.compile(r"^[,]?\d+[.,]?\d*\s*%", re.I)

IGNORABLE_EXACT = frozenset({"nr.", "nr", "nr.", "2", "3.", "3", "1.", "1", "2.", "a", ",", ", "})

IGNORABLE_PREFIXES = (
    "pentru a proceda la recep",
    "în perioada",
    "in perioada",
    ", conform",
)


def _slug(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^\w]+", "_", text.strip().lower(), flags=re.UNICODE)
    s = re.sub(r"_+", "_", s).strip("_")
    return (s[:max_len] or "field").strip("_")


def _normalize_ref(text: str) -> str:
    return text.strip().lstrip(". ").strip()


@dataclass
class BoldRun:
    text: str
    paragraph_index: int
    context_before: str
    paragraph_text: str
    in_table: bool
    proposed_key: str = ""
    placeholder_text: str = ""
    human_review: bool = False
    review_reason: str = ""
    default_from_settings: bool = False
    extra_keys: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    source: str
    bold_runs: list[BoldRun] = field(default_factory=list)

    def unique_fields(self) -> list[BoldRun]:
        seen: set[str] = set()
        out: list[BoldRun] = []
        for run in self.bold_runs:
            keys = [run.proposed_key, *run.extra_keys]
            for key in keys:
                if key in seen:
                    continue
                seen.add(key)
                if key == run.proposed_key:
                    out.append(run)
                else:
                    out.append(
                        BoldRun(
                            text=run.text,
                            paragraph_index=run.paragraph_index,
                            context_before=run.context_before,
                            paragraph_text=run.paragraph_text,
                            in_table=run.in_table,
                            proposed_key=key,
                            placeholder_text=run.placeholder_text,
                            human_review=run.human_review,
                            review_reason=run.review_reason,
                            default_from_settings=run.default_from_settings,
                        )
                    )
        return out


def iter_paragraphs(doc: DocumentType):
    for block in doc.element.body:
        if block.tag == qn("w:p"):
            yield Paragraph(block, doc), False
        elif block.tag == qn("w:tbl"):
            table = Table(block, doc)
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        yield para, True


def paragraph_context_before(para: Paragraph, run_index: int) -> str:
    acc = []
    for i, run in enumerate(para.runs):
        if i >= run_index:
            break
        acc.append(run.text)
    return "".join(acc)


def is_concluzii_section_header(para: Paragraph) -> bool:
    low = para.text.lower()
    return "concluzii" in low and ("iii" in low or "concluzii generale" in low)


def is_title_paragraph(para: Paragraph) -> bool:
    runs = [r for r in para.runs if r.text and r.text.strip()]
    if not runs:
        return False
    bold_count = sum(1 for r in runs if r.bold)
    full_text = para.text.strip()
    if PV_NR_FULL_RE.match(full_text) or PV_NR_BODY_RE.match(full_text):
        return False
    if DATE_RE.match(full_text) or PERIOD_RE.match(full_text):
        return False
    if AMOUNT_LEI_RE.search(full_text):
        return False
    if bold_count == len(runs) and len(full_text) > 3:
        upper_markers = (
            "proces-verbal",
            "proces verbal",
            "date generale",
            "constatări",
            "constatari",
            "concluzii",
            "verificări",
            "verificari",
            "exemplarul",
            "comisia de recep",
            "comisie recep",
            "nr. crt",
        )
        low = full_text.lower()
        if any(m in low for m in upper_markers):
            return True
        if full_text.isupper() or (bold_count == len(runs) and len(full_text) < 80):
            return True
    return False


def is_ignorable_bold(text: str) -> bool:
    t = text.strip()
    low = t.lower()
    if not t:
        return True
    if low in IGNORABLE_EXACT or low in {"nr.", "nr"}:
        return True
    if PV_NR_RE.match(t) and "din" not in low and len(t) < 6:
        return True
    if t in {"SEPTEMBRIE", "2026"}:
        return True
    for prefix in IGNORABLE_PREFIXES:
        if low.startswith(prefix):
            return True
    if low in {"ii.", "i.", "iii."}:
        return True
    return False


def sda_reference_key(context: str, _para_text: str, key_counts: Counter[str]) -> str:
    """Classify SDA nr./dată using local bold context (not full paragraph — avoids BMAT bleed)."""
    blob = context.lower()[-280:]
    if re.search(r"adresa\s+de\b|\bde\s+nr\b", blob):
        base = "referinta_de_calcul"
    elif re.search(r"adresa\s+sda", blob):
        if "pondere" in blob or "remunera" in blob:
            base = "referinta_sda_pondere"
        else:
            base = "referinta_sda_adresa"
    elif re.search(r"adresa\s+ucmr|ucmr-ada\s+nr", blob):
        base = "referinta_furnizor_bmat"
    elif any(k in blob for k in ("raport", "playlist", "transmis", "lunar", "luna")):
        base = "referinta_raportare"
    else:
        base = "referinta_sda"
    count = key_counts[base]
    key_counts[base] += 1
    return base if count == 0 else f"{base}_{count + 1}"


def settings_default_for_text(text: str) -> bool:
    low = text.lower()
    return any(m in low for m in SETTINGS_TEXT_MARKERS)


def propose_key(
    text: str,
    context: str,
    para_text: str,
    key_counts: Counter[str],
) -> tuple[str, str, bool, str, list[str]]:
    """Return (key, placeholder_replacement, human_review, reason, extra_keys)."""
    t = text.strip()
    low_ctx = context.lower()
    para_low = para_text.lower()
    human = False
    reason = ""

    inv_match = INVOICE_WITH_DATE_RE.search(t)
    if inv_match:
        base_nr = "numar_factura_furnizor"
        base_dt = "data_factura_furnizor"
        key_counts[base_nr] += 1
        key_counts[base_dt] += 1
        placeholder = (
            f"{{{{ {base_nr} }}}} din {{{{ {base_dt} }}}}"
        )
        return base_nr, placeholder, False, "", [base_dt]

    if PV_NR_FULL_RE.match(t) or PV_NR_BODY_RE.match(t):
        base = "numar_pv"
        key = base if key_counts[base] == 0 else f"{base}_{key_counts[base] + 1}"
        key_counts[base] += 1
        placeholder = f"{{{{ {key} }}}}"
        return key, placeholder, False, "", []

    ref_t = _normalize_ref(t)
    if SDA_REF_RE.search(ref_t) and not PERIOD_RE.match(ref_t):
        key = sda_reference_key(low_ctx, para_low, key_counts)
        placeholder = f"{{{{ {key} }}}}"
        return key, placeholder, False, "", []

    if DATE_RE.match(t):
        if "factur" in low_ctx or "factur" in para_low or "facturii" in low_ctx:
            base = "data_factura_furnizor"
        elif "convocată" in low_ctx or "convocata" in low_ctx or "convocată" in para_low:
            base = "data_convocare"
        elif "încheiat" in para_low or "incheiat" in para_low:
            base = "data_incheiere_pv"
            human = True
            reason = "incheiere_date"
        else:
            base = "data"
            human = True
            reason = "ambiguous_date"
        key = base if key_counts[base] == 0 else f"{base}_{key_counts[base] + 1}"
        key_counts[base] += 1
        placeholder = f"{{{{ {key} }}}}"
        return key, placeholder, human, reason, []

    if PERIOD_RE.match(t) or (
        "perioada" in (low_ctx + para_low) and re.search(r"\d{2}\.\d{2}", t)
    ):
        base = "perioada_servicii"
        key = base if key_counts[base] == 0 else f"{base}_{key_counts[base] + 1}"
        key_counts[base] += 1
        placeholder = f"{{{{ {key} }}}}"
        return key, placeholder, False, "", []

    if AMOUNT_LEI_RE.match(t):
        base = "valoare_servicii"
        key = base if key_counts[base] == 0 else f"{base}_{key_counts[base] + 1}"
        key_counts[base] += 1
        placeholder = f"{{{{ {key} }}}}"
        return key, placeholder, False, "", []

    if AMOUNT_PLAIN_RE.match(t):
        if "valoarea serviciilor" in para_low or "valoare" in para_low:
            base = "valoare_servicii"
        else:
            base = "valoare_detaliu"
            human = True
            reason = "amount_breakdown"
        key = base if key_counts[base] == 0 else f"{base}_{key_counts[base] + 1}"
        key_counts[base] += 1
        placeholder = f"{{{{ {key} }}}}"
        return key, placeholder, human, reason, []

    if PCT_RE.match(t):
        base = "procent_bmat"
        key = base if key_counts[base] == 0 else f"{base}_{key_counts[base] + 1}"
        key_counts[base] += 1
        placeholder = f"{{{{ {key} }}}}"
        return key, placeholder, False, "", []

    if INVOICE_UCM_RE.search(t):
        base = "numar_factura_furnizor"
        key = base if key_counts[base] == 0 else f"{base}_{key_counts[base] + 1}"
        key_counts[base] += 1
        placeholder = f"{{{{ {key} }}}}"
        return key, placeholder, False, "", []

    if INVOICE_CRD_RE.search(t):
        base = "numar_factura_furnizor"
        key = base if key_counts[base] == 0 else f"{base}_{key_counts[base] + 1}"
        key_counts[base] += 1
        placeholder = f"{{{{ {key} }}}}"
        return key, placeholder, False, "", ""

    if t in {"2", "3.", "3", "1.", "1", "2."}:
        return "enumerare_punct", "", True, "list_marker_not_field", []

    if len(t) <= 2:
        return "fragment_bold", "", True, "short_fragment", []

    base = f"bold_{_slug(t)}"
    human = True
    reason = "heuristic_slug"
    key = base if key_counts[base] == 0 else f"{base}_{key_counts[base] + 1}"
    key_counts[base] += 1
    placeholder = f"{{{{ {key} }}}}"
    return key, placeholder, human, reason, []


def analyze_path(path: Path) -> AnalysisResult:
    doc = Document(path)
    result = AnalysisResult(source=str(path))
    key_counts: Counter[str] = Counter()
    in_concluzii = False

    for para_index, (para, in_table) in enumerate(iter_paragraphs(doc)):
        if is_concluzii_section_header(para):
            in_concluzii = True
            continue
        if is_title_paragraph(para):
            continue
        if in_concluzii:
            continue

        para_text = para.text
        for run_index, run in enumerate(para.runs):
            if not run.bold or not run.text or not run.text.strip():
                continue
            text = run.text
            if is_ignorable_bold(text):
                continue
            ctx = paragraph_context_before(para, run_index)
            key, placeholder, human, reason, extra = propose_key(
                text, ctx, para_text, key_counts
            )
            if reason == "list_marker_not_field":
                continue
            default_settings = settings_default_for_text(text)
            result.bold_runs.append(
                BoldRun(
                    text=text,
                    paragraph_index=para_index,
                    context_before=ctx[-120:],
                    paragraph_text=para_text[:300],
                    in_table=in_table,
                    proposed_key=key,
                    placeholder_text=placeholder or f"{{{{ {key} }}}}",
                    human_review=human,
                    review_reason=reason,
                    default_from_settings=default_settings,
                    extra_keys=extra,
                )
            )
    return result


def analysis_to_schema(result: AnalysisResult, template_id: str, label_ro: str) -> dict:
    fields = []
    seen: set[str] = set()
    for run in result.bold_runs:
        for key in [run.proposed_key, *run.extra_keys]:
            if key in seen:
                continue
            seen.add(key)
            label = run.text.strip()[:200]
            if key == "data_factura_furnizor" and "din" in run.text:
                m = INVOICE_WITH_DATE_RE.search(run.text)
                label = m.group("dt") if m else label
            entry = {
                "key": key,
                "label": _field_label(key, label),
                "type": "string",
                "sample": label,
            }
            if run.default_from_settings and key == run.proposed_key:
                entry["default_from_settings"] = True
            if run.human_review and key == run.proposed_key:
                entry["human_review"] = True
                if run.review_reason:
                    entry["review_reason"] = run.review_reason
            fields.append(entry)

    return {
        "template_id": template_id,
        "label": label_ro,
        "category": "PV",
        "fields": fields,
    }


def _field_label(key: str, sample: str) -> str:
    labels = {
        "numar_pv": "Număr PV",
        "data_convocare": "Data convocării",
        "perioada_servicii": "Perioada servicii",
        "valoare_servicii": "Valoare servicii (TVA inclus)",
        "numar_factura_furnizor": "Număr factură furnizor",
        "data_factura_furnizor": "Data factură furnizor",
        "data_incheiere_pv": "Data încheierii PV",
        "procent_bmat": "Procent BMAT",
    }
    if key in labels:
        return labels[key]
    if key.startswith("referinta_"):
        return sample.strip()[:120]
    return sample.strip()[:200]


def apply_conversion(path: Path, out_docx: Path, result: AnalysisResult) -> None:
    doc = Document(path)
    key_counts: Counter[str] = Counter()
    in_concluzii = False

    for para_index, (para, _in_table) in enumerate(iter_paragraphs(doc)):
        if is_concluzii_section_header(para):
            in_concluzii = True
            continue
        if is_title_paragraph(para):
            continue
        if in_concluzii:
            continue

        para_text = para.text
        for run_index, run in enumerate(para.runs):
            if not run.bold or not run.text or not run.text.strip():
                continue
            if is_ignorable_bold(run.text):
                continue
            ctx = paragraph_context_before(para, run_index)
            key, placeholder, human, reason, extra = propose_key(
                run.text, ctx, para_text, key_counts
            )
            if reason == "list_marker_not_field":
                continue
            run.text = placeholder

    out_docx.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_docx)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docx", type=Path, nargs="+", help="Input .docx file(s)")
    parser.add_argument("--json", action="store_true", help="Emit analysis JSON to stdout")
    parser.add_argument(
        "--convert",
        action="store_true",
        help="Write docxtpl .docx and fields.schema.yaml (requires --template-id and --out-dir)",
    )
    parser.add_argument("--template-id", help="Template id for conversion output")
    parser.add_argument("--label", default="", help="Romanian display label for schema")
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="Directory for template.docx and fields.schema.yaml",
    )
    args = parser.parse_args(argv)

    for path in args.docx:
        if not path.is_file():
            print(f"Missing file: {path}", file=sys.stderr)
            return 1
        result = analyze_path(path)
        review_count = sum(1 for r in result.bold_runs if r.human_review)

        if args.json:
            payload = {
                "source": result.source,
                "bold_run_count": len(result.bold_runs),
                "unique_field_count": len(result.unique_fields()),
                "human_review_count": review_count,
                "runs": [
                    {
                        "text": r.text,
                        "proposed_key": r.proposed_key,
                        "extra_keys": r.extra_keys,
                        "human_review": r.human_review,
                        "review_reason": r.review_reason,
                        "default_from_settings": r.default_from_settings,
                        "paragraph_index": r.paragraph_index,
                        "in_table": r.in_table,
                    }
                    for r in result.bold_runs
                ],
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))

        print(
            f"{path.name}: {len(result.bold_runs)} bold runs, "
            f"{len(result.unique_fields())} unique keys, {review_count} flagged for review",
            file=sys.stderr if args.json else sys.stdout,
        )

        if args.convert:
            if not args.template_id or not args.out_dir:
                print("--convert requires --template-id and --out-dir", file=sys.stderr)
                return 1
            if yaml is None:
                print("PyYAML required for --convert (pip install pyyaml)", file=sys.stderr)
                return 1
            out_dir = args.out_dir
            label = args.label or args.template_id
            schema = analysis_to_schema(result, args.template_id, label)
            apply_conversion(path, out_dir / "template.docx", result)
            schema_path = out_dir / "fields.schema.yaml"
            schema_path.write_text(
                yaml.dump(schema, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            print(f"Wrote {out_dir / 'template.docx'} and {schema_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())