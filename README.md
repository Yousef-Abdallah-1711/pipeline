# lead-hunter

A Claude Code skill for autonomous local-business lead generation: discover real businesses in a niche + city via Google Maps, audit every real website they have with **measured** (never invented) data, score opportunity 0-100, and draft ready-to-review outreach — all without ever auto-sending anything.

## What it does

1. **Discover** — finds businesses via the Google Places API (if a key is set) or by driving Google Maps with a browser tool, across generic queries plus one query per city district.
2. **Parse & validate** — dedupes by Maps place ID, geo-validates against the target city's real bounding box (district-name searches routinely pull in same-named branches from other cities), and filters out businesses that don't actually match the niche.
3. **Audit** — real HTTP/HTML checks per website: HTTPS validity, mixed content, mobile viewport tag, bilingual content, contact form / file upload presence, WhatsApp/tel links, title/meta quality, structured data, sitemap, platform, and real measured server response time. **No Lighthouse/PageSpeed scores are ever fabricated** — if the public PSI API is quota-blocked (common without an API key), that's reported explicitly instead of guessing.
4. **Score** — business strength (reviews, rating, contactability) + website weakness (no site, slow, not mobile-friendly, not bilingual, no quote form, no WhatsApp, outdated) → tier A-D.
5. **Sales packs** — per-lead summary, top-3 real problems, business impact in plain language, a WhatsApp opener (≤5 lines, no price, ends with a free-audit offer), an email, three follow-ups, a call opener + objection handling, and a recommended package/price range.
6. **Report** — one self-contained, RTL-aware HTML file with a sortable/filterable leads table, a click-through detail panel (score breakdown, audit findings, screenshot, every drafted message with a copy button and a `wa.me` link that opens but never sends), status/notes persisted to `localStorage`, and CSV/JSON export.

## Install

Drop this folder into `~/.claude/skills/lead-hunter/` (Claude Code) or `~/.agents/skills/lead-hunter/` (Codex). See `SKILL.md` for the full workflow Claude follows, the hard rules it operates under (never invent data, never auto-send, always checkpoint), and how to adapt it to a new niche.

## Usage

> find leads for مكاتب محاماة in القاهرة

or any phrasing matching `SKILL.md`'s description trigger. Output lands in `./lead-hunter-output/{niche}-{city}/` next to wherever you run it — never inside this skill folder.

## Structure

```
SKILL.md                    # the workflow Claude follows
scripts/
  discover.py                # parse/dedupe/geo-filter/niche-filter raw Maps scrapes
  audit.py                    # real HTTP/HTML website audit
  score.py                    # the scoring rubric (edit per niche/market)
  build_sales_packs.py        # outreach draft generator
  build_report.py             # fills templates/report.html with this run's data
templates/
  report.html                  # the interactive HTML report template
references/
  niche-queries.md             # how to generate query variations for any niche/city
```

## License

Not yet specified by the author.
