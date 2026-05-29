# 152-FZ Compliance Checklist

This checklist maps the signals the scanner collects to the specific
requirements and articles of Federal Law No. 152-FZ "On Personal Data"
(Федеральный закон № 152-ФЗ «О персональных данных»).

All items are assessed based on **publicly observable evidence only**
(HTTP responses, page content, form fields, privacy policy text, network requests).
This checklist does not produce legal conclusions. Each item requires manual
validation before any compliance decision can be made.

---

## Operator Identification (Art. 18.1)

| Signal | What scanner checks | Article | Gap if absent |
|---|---|---|---|
| Privacy policy publicly accessible | Detects links containing "privacy", "policy", "персональные данные", "конфиденциальность" | Art. 18.1 | No public policy — **high priority gap** |
| Operator identity in policy | Looks for organization name, INN/OGRN patterns in policy text | Art. 18.1(1) | Operator legal identity unclear |
| Policy language | Checks if policy is present (language detection is out of scope) | Art. 8(1) | — |

---

## Consent and Legal Basis (Art. 6, Art. 9)

| Signal | What scanner checks | Article | Gap if absent |
|---|---|---|---|
| Explicit consent checkbox on data-collection forms | Detects `<input type="checkbox">` with consent-related labels near forms | Art. 6(1)(1), Art. 9(1) | No documented consent mechanism |
| Bundled/implied consent text | Detects text patterns like "нажимая кнопку, вы соглашаетесь" | Art. 9(1) | Implied consent — adequacy requires legal review |
| Marketing consent checkbox | Separate checkbox for marketing/newsletter consent | Art. 15 | No separate marketing consent |
| Consent mechanism classification | Classifies as: explicit_checkbox / bundled_text / weak_or_absent / mixed / unknown | — | — |

---

## Privacy Policy Content (Art. 14, Art. 18.1)

| Section | What scanner checks | Article |
|---|---|---|
| Purpose / processing goals | Keyword patterns: цели обработки, цель сбора, processing purposes | Art. 14(2)(2) |
| Personal data categories | Keyword patterns: категории персональных данных, types of data | Art. 14(2)(3) |
| Legal basis | Keyword patterns: правовое основание, legal basis | Art. 14(2)(1) |
| Third-party / processor disclosure | Keyword patterns: третьи лица, передача данных, operators, processors | Art. 14(2)(5) |
| Cross-border transfer | Keyword patterns: трансграничная передача, cross-border | Art. 12 |
| Data subject rights | Keyword patterns: права субъекта, право на доступ, право на удаление | Art. 14 |
| Retention and destruction | Keyword patterns: сроки хранения, уничтожение, retention period | Art. 21 |
| Data localization statement | Keyword patterns: хранение на территории РФ, localization | Art. 18.1(5) |

---

## Third-Party Routing and Processors (Art. 6(4), Art. 12)

| Signal | What scanner checks | Article | Gap if absent |
|---|---|---|---|
| Third-party JS includes | Detects external scripts (Yandex Metrica, Google Analytics, Facebook Pixel, etc.) | Art. 6(4) | Third parties receiving data without disclosed basis |
| Processor map | Classifies vendors by category: analytics, ad_tech, CDN, payment, CRM | Art. 6(4) | Processor list not established |
| Cross-border indicator | Third-party vendors with non-RU IP ranges or known foreign operators | Art. 12 | Cross-border transfer may not be documented |

---

## Data Localization (Art. 18.1(5))

| Signal | What scanner checks | Gap if not addressed |
|---|---|---|
| Localization statement in policy | Keyword pattern in policy text | Policy does not address localization requirement |
| Server geolocation | Out of scope — infrastructure scan required separately | — |
| Third-party processors' jurisdiction | Inferred from vendor classification; not authoritative | Cross-border transfer safeguards unclear |

---

## Operator Registration (Roskomnadzor Registry)

| Signal | What scanner checks | Note |
|---|---|---|
| Registration with RKN | Out of scope — requires API check against РКН registry | Must be verified manually |
| INN/OGRN in policy | Looks for patterns matching Russian tax ID formats | Aids operator identification |

---

## What This Scanner Does NOT Cover

| Item | Why it is out of scope |
|---|---|
| Actual PD stored or processed | Scanner does not access databases or backend systems |
| Consent record storage | Scanner cannot verify that collected consents are stored and retrievable |
| DPA (data processing agreements) | Internal contracts are not publicly observable |
| Encryption of stored data | Requires infrastructure access |
| Access control for PD systems | Requires authenticated access |
| Incident response procedures | Internal documents, not publicly observable |
| RKN registration status | Requires separate registry API query |
| Legal conclusions | All output is heuristic; legal analysis requires a qualified lawyer |

---

## Limitations

- All checks are based on publicly observable signals at the time of scan.
- Scanner output should be treated as a starting point for manual review.
- A "gap detected" result does not confirm non-compliance. Additional controls
  not visible to the scanner may exist.
- A "no gap detected" result does not confirm compliance. Required documentation
  may exist but not be publicly accessible.
- This checklist covers the most common heuristic signals. It is not a complete
  audit methodology for 152-FZ compliance.
