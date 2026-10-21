# Generating query variations for a new niche

Google Maps result quality depends heavily on query diversity. Use this pattern for any niche+city:

## 1. Generic queries (3-5)
- `"<niche Arabic term> <city>"` — e.g. `"مكاتب محاماة القاهرة"`
- `"<niche English term> <city> <country>"` — e.g. `"law firm Cairo Egypt"`
- A specialization variant — e.g. `"محاماة قضايا أسرة القاهرة"` for family-law firms specifically
- A certified/professional qualifier if relevant to the niche — e.g. `"محامي معتمد"`, `"عيادة أسنان معتمدة"`

## 2. One query per major district/neighborhood of the city
List every well-known district (ask the user, or recall common ones for major Egyptian/Gulf cities) and run `"<niche short term> <district>"` for each — e.g. `"مكتب ترجمة سموحة"`. This surfaces hyper-local businesses the generic city-wide query misses because Maps only returns a capped result count per search.

**Always geo-validate afterward** (see `scripts/discover.py --parse`). Sparse districts make Google Maps silently widen the search radius to other cities or even other countries — this is routine, not a bug, and the geo-filter catches it every time. Do not skip it.

## 3. Niche-keyword list for the relevance filter
Pick 4-8 words/stems that would appear in ANY real business of this niche, in Arabic and English, e.g.:
- Translation: `ترجم,translat,مترجم,localiz,interpret`
- Law firms: `محام,law,legal,محاماة,attorney`
- Dental: `أسنان,dental,dentist,تقويم`

Google Maps keyword search also surfaces tangential matches that share category/location text with the real niche (government offices, religious buildings, cultural centers, visa/consulate services, directory/aggregator pages instead of an owned site). After the keyword filter, **manually scan the printed exclusion list once** — the filter catches most of these, but transliterated names (a real business whose name doesn't contain the Arabic/English root, e.g. "Atarjamat") can slip through as false negatives, and ambiguous category overlaps (a cultural center that also does translation) need a human call, not a silent auto-exclude.

## 4. Stopping condition
Keep adding district/specialization queries until 2-3 consecutive new queries add zero new unique businesses (by CID dedup) within the already-covered geography. Don't stop at an arbitrary query count — the `MAX_LEADS` target in SKILL.md is about total unique businesses, not queries run.

## Known city bounding boxes (lat_min,lat_max,lng_min,lng_max) for `discover.py --parse`
- Alexandria, Egypt: 30.9,31.45,29.6,30.3
- Cairo, Egypt (incl. Giza/Nasr City/New Cairo/Maadi): 29.8,30.3,31.0,31.6
- Riyadh, Saudi Arabia: 24.4,25.0,46.4,47.0
- Jeddah, Saudi Arabia: 21.3,21.8,39.0,39.4

For a city not listed, get an approximate bounding box by checking a known landmark's coordinates on Google Maps and padding ~0.3 degrees in each direction (roughly a 30km radius, enough to cover sprawl without admitting neighboring cities).
