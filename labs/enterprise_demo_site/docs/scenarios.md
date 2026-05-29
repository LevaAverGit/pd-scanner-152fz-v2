# PD Scanner Test Scenarios

## Profile Overview

The lab supports three compliance profiles, switchable at runtime without restart:

```bash
curl -X POST http://localhost:8001/api/profile/good_compliance
curl -X POST http://localhost:8001/api/profile/mixed_compliance
curl -X POST http://localhost:8001/api/profile/bad_compliance
```

---

## Scenario 1: good_compliance

### What it signals to PD Scanner

**Consent:** Explicit checkbox on all forms with link to privacy policy.
Text: "Я даю согласие на обработку персональных данных в соответствии с Политикой конфиденциальности".
`checkbox_present = 1`, `consent_type = explicit_checkbox`.

**Privacy policy:** Present in footer, all 8 sections complete:
1. Цели обработки
2. Категории ПДн
3. Правовые основания (ст. 6 152-ФЗ)
4. Третьи лица и обработчики (named: АналитикаСервис, КРМ Системы, ИП Вебхук)
5. Трансграничная передача
6. Права субъектов
7. Сроки хранения (3 года)
8. Локализация (ст. 18.1 152-ФЗ)

**Routing:** First-party only. `routing_events.route_type = first_party`, `destination = internal_db`.

**Tracking:** No tracking pixel. Cookie banner shown with privacy link.

**Policy files:** PDF and DOCX available at /privacy.pdf and /privacy.docx.

### Expected PD Scanner result
- Compliance score: HIGH
- No missing consent mechanisms
- Policy completeness: 8/8 sections
- No undisclosed third-party routing
- No tracking pixel

---

## Scenario 2: mixed_compliance

### What it signals to PD Scanner

**Consent:** Bundled text (no checkbox). Example: "Отправляя форму, вы соглашаетесь с Политикой конфиденциальности."
`checkbox_present = 0`, `consent_type = bundled_text`.

**Privacy policy:** Present but incomplete:
- Sections present: 1, 2, 3, 4 (vague — "партнёрские сервисы"), 6, 7 (partial)
- Missing: Section 5 (трансграничная передача), Section 8 (локализация)

**Routing:** First-party + webhook. `routing_events` contains both `internal_db` and `webhook_mock` destinations.

**Tracking:** Cookie banner present but no privacy link in banner. No tracking pixel.

**Hidden form fields:** `_crm_source` and `_form_platform` hidden inputs on request-demo form.

### Expected PD Scanner result
- Compliance score: MEDIUM
- Consent mechanism: bundled (not explicit)
- Policy completeness: 6/8 sections (missing cross-border transfers, localization)
- Secondary routing detected: webhook endpoint
- Third-party processors partially disclosed

---

## Scenario 3: bad_compliance

### What it signals to PD Scanner

**Consent:** Absent. No consent text, no checkbox on any form.
`consent_type = absent`, `checkbox_present = 0`.

**Privacy policy:** Not linked in footer. Not linked on forms.
Minimal sections visible (only 1, 2, 6 — no legal basis, no third-party disclosure, no retention, no localization).

**Routing:** Third-party CRM. `routing_events.route_type = third_party_crm`, `destination = http://localhost:8001/crm/mock`.
`processor_events` contains `MockCRM` entry with `crm_api_post_observed`.

**Tracking:** Tracking pixel present (`/mock/pixel.gif`). CRM SDK loaded (`/mock/crm.js`).
Forms have `data-crm-capture` attribute (CRM form-capture SDK pattern).
Hidden inputs: `_crm_source`, `_form_platform`.

**Footer:** Privacy policy link absent. Privacy contact absent.

### Expected PD Scanner result
- Compliance score: LOW / FAIL
- Consent mechanism: absent
- Privacy policy: not linked from forms
- Policy completeness: 3/8 sections
- Third-party CRM routing without disclosure
- Tracking pixel detected
- CRM SDK script detected

---

## Running PD Scanner Against the Lab

```bash
# 1. Start the lab
cd labs/enterprise_demo_site
make run

# 2. Switch to desired profile
make profile-bad   # or profile-good, profile-mixed

# 3. Run PD Scanner (from main app directory)
# Configure PD Scanner target to http://localhost:8001

# 4. After scan, check DB via admin panel
# http://localhost:8001/admin/submissions
```

## Verifying Synthetic Submission Results

After PD Scanner submits a test form:
- Check `routing_events` to see where data was routed
- Check `consent_events` to see consent type captured
- Check `processor_events` to see which processors received data
- All accessible at http://localhost:8001/admin/
