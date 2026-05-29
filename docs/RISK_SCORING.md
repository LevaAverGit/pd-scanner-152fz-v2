# Risk Scoring Model

This document describes the heuristic risk scoring used to derive
`overall_public_risk_level` in the `FZ152Assessment`.

**Important:** This is a heuristic score based on publicly observable signals.
It does not constitute a legal risk assessment and must not be used as a
substitute for professional legal review.

---

## Overall Public Risk Level

The scanner assigns one of three levels: `low`, `medium`, or `high`.

These correspond to the density of observable signals that may indicate
compliance gaps under 152-FZ, not to confirmed legal violations.

| Level | Meaning |
|---|---|
| low | Few or no observable gap signals found in public-facing evidence |
| medium | One or more gap signals detected; manual review recommended |
| high | Multiple gap signals detected, including high-weight indicators; manual review required |

---

## Scoring Factors

Each factor adds points to an internal score. The score determines the risk level.

| Factor | Points | Rationale |
|---|---|---|
| No public privacy policy found | +3 | Highest weight — public availability is an explicit 152-FZ requirement (Art. 18.1) |
| Consent mechanism: `weak_or_absent` | +3 | Forms collect data with no consent signal — direct documented-consent risk (Art. 6, Art. 9) |
| Consent mechanism: `bundled_text` | +2 | Implied/bundled consent — adequacy uncertain without legal review |
| Third-party routing present + no processor disclosure in policy | +2 | Processors receiving data without policy disclosure (Art. 6(4)) |
| Third-party routing present + no cross-border section in policy | +1 | Potential undisclosed cross-border transfer (Art. 12) |
| No legal basis section in policy | +2 | Legal basis for processing not publicly evidenced (Art. 14(2)(1)) |
| No data subject rights section | +1 | Rights not documented publicly (Art. 14) |
| No retention/destruction section | +1 | Retention procedures not publicly evidenced (Art. 21) |
| Metrics/tracking signals present | +1 | Cookie/analytics consent and disclosure requires validation |
| More than 5 potential gaps identified | +1 | Broad signal density indicates systemic review needed |

### Thresholds

| Score | Level |
|---|---|
| 0 | low |
| 1 – 2 | medium |
| 3 or more | high |

---

## Score Calculation Example

**Site A — publicly observable gaps:**
- Privacy policy found: yes (0 pts)
- Consent mechanism: `bundled_text` (+2)
- Third-party scripts present, no processor section (+2)
- No legal basis section (+2)

Score = 6 → **high**

**Site B — minimal observable gaps:**
- Privacy policy found, all sections present (0 pts)
- Consent mechanism: `explicit_checkbox` (0 pts)
- No third-party scripts (0 pts)
- Tracking scripts present (+1)

Score = 1 → **medium**

---

## What the Score Does NOT Represent

- Not a CVSS-equivalent vulnerability score
- Not a legal compliance score or audit grade
- Not comparable across operators with different contexts
  (a healthcare operator and an e-commerce operator face different regulatory expectations)
- Not based on any specific regulatory guidance or official scoring methodology

---

## Data Category Risk Classification

In addition to the overall risk level, the scanner flags high-risk personal data categories
that receive additional attention in the UI:

| Category | Regulatory basis | Why high-risk |
|---|---|---|
| `health` | Art. 9(1) 152-FZ | Special category — biometric/health data; stricter consent requirements |
| `financial` | Art. 9 152-FZ, PCI DSS | Payment card and banking data — regulated by PCI DSS and 152-FZ |
| `national_id` | Art. 87 GDPR / 152-FZ | Government-issued IDs require heightened protection |
| `gender` | Art. 9 GDPR / 152-FZ | Can qualify as special category data |

High-risk categories are labeled in the UI and in reports to draw analyst attention.
Their detection does not automatically raise the `overall_public_risk_level` — that
score is based on consent and policy signals, not on category detection alone.

---

## Limitations

- The scoring model is calibrated for typical Russian commercial websites.
  Sites with unusual patterns (e.g., multi-form flows, cookie consent managed via
  external CMP) may produce inaccurate risk signals.
- A `low` score does not mean the site is compliant. It means the scanner found
  few observable signals in the public layer it can access.
- A `high` score does not mean the site is non-compliant. The operator may have
  controls in place that are not publicly visible.
- The model assigns equal weight to all instances of each factor. In a real
  risk assessment, context would modulate weight (e.g., the type of data processed,
  the operator's industry, the volume of processing).
