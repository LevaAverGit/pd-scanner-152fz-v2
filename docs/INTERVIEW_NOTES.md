# Interview Notes

Talking points for presenting this project in an interview.
This project touches 152-FZ, so the framing is deliberately careful: it is a **technical
pre-screening tool**, never a legal or compliance verdict. See `docs/LIMITATIONS.md` for
the authoritative scope statement — this file does not restate or expand those limits.

---

## 30-second pitch

> I built a local-first technical pre-screening tool that crawls the public pages of a
> website and flags visible signals related to personal-data collection — forms,
> third-party requests, privacy-policy presence, consent checkboxes. It separates evidence
> into observed / inferred / operator-supplied, runs behind an SSRF guard, and produces a
> structured report for a human reviewer. It is not a legal audit and does not guarantee
> 152-FZ compliance.

---

## 60-second technical explanation

- **Crawler:** a headless browser (Playwright) loads each public page and collects
  evidence from the rendered DOM — form fields, outbound third-party requests, links to a
  privacy policy, consent checkboxes.
- **Why Playwright:** many sites render content and fire tracking requests via JavaScript;
  raw HTML would miss them. Playwright captures the page as a browser actually renders it.
- **Why local-first:** the tool runs on the operator's own machine against sites they are
  authorized to check. Nothing is sent to a third-party service, which keeps the evidence
  and the target list private.
- **Evidence separation:** `observed` = directly seen on the page; `inferred` = derived
  from a heuristic signal; `operator-supplied` = provided by the user, not discovered.
  Keeping these distinct is what stops the report from overclaiming.
- **SSRF guard:** before fetching any URL the tool resolves the host and rejects internal,
  loopback, and link-local ranges and non-HTTP(S) schemes, so it cannot be pointed at
  internal infrastructure. See `docs/THREAT_MODEL.md`.
- **No legal conclusions:** the report lists signals and evidence for a human reviewer; it
  never outputs "compliant" or "non-compliant."

---

## What this project demonstrates

- Secure crawling with an explicit SSRF guard
- SSRF-aware design and trust-boundary thinking
- Evidence modeling with a confidence/source distinction
- Structured report generation for downstream human review
- Careful scope control and overclaim avoidance
- Full-stack engineering (FastAPI backend, frontend, async scan lifecycle)
- Privacy/compliance-adjacent technical thinking, kept on the technical side of the line

---

## What this project does NOT do

- Does not provide legal advice
- Does not guarantee compliance with 152-FZ
- Does not replace a lawyer or a DPO
- Does not replace a formal audit
- Does not contact Roskomnadzor
- Does not scan private or internal systems without authorization

---

## Files to show during interview

| Interview topic | File to show | What to explain |
|---|---|---|
| Evidence model | `docs/EVIDENCE_MODEL.md` | observed / inferred / operator-supplied and confidence |
| Scope and limits | `docs/LIMITATIONS.md` | The authoritative "what it is / is not" and legal-scope table |
| SSRF guard | `docs/THREAT_MODEL.md` | Trust boundaries and how internal targets are rejected |
| Crawler | `docs/DATA_FLOW.md` | URL → crawler → classification → report pipeline |
| Sample output | `sample_reports/` | What a real report looks like — evidence, not verdicts |
| Tests | `docs/QUALITY_ASSURANCE.md` | Test strategy and DB isolation |

---

## Likely questions and short (careful) answers

1. **Why did you build this project?**
   To practice secure crawling, evidence modeling, and careful scope control on a problem
   where overclaiming would be harmful — privacy signals on public sites.

2. **Is this a legal compliance tool?**
   No. It is a technical pre-screening tool. It surfaces signals for a human reviewer and
   makes no legal determination.

3. **What does "technical pre-screening" mean?**
   It collects and structures publicly visible evidence before a qualified person does the
   actual assessment — it narrows where a reviewer should look, nothing more.

4. **How do you avoid overclaim?**
   The report only lists evidence, never a compliance verdict, and every finding is tagged
   observed / inferred / operator-supplied so the reader knows how strong each signal is.

5. **How does SSRF protection work?**
   Before any fetch, the target host is resolved and internal/loopback/link-local ranges
   and non-HTTP(S) schemes are rejected, so the crawler can't reach internal services.

6. **Why Playwright?**
   To capture JavaScript-rendered content and dynamically fired third-party requests that
   raw HTML parsing would miss.

7. **What is observed vs inferred evidence?**
   Observed is directly present on the page (a visible form field). Inferred is derived
   from a heuristic (a request pattern suggesting analytics). They are kept separate.

8. **What would you improve in a real team?**
   Clearer authorization/scoping workflow, broader signal coverage, reviewer-facing
   tooling, and tighter calibration of the heuristics with real reviewer feedback.

9. **What are the main limitations?**
   Public pages only, no server-side visibility, heuristic and non-definitive signals,
   and it stops at authentication barriers. The full list is in `docs/LIMITATIONS.md`.

10. **How did you test it?**
    With pytest and isolated test databases; the test strategy is in
    `docs/QUALITY_ASSURANCE.md`. The crawler tests avoid hitting live external sites.

---

## Phrases to avoid

- "guarantees 152-FZ compliance"
- "legal audit"
- "full compliance scanner"
- "automated legal assessment"
- "this site is compliant / non-compliant"
- "Roskomnadzor-ready conclusion"

---

## Good closing explanation

> This project demonstrates technical security and privacy-engineering thinking — secure
> crawling, SSRF-aware design, careful evidence modeling, and disciplined scope control.
> It is a pre-screening aid for a human reviewer, not legal expertise and not a compliance
> verdict.
