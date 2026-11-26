#!/usr/bin/env python3
"""Scan PV Word templates for bold fill-in runs and propose docxtpl field keys.

Bold text in source PV documents marks values that change per issuance. Headers
and table labels are usually bold too; this script flags those for human review.

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

SETTINGS_DEFAULT_HINTS = (
    "contract",
    "ucm-",
    "licen",
    "hotărâre",
    "hotarare",
    "deciziei pdg",
    "decizie pdg",
    "mediaforest",
    "monitorul oficial",
)

DATE_RE = re.compile(r"^\d{1,2}\.\d{1,2}\.\d{4}$")
PERIOD_RE = re.compile(r"^\d{1,2}\.\d{1,2}\.?\s*-\s*\d{1,2}\.\d{1,2}\.\d{4}$")
AMOUNT_RE = re.compile(r"^\d[\d.,\s]*\s*lei", re.I)
PV_NR_RE = re.compile(r"^Nr\.?\s*\d+", re.I)
SDA_REF_RE = re.compile(r"\d{3,}/\d{2}\.\d{2}\.\d{4}")
INVOICE_UCM_RE = re.compile(r"\d{4}UCM-\d+", re.I)
INVOICE_CRD_RE = re.compile(r"CRD\d+", re.I)


def _slug(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^\w]+", "_", text.strip().lower(), flags=re.UNICODE)
    s = re.sub(r"_+", "_", s).strip("_")
    return (s[:max_len] or "field").strip("_")


@dataclass
class BoldRun:
    text: str
    paragraph_index: int
    context_before: str
    in_table: bool
    proposed_key: str = ""
    human_review: bool = False
    review_reason: str = ""
    default_from_settings: bool = False


@dataclass
class AnalysisResult:
    source: str
    bold_runs: list[BoldRun] = field(default_factory=list)

    def unique_fields(self) -> list[BoldRun]:
        seen: set[str] = set()
        out: list[BoldRun] = []
        for run in self.bold_runs:
            if run.proposed_key in seen:
                continue
            seen.add(run.proposed_key)
            out.append(run)
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
    return "".join(acc).lower()


def is_title_paragraph(para: Paragraph) -> bool:
    runs = [r for r in para.runs if r.text and r.text.strip()]
    if not runs:
        return False
    bold_count = sum(1 for r in runs if r.bold)
    full_text = para.text.strip()
    if PV_NR_RE.search(full_text) or DATE_RE.search(full_text) or PERIOD_RE.match(full_text):
        return False
    if AMOUNT_RE.search(full_text):
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


def propose_key(text: str, context: str, key_counts: Counter[str]) -> tuple[str, bool, str]:
    t = text.strip()
    low_ctx = context.lower()
    human = False
    reason = ""

    if PV_NR_RE.match(t) and "din" in t.lower():
        base = "numar_pv"
    elif DATE_RE.match(t):
        if "convocată" in low_ctx or "convocata" in low_ctx:
            base = "data_convocare"
        elif "semnat" in low_ctx or "data de" in low_ctx[-40:]:
            base = "data_semnare"
        else:
            base = "data"
            human = True
            reason = "ambiguous_date"
    elif PERIOD_RE.match(t) or (
        "perioada" in low_ctx and re.search(r"\d{2}\.\d{2}", t)
    ):
        base = "perioada_servicii"
    elif AMOUNT_RE.match(t):
        base = "valoare_servicii"
    elif INVOICE_UCM_RE.search(t):
        base = "numar_factura_furnizor"
    elif INVOICE_CRD_RE.search(t):
        base = "numar_factura_furnizor"
    elif SDA_REF_RE.search(t) and len(t) > 15:
        base = "referinte_documente"
        human = True
        reason = "compound_reference_block"
    elif t in {"2", "3.", "3", "1.", "1", "2."}:
        base = "enumerare_punct"
        human = True
        reason = "list_marker_not_field"
    elif len(t) <= 2:
        base = "fragment_bold"
        human = True
        reason = "short_fragment"
    else:
        base = f"bold_{_slug(t)}"
        human = True
        reason = "heuristic_slug"

    default_settings = any(h in (low_ctx + " " + t.lower()) for h in SETTINGS_DEFAULT_HINTS)
    if default_settings and base.startswith("bold_"):
        human = True
        reason = (reason + ";settings_default_candidate").strip(";")

    count = key_counts[base]
    key_counts[base] += 1
    key = base if count == 0 else f"{base}_{count + 1}"
    return key, human, reason


def analyze_path(path: Path) -> AnalysisResult:
    doc = Document(path)
    result = AnalysisResult(source=str(path))
    key_counts: Counter[str] = Counter()

    for para_index, (para, in_table) in enumerate(iter_paragraphs(doc)):
        if is_title_paragraph(para):
            continue
        for run_index, run in enumerate(para.runs):
            if not run.bold or not run.text or not run.text.strip():
                continue
            text = run.text
            ctx = paragraph_context_before(para, run_index)
            key, human, reason = propose_key(text, ctx, key_counts)
            default_settings = any(
                h in (ctx + " " + text.lower()) for h in SETTINGS_DEFAULT_HINTS
            )
            result.bold_runs.append(
                BoldRun(
                    text=text,
                    paragraph_index=para_index,
                    context_before=ctx[-120:],
                    in_table=in_table,
                    proposed_key=key,
                    human_review=human,
                    review_reason=reason,
                    default_from_settings=default_settings,
                )
            )
    return result


def analysis_to_schema(result: AnalysisResult, template_id: str, label_ro: str) -> dict:
    fields = []
    for run in result.unique_fields():
        if run.review_reason == "list_marker_not_field":
            continue
        entry = {
            "key": run.proposed_key,
            "label": run.text.strip()[:200],
            "type": "string",
            "sample": run.text.strip()[:200],
        }
        if run.default_from_settings:
            entry["default_from_settings"] = True
        if run.human_review:
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


def apply_conversion(path: Path, out_docx: Path, result: AnalysisResult) -> None:
    doc = Document(path)
    key_counts: Counter[str] = Counter()
    used_keys: dict[tuple[int, str], str] = {}

    for para_index, (para, _in_table) in enumerate(iter_paragraphs(doc)):
        if is_title_paragraph(para):
            continue
        for run_index, run in enumerate(para.runs):
            if not run.bold or not run.text or not run.text.strip():
                continue
            ctx = paragraph_context_before(para, run_index)
            key, human, reason = propose_key(run.text, ctx, key_counts)
            if reason == "list_marker_not_field":
                continue
            run.text = f"{{{{ {key} }}}}"
            used_keys[(para_index, key)] = key

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