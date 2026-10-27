---
name: lead-hunter-website-audit
description: Run a full, evidence-backed audit for one supplied website URL and produce a complete offline HTML report, source/evidence record, remediation roadmap, and a client-ready Egyptian Arabic PDF. Invoke through lead-hunter with the `website-audit` command and a supplied URL.
---

# Website Audit Sub-skill

Use this sub-skill when the user supplies one website URL and asks for a full review, client report, audit PDF, or the `website-audit` command. This is a single-site audit workflow; do not run Google Maps lead discovery or score the organization as a sales lead.

## Command

Preferred invocation:

```text
/lead-hunter website-audit https://example.com
```

The same route may be invoked naturally, for example: “اعمل تدقيق كامل للموقع ده وجهّز التقرير والـPDF للعميل: https://example.com”. If the user gives the URL without a command name but clearly asks for a complete website audit, use this workflow.

The command runner is `scripts/run_site_audit.py`. When this skill is installed in the lead-hunter folder, run:

```text
python <lead-hunter-skill-folder>/scripts/run_site_audit.py https://example.com
```

It needs Python packages from `requirements-site-audit.txt` and Playwright Chromium. If unavailable, install them from the skill folder with `python -m pip install -r requirements-site-audit.txt` and `python -m playwright install chromium`; do not silently replace the crawl with a hand-picked sample. To rebuild reports after editing `audit-data.json`, run `python <lead-hunter-skill-folder>/scripts/run_site_audit.py --from-data <output-folder>/audit-data.json`.

Use the URL as the audit target. Normalize its domain, preserve the supplied canonical route, and verify redirects before assigning the output slug. If no output location is specified, create `website-audits/<domain-slug>/<UTC-run-time>/` in the current workspace. Do not overwrite an existing audit run: the runner creates a new dated folder automatically.

## Deliverables

Produce a reviewable package with these default files:

- `index.html` — complete offline audit report. It includes the executive summary, all findings retained after review, severity and priority, a row for every discovered page, source references, screenshots, method, scope, and limitations. Keep it with its adjacent `evidence/` folder so images work offline.
- `client-brief.pdf` — a separate client-facing summary with up to the 10 most important verified findings, real screenshot evidence, plain-language business/customer impact, cautious search visibility implications, and an actionable next step for each. Never add filler findings to reach ten.
- `audit-summary.md` — concise overall conclusions and the assessment scope.
- `implementation-roadmap.md` — prioritized fixes, dependencies, and practical sequencing; distinguish recommendations from completed work.
- `audit-data.json` — machine-readable structured record of the site, pages, findings, evidence, measurements, and source references.
- `sources-and-method.md` — source URL, access date/time and timezone, what was checked, and what could not be verified.
- `evidence/` — genuine captures and machine-readable artifacts used to support findings. Keep filenames linked to finding IDs, such as `F-01-mobile-overflow.png`.

Keep all deliverables for one run together. Link the PDF and the full HTML report from a short README if the package contains additional artifacts. Do not claim a report or screenshot exists until it has been written and checked.

## Workflow

