# Discovery sources — availability and access rules

| Source | Status in this environment | Access method | Notes |
|---|---|---|---|
| Google Maps (browser-driven) | **Available** | Live `browser_navigate` + `browser_evaluate` scroll/extract (see SKILL.md Phase 1) | Primary source. Public listing data only (name, address, phone, rating, review count, website link). No login, no CAPTCHA bypass. |
| Google Places API (Text Search + Place Details) | **Conditionally available** | `scripts/sources.py` → `GooglePlacesAPISource`, used automatically when `GOOGLE_PLACES_API_KEY` is set in env | Checked fresh each run — never assume a key exists; `scripts/sources.py` reports `unavailable: no API key configured` and falls back to the Maps browser method when absent. |
| Company's own website | **Available** | `audit.py` real HTTP fetch | Used both for the technical audit and for B2B/operational-complexity signals (careers page, branch count, dealer/portal language) — see `audit.py`'s `b2b_signals` block. |
| LinkedIn company pages / employee profiles | **Not implemented as an automated adapter** | — | LinkedIn requires an authenticated session for most profile/company data and its ToS restricts automated collection. Bypassing that is explicitly against this skill's hard rules (no authwall/CAPTCHA bypass). **Manual workflow instead:** search `site:linkedin.com/company <business name>` and open the result yourself if you need a decision-maker's public title; do not script this. |
| Egyptian business/industry directories (chambers of commerce, exporter directories, trade-fair exhibitor lists) | **Not implemented** | — | No specific directory was verified in this run as both (a) actually covering this niche/region and (b) permitting automated collection. Inventing a directory name or URL is explicitly forbidden. If you have a specific directory in mind, add it as a new `DiscoverySource` subclass in `scripts/sources.py` (see the `ManualDirectorySource` stub for the interface) once you've confirmed its ToS allows it. |
| Public search engines (for growth/hiring/expansion signals) | **Available, but manual** | `WebSearch` tool, used selectively per-lead, not as a bulk adapter | Bulk-querying a search engine programmatically risks ToS violations; this skill uses it only for targeted, low-volume, per-lead verification (e.g. confirming a claimed new facility), not as a primary discovery adapter. |

## Why this matters for the data you get back

Every lead's `evidence` block states which of the above sources actually contributed to it. A lead with only "Google Maps (browser-driven)" as a source has NOT been cross-verified against its own website or any other source — check `audit.reachable` before trusting anything beyond name/phone/address for that lead.

## Adding a new source

Subclass `DiscoverySource` in `scripts/sources.py`:

```python
class MySource(DiscoverySource):
    name = "my_source"

    def available(self) -> tuple[bool, str]:
        # return (True, "") if usable right now, else (False, "<reason>")
        ...

    def search(self, query: str, limit: int = 50) -> list[dict]:
        # return normalized records: {"name", "source_url", "raw", ...}
        ...
```

`available()` must do a real check (env var present, endpoint reachable) — never hardcode `True`.
