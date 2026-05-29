# PD Scanner — Limitations and Scope

This document clearly defines what PD Scanner does and does not do.
Understanding these limitations is required for responsible use.

---

## What PD Scanner Is

A **technical pre-screening tool** that:
- Crawls publicly accessible web pages of a given site
- Identifies visible signals that suggest personal data collection
- Classifies those signals against 152-FZ data categories
- Produces a structured evidence report for further review

All analysis is **heuristic**, **public-signal-based**, and **non-definitive**.

---

## Legal Scope

| Claim | Status |
|---|---|
| Guarantees 152-FZ compliance | ❌ Not possible — PD Scanner does not make legal determinations |
| Replaces a legal compliance audit | ❌ Never — legal audits require qualified specialists |
| Constitutes an official Roskomnadzor inspection result | ❌ Completely out of scope |
| Can determine if an operator has violated 152-FZ | ❌ Too many unobservable factors |
| Identifies potential risk indicators for manual review | ✅ This is the intended use |
| Provides structured evidence for a human reviewer | ✅ This is the intended use |

---

## Technical Scope

**The scanner can observe:**
- Form fields on publicly reachable pages (names, emails, phone numbers, etc.)
- Outbound network requests to third-party domains (analytics, CRM, payment processors)
- Privacy policy pages reachable via links from the scanned site
- Presence or absence of privacy consent checkboxes
- Standard policy section headings (data subject rights, retention period, etc.)

**The scanner cannot observe:**
- What happens to data after it is submitted — server-side processing is invisible
- Whether the operator has a valid Data Processing Agreement with processors
- Whether user consents are stored correctly
- Whether data is transferred cross-border in practice
- What the site does when JavaScript is executed — Playwright captures rendered pages, not raw HTML
- Login-gated pages — crawling stops at authentication barriers
- Server configuration, databases, or internal APIs
- Whether stated policies match actual data handling practices

---

## Crawler Constraints

- **Depth:** Maximum 20 pages per scan (bounded BFS, same-host only)
- **Scope:** Only pages reachable from the seed URL without authentication
- **Speed:** Rate-limited to avoid overwhelming the target server
- **No form submission:** The scanner does not submit real personal data into forms
- **No CAPTCHA bypass:** Stops if CAPTCHA is encountered
- **No JavaScript execution of untrusted scripts:** Playwright renders pages but does not follow arbitrary JS redirects off-domain

---

## Security Constraints

- **SSRF protection:** All target URLs are resolved and checked against RFC 1918
  (10.x, 172.16–31.x, 192.168.x), loopback (127.x), link-local (169.254.x),
  and non-HTTP(S) schemes before any request is sent
- **No credential scanning:** The tool does not attempt to authenticate to any service
- **Local-only database:** All scan results are stored in a local SQLite file — no remote storage
- **No data sent externally:** The tool does not communicate with any external API during scanning

---

## Intended Use Cases

✅ Preliminary technical screening before a formal compliance audit  
✅ Identifying pages that likely collect personal data for further manual review  
✅ Academic research or educational demonstration of 152-FZ compliance signals  
✅ Developer self-assessment of a site under development  

---

## Not Intended For

❌ Legal proceedings or regulatory submissions  
❌ Claiming that a site is compliant (scanner passes) or non-compliant (scanner flags)  
❌ Replacing a qualified DPO (Data Protection Officer) review  
❌ Commercial compliance certification services  

---

## Required Follow-Up

Every PD Scanner report should be treated as **input to a human review process**, not as a final conclusion.

Recommended next steps after a scan:
1. Review flagged pages manually in a browser
2. Test form submission behavior (with consent)
3. Engage a qualified legal specialist or DPO for interpretation
4. Cross-reference with the operator's internal data processing register

---

*For technical details about what the scanner detects, see `docs/EVIDENCE_MODEL.md`.*  
*For the SSRF guard implementation, see `docs/THREAT_MODEL.md`.*
