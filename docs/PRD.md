# PD Scanner — Product Requirements Document

## Purpose

PD Scanner is an internal tool for privacy and compliance consultants. Given the URL of a public registration or sign-up page, it renders the page in a headless browser, extracts every visible and hidden form field, classifies each field into a recognized personal data category, and presents the findings in a structured report. The goal is to make GDPR/CCPA gap analysis of third-party or client sign-up flows fast and auditable without manual inspection.

## Goals

- Scan a public URL and extract all form fields (labels, input types, names, placeholders)
- Classify fields into personal data categories (name, email, phone, address, DOB, government ID, etc.)
- Display findings in a clear web UI with scan history
- Export findings as JSON and Markdown for use in audit reports

## Non-Goals

- No form submission of any kind
- No CAPTCHA bypass or circumvention
- No authentication bypass (login-gated pages are out of scope)
- No mass crawling or link following — single-URL scans only
- No real personal data is entered, stored, or transmitted

## Users

- Privacy consultants performing third-party vendor assessments
- Data Protection Officers (DPOs) auditing client registration flows
- Compliance teams preparing GDPR/CCPA data mapping inventories

## Core Features (Phased)

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Project skeleton, FastAPI app with health endpoint, docs baseline | Complete |
| 2 | SQLite persistence, full CRUD API (scan create/get/list/delete) | Complete |
| 3 | Playwright scanner: DOM extraction, PD classification, screenshot, network metadata, exports | Complete |
| 4 | React/TS/Vite/Tailwind frontend: dashboard, scan details, history, export download | Complete |
| 5 | Tests (API + classifier), docs alignment | Complete |
| 6 | Security hardening: SSRF blocklist, CORS lockdown, rate limiting, path controls | Planned |
| 7 | Final integration pass, demo readiness | Planned |

## Data Categories (Implemented)

The following 12 personal data categories are implemented in `backend/app/utils/pd_dictionary.py`:

| Category | GDPR Reference | Example Fields |
|---|---|---|
| full_name | Art. 4(1) | name, first_name, last_name, surname |
| email | Art. 4(1) | email, e-mail, mail |
| phone | Art. 4(1) | phone, mobile, tel, telephone |
| date_of_birth | Art. 4(1) | dob, birth, birthday, birthdate |
| address | Art. 4(1) | address, street, city, postcode, zip |
| national_id | Art. 87 | ssn, passport, national_id, tax_id |
| gender | Art. 9 | gender, sex, salutation |
| username | Art. 4(1) | username, login, handle, nickname |
| password | Art. 32 | password, passwd, pin |
| financial | Art. 9 | iban, credit_card, cvv, billing |
| health | Art. 9(1) | health, medical, disability, allergy |
| ip_address | Recital 30 | ip, ip_address, ipv4 |

Classification uses word-boundary-aware keyword matching (not substring matching) to avoid false positives.

## Limitations and Assumptions

- The tool operates on pages that render without login; authenticated pages will not yield complete results.
- JavaScript-heavy SPAs are supported via Playwright's full render, but pages with aggressive bot detection may fail to load completely.
- Classification accuracy depends on field labels and name attributes; obfuscated or unlabeled fields may be categorized as unclassified.
- All data remains on the local machine; there is no telemetry, cloud storage, or remote reporting.
- The tool is designed for single-user local use and has no multi-tenancy or access control.