1. **Crawl the public site.** Run `scripts/run_site_audit.py` with no page cap by default. It discovers URLs from available sitemap files and recursively rendered internal links, follows public JavaScript-rendered pages, and records every unique same-site HTML URL it attempts. It checks `robots.txt`, records blocked and failed URLs, and captures desktop and mobile viewport screenshots for each page that responds. Do not replace this run with a representative-page sample. A page cap is allowed only when requested or required to bound a very large site, and the report must mark coverage incomplete.
2. **Review coverage and evidence.** Compare discovered, reviewed, failed, non-HTML, redirected, and robots-blocked counts. Review the per-page data and screenshots for every crawled page, including its visible text, title, headings, links, forms, image alternatives, mobile overflow, and load timing. Add manually observed findings only when screenshots or page evidence support them. Do not claim coverage of orphan URLs absent from the sitemap and public internal links, login-protected routes, infinite app states, or pages blocked by robots/access controls. These limits must be visible in the report.
3. **Check relevant areas.** Inspect responsive layout, page clarity and navigation, performance evidence available in the environment, accessibility signals, forms/contact paths, page titles/headings/meta, indexability hints, sitemap/robots, structured data, broken resources and links, and HTTPS/security headers as relevant. Use source HTML/network evidence or a named measurement tool to support technical claims. Check current search guidance against official Google Search Central documentation when making claims about current Google behavior.
4. **Classify every finding.** Give it a stable ID, short title, severity/priority, affected URL(s), evidence reference(s), confidence, what was observed, likely customer/business effect, search visibility relevance, recommended action, and implementation effort when supportable. Clearly label measured facts, visual observations, hypotheses, and recommendations. Explain causal uncertainty; never promise traffic, ranking, lead, or revenue gains without client analytics that support them.
5. **Build the full report and data.** Make `audit-data.json` the source of truth for the HTML report and PDF so the facts and counts agree. The runner produces a first-pass JSON, full HTML, client PDF, summary, roadmap, source/method file, and page screenshots. Review `audit-data.json`, remove false positives, add supported manual findings and authoritative references, then regenerate the package with `--from-data`. The JSON should preserve run metadata and timezone; target/canonical URL; discovered, reviewed, failed, and skipped routes; tools and measurement settings; finding records; screenshot/evidence paths; source references; limitations; and the PDF's selected finding IDs.
6. **Write for the intended reader.** Default the client brief to professional, natural Egyptian Arabic when the client is in Egypt or the user asks for Egyptian Arabic. Explain technical terms in plain language. Keep source names, URLs, measured values, and unavoidable product/brand names exact. A fuller technical appendix may use standard technical terminology, but should still explain why each item matters.
7. **Create and visually inspect the PDF.** Use a reliable HTML-to-PDF or PDF workflow with correct Arabic shaping and right-to-left layout. Include actual evidence screenshots, legible labels, and source references. Render every PDF page to images and inspect the entire set for reversed/malformed text, mixed-direction number errors, overlap, clipping, overflow beyond page boundaries, missing screenshots, and footer collisions. Fix and render again before delivery.
8. **Review consistency and package.** Reconcile all counts across JSON, HTML, Markdown, and PDF; confirm every reported issue has evidence and every PDF item exists in the full report. Confirm the `all_discoverable_public_pages` coverage flag and call out any skips or cap. Open the local HTML, check links/navigation and console output when possible, reopen and render every PDF page, verify Arabic text and that all content stays within page bounds, then remove temporary render files. Finish with links to both client-ready PDF and complete HTML plus a short description of scope and limitations.

## Evidence and reporting rules

- Prefer direct evidence from the audited site and authoritative documentation. Keep a source URL adjacent to each externally sourced claim. Do not treat an earlier audit, another company, or a generated mockup as current evidence.
- Use screenshots captured from the real site as evidence. Never synthesize a website screenshot, fabricate a browser result, or edit away a defect. Cropping for legibility is fine if the full capture is retained alongside it.
- If PageSpeed Insights, Lighthouse, CrUX, analytics, or an accessibility scanner is unavailable, state that plainly and do not substitute an invented score. Label lab measurements, field measurements, and manually observed behavior separately.
- The runner supports static sites, common CMS sites, and public JavaScript-rendered apps by using Chromium. It is an HTML-page crawler, not a universal crawler of private dashboards, API-only screens, content behind authentication, or interactive states that require submitting data. Record those exclusions instead of claiming every possible application state was covered.
- A technical finding may have an indirect or uncertain SEO effect. Say so. Avoid categorical claims that an issue causes a specific ranking loss unless the evidence and a current authoritative source establish it.
- Do not estimate lost sales, conversion rate, or ROI without client-specific data. Describe potential friction or an opportunity and recommend how the client can measure the result after implementation.
- Keep private or sensitive user data out of captures and reports. Do not include credentials, session tokens, or personal information unrelated to the public business website.
- Keep outreach separate. This audit prepares evidence and recommendations; it never sends email, WhatsApp, forms, or other messages.

## Suggested finding record

```json
{
  "id": "F-01",
  "title": "Short, plain-language finding",
  "severity": "high",
  "status": "verified",
  "category": "mobile-usability",
  "affected_urls": ["https://example.com/page"],
  "observation": "What was directly measured or seen",
  "evidence": ["evidence/F-01-mobile.png"],
  "sources": ["https://example.com/page"],
  "confidence": "high",
  "customer_business_impact": "Evidence-based potential effect, not an invented outcome",
  "search_impact": "Direct, indirect, none, or unknown, with rationale",
  "recommendation": "A concrete next action",
  "effort": "medium"
}
```

Adjust categories and fields to the target site, but preserve stable IDs and explicit evidence, status, and uncertainty. If a finding cannot be reproduced or supported, move it to an unverified follow-up note or omit it from the client PDF.
