# lead-hunter

A Claude Code skill for autonomous local-business lead generation: discover real businesses in a niche + city via Google Maps (or the Places API when a key exists), audit every real website they have with **measured** (never invented) data, score **two independent opportunities per lead**, and draft ready-to-review outreach — all without ever auto-sending anything.

## Two scores, on purpose

A weak website does not prove a company needs internal software, and a great website does not rule it out. Every lead gets:
- **`score_software_fit`** (0-100) — custom software/automation opportunity, from public operational-complexity signals (branches, warehouses, dealer/distributor language, B2B portals, tech hiring).
- **`score_website_opportunity`** (0-100) — the original website-quality/marketing-site opportunity.

Each component of each score ships with a one-line reason, and every "opportunity hypothesis" in a sales pack is phrased as a hypothesis ("ممكن", "فرصة محتملة"), never a confirmed internal fact — see `tests/test_score.py`'s `TestDualScoreIndependence` for the regression test that enforces this.

## What it does

1. **Discover** — Google Places API when `GOOGLE_PLACES_API_KEY` is set (`scripts/sources.py`), otherwise drives Google Maps with a browser tool, across generic + per-district/per-industry queries (`references/industry-playbooks.md`, `scripts/query_templates.py`).
2. **Parse & validate** — dedupes by Maps place ID/phone, geo-validates against the target city's real bounding box, filters out businesses that don't match the niche (`scripts/discover.py`).
3. **Audit** — real HTTP/HTML checks per website: HTTPS, mixed content, mobile viewport, bilingual content, contact form/file upload, WhatsApp/tel links, title/meta quality, structured data, sitemap, platform, real measured server response time, **and** B2B operational signals (multi-branch/warehouse/dealer-portal/quote-request language, careers-page tech hiring) (`scripts/audit.py`). **No Lighthouse/PageSpeed scores are ever fabricated.**
4. **Score** — the dual model above (`scripts/score.py`), tiers A-D (A 80+, B 65-79, C 45-64, D <45) on each score independently.
5. **Sales packs** — two verticals (`--vertical b2b_software` default, or `translation`): summary, up to 3 evidence-backed hypotheses, evidence gaps, likely buyer role, a WhatsApp opener (≤5 lines, no price), an email, follow-ups, call opener + objections, discovery questions, and a price range that **requires a discovery call** instead of a guess whenever there's no scale signal to justify one (`scripts/build_sales_packs.py`).
6. **Report + docs** — one self-contained RTL HTML report with both scores, a detail panel, copy buttons, a `wa.me` link that opens but never sends, `localStorage` status/notes, CSV/JSON export (`scripts/build_report.py` + `templates/report.html`), plus `run-metadata.json` / `research-summary.md` / `sources-and-evidence.md` / `limitations.md` with every count derived from what's actually on disk (`scripts/build_research_docs.py`).

## Install

Drop this folder into `~/.claude/skills/lead-hunter/` (Claude Code) or `~/.agents/skills/lead-hunter/` (Codex). See `SKILL.md` for the full workflow, hard rules (never invent data, never auto-send, never bypass an authwall/ToS, always checkpoint), and how to adapt it to a new niche or market.

## Optional credentials

- `GOOGLE_PLACES_API_KEY` — if set, `scripts/sources.py` uses the real Places API instead of browser-driven Maps scraping. Entirely optional; the skill works without it (confirmed in every run so far — never assumed present).
- Nothing else is required. LinkedIn and third-party directories are intentionally **not** automated (see `references/sources.md`) — they need either an authenticated session or a verified-permitted source, neither of which this skill fakes.

## Usage

Find leads in a niche and city with a natural-language request, such as a request for food manufacturers in Alexandria and Borg El Arab.

For a complete audit package for one supplied website, use:

```text
/lead-hunter website-audit https://example.com
```

In Codex, invoke the installed skill as `$lead-hunter website-audit https://example.com`.

This creates a full offline HTML audit, structured findings and source records, an implementation roadmap, and a separate client-ready PDF. The single-site route does not run Maps lead discovery or outreach.

Normal lead-generation runs continue to write to `./lead-hunter-output/{niche}-{city}/` next to the current workspace.

## Testing

```
cd ~/.claude/skills/lead-hunter && python -m unittest discover -s tests -v
```

Real `unittest` suite, no network, no credentials required. Covers query generation, Maps-text parsing (including a regression test for a real phone-regex bug this project hit), score boundaries, and the dual-score independence invariant.

## Structure

```
SKILL.md                      # the workflow Claude follows
scripts/
  sources.py                   # discovery source adapter interface (Places API / Maps-browser / directory stub)
  query_templates.py           # Arabic/English query generation per industry playbook
  discover.py                  # parse/dedupe/geo-filter/niche-filter raw Maps scrapes
  audit.py                      # real HTTP/HTML website audit + B2B operational-signal detection
  score.py                      # the dual scoring model (edit per niche/market)
  build_sales_packs.py          # outreach draft generator (--vertical b2b_software | translation)
  build_report.py               # fills templates/report.html, writes leads.csv/leads.json
  build_research_docs.py        # run-metadata.json, research-summary.md, sources-and-evidence.md, limitations.md
templates/
  report.html                   # the interactive HTML report template
references/
  niche-queries.md               # legacy single-niche query-variation guide
  industry-playbooks.md          # Egypt B2B software-prospect playbooks (9 sectors)
  sources.md                     # which discovery sources are actually usable, and why
  upgrade-plan.md                 # v1->v2 gap analysis and design decisions
scripts/run_site_audit.py         # uncapped-by-default public-site crawler + HTML/PDF audit package
requirements-site-audit.txt       # requests and Playwright dependencies for the site-audit runner
subskills/
  website-audit/SKILL.md        # single-site audit command and client-report workflow
tests/
  test_discover.py, test_score.py, test_query_templates.py
```

## License

Not yet specified by the author.
