# Lead Hunter v2 — gap analysis & upgrade plan (Egypt B2B software/automation vertical)

## What already works (v1, committed 0f7510d)
- Maps-driven discovery via live browser automation (no Places API key available in this environment — confirmed again, `env | grep -i google/places/api_key` empty).
- `discover.py --parse`: dedup by CID/phone, geo-bounding-box validation, single-keyword-list niche filter.
- `audit.py`: real HTTP/HTML checks (HTTPS, mixed content, viewport, bilingual, form/file-upload, WhatsApp/tel, title/meta, H1, structured data, sitemap, copyright year, platform, real response time). No Lighthouse/PSI anywhere.
- `score.py`: single 0-100 score (business strength 40 + website weakness 50 + contactability folded in), tiers A-D.
- `build_sales_packs.py`: translation-office-specific Arabic templates, hook selection by single most severe finding.
- `build_report.py` + `templates/report.html`: RTL HTML report, sortable/filterable table, detail panel, localStorage status/notes, CSV/JSON export.

## What's missing for this vertical (Egyptian B2B software/automation prospects)
1. **Single score conflates two different things**: "bad website" and "needs internal software" are not the same signal. v1's score can't express that.
2. **No decision-maker / evidence-provenance fields**: v1's business record has no owner/role, no per-claim source URL, no verified/inferred/unknown labeling.
3. **No operational-complexity signal detection**: v1's audit only looks at marketing-site basics (form, whatsapp, bilingual). Nothing looks for branches/warehouses/dealer-portal/careers-ERP-hiring signals that actually indicate operational complexity.
4. **No industry playbooks**: v1 has one generic niche-keyword list. This vertical needs per-industry query templates, disqualifiers, and discovery questions.
5. **No multi-source architecture**: v1 is Maps-only. LinkedIn and most Egyptian business directories require authenticated access or are not reliably scrapable without violating ToS — these stay **documented as unavailable/manual**, not faked. What's realistically addable without credentials: the company's **own website** as a second real evidence source (careers page, branch count, portal presence) — already partially covered by `audit.py`, extended here.
6. **No automated tests.** Added a minimal real suite (stdlib `unittest`, no network, no fixtures requiring credentials).
7. **Sales packs are translation-office-specific wording.** Generalized to an industry-agnostic software/automation angle, with a `--vertical` switch so the original translation-office wording isn't deleted, just no longer the only option.

## Decisions made
- Implement the **dual-score model** (Score A: software/digitization fit, Score B: website opportunity) exactly as specified, superseding v1's single score. v1's single `total_score`/`tier` fields are kept for backward compatibility (derived as a simple combination) so nothing downstream silently breaks.
- LinkedIn and third-party Egyptian directories: **not implemented as automated adapters**. Logging in or scraping LinkedIn profile pages violates the explicit "do not bypass access controls / authwalls" rule and LinkedIn's ToS; this is documented in `references/sources.md` as an honest limitation, with a manual-research procedure instead of a fake adapter that would silently return nothing or violate ToS.
- Added `scripts/sources.py`: a small adapter interface (`DiscoverySource` base class) with two real, usable implementations (`GoogleMapsBrowserSource` — a thin wrapper documenting the live browser_evaluate procedure already in `SKILL.md`; `GooglePlacesAPISource` — real Places API calls, auto-skips with a clear message when no key is set) and one explicitly-stubbed `ManualDirectorySource` that always reports itself unavailable rather than pretending to scrape a directory I haven't verified is legitimately accessible.
- Kept everything backward compatible: a v1 run's `raw_businesses.json`/`audits.json` still work with the new `score.py`; the new fields are additive.
