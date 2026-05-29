# PD Scanner — Scan Report

> **SYNTHETIC EXAMPLE — All data is fabricated for demonstration purposes.**
> This report does not represent any real organisation, website, or scan result.

---

**Scan ID:** `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
**URL:** `https://example-corp.ru/register`
**Scanned:** 2026-04-01 10:15:42 UTC
**Status:** complete

---

## Summary

| Metric | Value |
|---|---|
| Pages scanned | 8 |
| Forms found | 3 |
| Pages with forms | 3 |
| Personal data categories detected | 6 |
| Third-party hosts observed | 4 |
| Pages with privacy link | 7 |
| Pages with consent checkbox | 2 |
| Pages with marketing consent | 1 |

---

## Detected Personal Data Categories

| Category | Confidence | Matched Signals |
|---|---|---|
| email | 1.0 | `email`, `email` (label: "Электронная почта") |
| full_name | 1.0 | `name`, `first_name`, `last_name` |
| phone | 1.0 | `phone`, `tel` |
| date_of_birth | 0.7 | `dob` |
| address | 0.7 | `city` |
| password | 1.0 | `password`, `confirm_password` |

**Registration relevance:** high

---

## Site Summary

- **Seed URL registration relevance:** high
- **Consent mechanism type:** explicit_checkbox (privacy consent checkbox present on registration page)
- **Top third-party hosts:** `mc.yandex.ru`, `connect.facebook.net`, `api.amplitude.com`

---

## Third-Party Network Observations

| Host | Type | Vendor Class |
|---|---|---|
| `mc.yandex.ru` | script | analytics |
| `connect.facebook.net` | script | ad_tech |
| `api.amplitude.com` | xhr | analytics |
| `cdn.jsdelivr.net` | script | cdn |

---

## Vendor Classification

| Host | Vendor | Class | Notes |
|---|---|---|---|
| `mc.yandex.ru` | Yandex Metrica | analytics | Yandex analytics pixel — common on Russian sites |
| `connect.facebook.net` | Meta Pixel | ad_tech | Meta advertising pixel; cross-border transfer implied |
| `api.amplitude.com` | Amplitude | analytics | Behavioural analytics; US-hosted |
| `cdn.jsdelivr.net` | jsDelivr | cdn | Open-source CDN; no PD concern |

---

## Policy / Privacy Page Analysis

> _Findings are heuristic only. Text analysis does not constitute a legal compliance assessment._

**URL:** https://example-corp.ru/privacy-policy
**Document type:** HTML page
**Parse status:** parsed ✓
**Operator (inferred):** ООО «Пример Корп»
**Contacts found:** privacy@example-corp.ru, +7 (495) 000-11-22

| Section | Present |
|---|---|
| Purpose / goals | yes |
| Personal data categories | yes |
| Legal basis | yes |
| Third-party processors | yes |
| Cross-border transfers | — |
| Data subject rights | yes |
| Retention / destruction | — |
| Localization (152-FZ) | yes |

**Signals:**
- Purpose/goals section found
- Personal data categories section found
- Legal basis section found
- Third-party processor/transfer section found
- Data subject rights section found
- Data localization statement found (possible 152-FZ reference)

---

## Downstream Processor Map

> Source labels: `observed_submit` = scanner-observed network request;
> `inferred_public_signal` = derived from DOM/scripts; `operator_supplied` = provided by operator.

| Processor | Type | Source | Confidence | Evidence |
|---|---|---|---|---|
| Yandex Metrica | analytics | inferred_public_signal | high | Script tag `mc.yandex.ru` detected on 6 pages |
| Meta Pixel | ad_tech | inferred_public_signal | high | Script `connect.facebook.net` on 4 pages |
| Amplitude | analytics | inferred_public_signal | medium | XHR to `api.amplitude.com` observed |

---

## 152-FZ Public Evidence Summary

> **Disclaimer:** This assessment is based solely on publicly observable site behavior and
> heuristic analysis. It does not constitute legal advice or a definitive compliance
> determination under 152-FZ. All findings require manual validation by a qualified specialist.

### Overall Public Risk Level: 🟡 MEDIUM

**Operator (inferred from policy page):** ООО «Пример Корп»
**Policy publicly available:** yes
**Privacy links found across site:** 7 pages
**Forms collecting personal data:** 3 forms
**Detected personal data categories:** email, full_name, phone, date_of_birth, address, password
**Consent mechanism type:** explicit_checkbox

### Policy Section Coverage

| Section | Present |
|---|---|
| Purpose / goals | yes |
| Personal data categories | yes |
| Legal basis | yes |
| Third-party processors | yes |
| Cross-border transfers | — |
| Data subject rights | yes |
| Retention / destruction | — |
| Localization (152-FZ Art. 18.1) | yes |

### Processing & Routing

- Processor map present: yes (3 entries)
- Third-party routing detected: yes
- Observed form submission: no (synthetic submission not enabled)
- Metrics / tracking present: yes (Yandex Metrica, Amplitude, Meta Pixel)

### Potential Public-Signal Gaps

> All items below require manual validation. These are heuristic signals, not legal determinations.

1. Cross-border data transfer section not detected in public policy — Meta Pixel (US) and Amplitude (US) are present; cross-border transfer clause may be required.
2. Data retention / destruction section not detected in public policy.
3. Metrics and tracking tools are present; cookie consent / analytics disclosure may be required.

### Manual Validation Checklist

- [ ] Verify operator legal identity (INN/OGRN/full legal name) from public registry.
- [ ] Verify public policy is complete, current, and authored by a qualified specialist.
- [ ] Review consent mechanisms: confirm checkboxes are not pre-ticked and consent is granular.
- [ ] Validate DPA agreements exist with all identified third-party processors.
- [ ] Clarify cross-border data transfer practices: Meta Pixel (US) and Amplitude (US) detected.
- [ ] Define and document personal data retention and destruction procedures.
- [ ] Verify tracking/analytics cookie consent disclosure on site.

---

## Recommended Manual Follow-up

> _These findings are based on automated public-site observation. Manual review is recommended for:_

- Pages with third-party form submission targets
- Forms where consent relies on bundled / implied text rather than explicit checkboxes
- Policy pages missing cross-border transfer and retention sections
- High-risk data categories (password collected — verify storage is hashed)
- Meta Pixel and Amplitude presence with no cross-border transfer clause in policy

---

_Generated by PD Scanner. All findings are heuristic. This report is a starting point for manual analysis, not a legal opinion._
