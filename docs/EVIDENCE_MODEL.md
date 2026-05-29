# Evidence Model

This document describes what evidence the scanner collects, how it is
structured in the data model, and what limitations apply to each evidence type.

---

## Evidence Hierarchy

```
ScanResult
├── data_categories          — classified personal data fields found in forms
├── vendor_summary           — third-party JS sources by vendor class
├── processor_map            — inferred data processors with confidence level
├── site_summary             — aggregated crawl statistics
├── fz152_assessment         — synthesised compliance signal summary
│   ├── consent_mechanism_type
│   ├── policy section flags (boolean per section)
│   ├── potential_gaps       — list of heuristic gap strings
│   └── manual_validation_targets
└── operator_integration     — operator-supplied evidence (if provided)
```

---

## Data Categories Evidence

Collected by: `classifier_service.py` + `pd_dictionary.py`

Each `DataCategoryItem` contains:

| Field | Type | Description |
|---|---|---|
| `category` | str | Category name (e.g., `email`, `national_id`, `health`) |
| `confidence` | float | 1.0 = two or more field signals matched; 0.7 = one signal matched |
| `matched_signals` | list[str] | Which field attributes triggered the match (name, id, label, placeholder) |
| `explanation` | str | Human-readable description of the match |

**Confidence model:**

The classifier builds *text signals* from a form field's `name`, `id`, `label`,
`placeholder`, `aria-label`, and `autocomplete` attributes. It then compares each
signal against the category's keyword list.

- Two or more distinct signals match → confidence = 1.0
- Exactly one signal matches → confidence = 0.7
- No signals match → field not classified

The highest-confidence match wins. If two categories tie on hit count, the category
with higher position in the `PD_CATEGORIES` definition order wins.

**Limitation:** Confidence is based on field attribute text, not on the actual data
collected at runtime. A field named `tel` is classified as `phone` regardless of
whether phone numbers are actually submitted through it.

---

## Vendor Summary Evidence

Collected by: `vendor_classification_service.py`

Each `VendorSummaryItem` contains:

| Field | Type | Description |
|---|---|---|
| `host` | str | Hostname of the third-party script source |
| `vendor_name` | str | Resolved vendor name (e.g., "Yandex Metrica") |
| `vendor_class` | str | Category: analytics / ad_tech / CDN / payment / CRM / social / tracking / unknown |

**How vendors are identified:**

The service compares third-party script hosts against a lookup table of known
vendor hostnames. Hosts not in the table receive class `unknown`.

**Limitation:** The lookup table covers common Russian and international vendors.
Custom or obscure analytics platforms may not be recognized. Vendor classification
does not confirm that data is being transferred — only that the script is loaded.

---

## Processor Map Evidence

Collected by: `vendor_classification_service.py` (inferred) + operator integration

Each `ProcessorMapItem` contains:

| Field | Type | Description |
|---|---|---|
| `processor_name` | str | Processor name |
| `processor_type` | str | Type: analytics / ad / payment / CRM / CDN / unknown |
| `confidence` | str | high / medium / low |
| `source` | str | How identified: js_include / policy_mention / operator_supplied |
| `evidence` | str | Description of the evidence (e.g., script host, policy keyword) |

**Confidence levels:**

| Level | Meaning |
|---|---|
| high | Named vendor in lookup table, observed loading on page |
| medium | Hostname pattern match, or policy keyword + JS include corroborate |
| low | Inferred from generic hostname pattern or single weak signal |

**Limitation:** A processor entry with `confidence = low` means the tool found
a weak signal that a particular service may be involved. This requires manual
verification before any compliance action is taken.

---

## Policy Analysis Evidence

Collected by: `policy_extraction_service.py` + `document_extraction_service.py`

`PolicyAnalysis` contains per-section boolean flags:

| Flag | Positive signal (examples) |
|---|---|
| `has_purpose_section` | "цели обработки", "processing purposes", "purpose of collection" |
| `has_categories_section` | "категории персональных данных", "types of personal data" |
| `has_legal_basis_section` | "правовое основание", "legal basis", "основание обработки" |
| `has_processor_or_third_party_section` | "третьи лица", "поручение", "data processors" |
| `has_cross_border_section` | "трансграничная передача", "cross-border", "transfer to third countries" |
| `has_subject_rights_section` | "права субъекта", "right to access", "право на удаление" |
| `has_retention_or_destruction_section` | "сроки хранения", "retention period", "уничтожение данных" |
| `has_localization_statement` | "хранение на территории РФ", "локализация", "Russian Federation servers" |

**Limitation:** A section flag of `True` means keywords indicating that section
were found in the document. It does not mean the section is complete, accurate,
or legally sufficient. Manual review of the actual policy text is required.

---

## FZ152 Assessment Evidence

Built by: `fz152_assessment_service.py`

The `FZ152Assessment` synthesises all prior evidence into:

| Field | Type | Description |
|---|---|---|
| `consent_mechanism_type` | str | explicit_checkbox / bundled_text / weak_or_absent / mixed / unknown |
| `overall_public_risk_level` | str | low / medium / high (heuristic score only) |
| `policy_publicly_available` | bool | Whether a policy link was found |
| `policy_has_*` fields | bool | Per-section presence flags (see Policy Analysis above) |
| `potential_gaps` | list[str] | Heuristic gap descriptions |
| `manual_validation_targets` | list[str] | Specific items requiring human review |

**Important:** `overall_public_risk_level` is derived from a heuristic point score
and indicates the density of publicly observable signals that may warrant attention.
It is NOT a legal compliance assessment and should not be described as such.

---

## Evidence Confidence Summary

| Evidence type | How strong | What it confirms |
|---|---|---|
| Data category (confidence 1.0) | Medium | Field attributes suggest this category; data may or may not flow |
| Data category (confidence 0.7) | Low | One attribute heuristically matched; verify manually |
| Vendor summary | Medium | Script was loaded from this host at scan time |
| Processor (high) | Medium-high | Known vendor, observed loading |
| Processor (medium) | Low-medium | Corroborating signals; needs verification |
| Processor (low) | Low | Weak heuristic; treat as hypothesis |
| Policy section flag = True | Low-medium | Keywords found; section may or may not be complete |
| Gap string | Informational | Heuristic signal; not a confirmed compliance finding |

All evidence in the scanner output requires manual review before being used
for compliance decisions, audits, or reporting to a regulator.
