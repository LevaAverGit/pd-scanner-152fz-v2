# Privacy Audit Methodology Mapping

This document maps the scanner's output to the phases of a structured
privacy audit and describes how the tool fits into a real compliance
review workflow for Russian 152-FZ.

---

## How a Privacy Audit Works

A structured privacy audit for 152-FZ compliance typically follows these phases:

1. **Scope and authorization** — define what systems are in scope, obtain authorization
2. **Evidence collection** — gather observable data: policy, forms, third-party integrations
3. **Gap analysis** — compare evidence against regulatory requirements
4. **Risk classification** — prioritize gaps by severity
5. **Remediation guidance** — produce actionable recommendations
6. **Manual validation** — a qualified specialist reviews and confirms findings
7. **Reporting** — formal report for operator, DPO, or regulator

This scanner automates **phase 2 (evidence collection)** and partially **phase 3 (gap analysis)**
against the publicly observable layer of the target website.

---

## Phase Mapping

| Audit phase | This scanner | What is NOT covered |
|---|---|---|
| Scope and authorization | User-provided URL; SSRF guard prevents internal network targeting | Authorization workflow, engagement scope document |
| Evidence collection (public layer) | Form field classification, policy text analysis, third-party script detection, consent signal detection | Backend data flows, internal system configuration, database content |
| Gap analysis | Heuristic gap strings based on required policy sections and consent signals | Legal interpretation of gaps; severity depends on operator context |
| Risk classification | `overall_public_risk_level` (low/medium/high) | Contextual risk weighting (e.g., healthcare operator vs. e-commerce) |
| Remediation guidance | `potential_gaps` and `manual_validation_targets` lists | Specific remediation steps for the operator's technical stack |
| Manual validation | `manual_validation_targets` list | Performed by a qualified specialist, not the scanner |
| Reporting | Scan result + export | Formal legal report, regulatory correspondence |

---

## Mapping to Common Privacy Audit Activities

### Activity: Identify personal data categories collected

| Scanner output | Audit equivalent |
|---|---|
| `data_categories` list with confidence scores | PD inventory — listing of categories processed via web forms |
| Form fields with matched signals | Field-level evidence for the PD inventory |
| `site_summary.unique_categories_found` | Summary of categories across all scanned pages |

**Limitation:** The scanner detects categories observable through form field attributes.
PD categories collected by server-side logic, uploaded files, or cookies are not covered.

---

### Activity: Assess consent mechanism adequacy

| Scanner output | Audit equivalent |
|---|---|
| `fz152_assessment.consent_mechanism_type` | Consent mechanism classification |
| `has_consent_checkbox` per page | Per-form consent signal evidence |
| Gap: "No explicit consent mechanism detected" | Finding: consent documentation risk |

**Limitation:** The scanner detects form-level consent signals. The legal adequacy
of the consent wording, its scope, and its record-keeping are not assessable
from public observation.

---

### Activity: Verify privacy policy completeness

| Scanner output | Audit equivalent |
|---|---|
| `policy_has_*` boolean flags | Policy section checklist review |
| `policy_publicly_available` | Availability of the public privacy policy |
| Gaps for missing sections | Policy gap findings |

**Limitation:** Section presence is detected via keyword matching. A section may
pass keyword detection but contain inadequate or outdated content. Manual reading
of the policy is required.

---

### Activity: Map data processors and third parties

| Scanner output | Audit equivalent |
|---|---|
| `vendor_summary` (third-party scripts) | Third-party data recipients observed |
| `processor_map` | Inferred data processor list |
| Gap: "Third-party routing present but policy does not evidence processor disclosure" | Finding: processor disclosure risk |

**Limitation:** The processor map is based on scripts observed loading at scan time.
Server-side integrations, API calls made from the backend, and processors mentioned
only in internal documentation are not visible.

---

### Activity: Assess cross-border transfer risk

| Scanner output | Audit equivalent |
|---|---|
| Third-party vendors with known foreign operator status | Indicator of cross-border transfer |
| Gap: "No cross-border transfer statement publicly evidenced" | Finding: cross-border documentation risk |
| `policy_has_cross_border_section` | Policy coverage check |

**Limitation:** Cross-border transfer determination requires knowing the actual data
flow paths and the legal jurisdiction of each processor. The scanner provides
observable indicators only.

---

## What This Tool Produces vs. What a Full Audit Produces

| Artifact | This tool | Full audit |
|---|---|---|
| PD categories list | Heuristic, form-level | Complete, from all processing activities |
| Consent assessment | Observable signal classification | Legal adequacy opinion |
| Policy coverage | Boolean keyword flags | Substantive review with legal analysis |
| Processor list | Inferred from public signals | Formal processor register with DPAs |
| Risk level | Heuristic score from public signals | Legal risk assessment |
| Gaps | Heuristic strings, not confirmed findings | Confirmed findings with legal basis |
| Recommendations | `manual_validation_targets` | Specific, prioritized remediation plan |
| Deliverable | JSON/export from scan | Formal audit report signed by DPO/specialist |

---

## Intended Use

This scanner is designed for:

- Initial reconnaissance before a formal privacy review
- Internal hygiene checks by a development or product team
- Educational exploration of 152-FZ observable requirements
- Automated monitoring of public-facing compliance signals

It is **not a substitute for** a legal privacy audit, a Data Protection Impact
Assessment (DPIA), or any regulatory filing. Findings should be reviewed by
a qualified data protection specialist before any compliance decision is made.
