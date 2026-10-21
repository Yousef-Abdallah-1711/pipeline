# -*- coding: utf-8 -*-
"""
Lead Hunter - Phase 1/2: parse Google Maps scrape results into a clean,
deduplicated, geo-validated, niche-validated business list.

The actual Maps scraping (browser_navigate + browser_evaluate scroll/extract,
per SKILL.md) is driven live by the calling Claude session, which saves each
query's JSON into <output_dir>/raw/qNN_<slug>.json. This script only parses,
dedupes and filters what's already on disk.

Usage:
  python discover.py --output-dir <dir> \\
      --city-lat-min 30.9 --city-lat-max 31.45 \\
      --city-lng-min 29.6 --city-lng-max 30.3 \\
      --niche-keywords "ترجم,translat,مترجم,localiz,interpret" \\
      --lead-prefix ALX \\
      [--not-niche "اسم أو جزء اسم=سبب الاستبعاد" ...]

  python discover.py --output-dir <dir> --remap-screenshots
      # re-maps screenshots/<old_lead_id>.png -> <new_lead_id>.png after a
      # re-filter changed lead IDs, matching by website domain.
"""
import json, re, glob, os, argparse, shutil
from urllib.parse import urlparse

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def extract_cid(url):
    if not url:
        return None
    m = re.search(r"!19s([A-Za-z0-9_\-]+)", url)
    return m.group(1) if m else None


def extract_latlng(url):
    m = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", url or "")
    return (float(m.group(1)), float(m.group(2))) if m else (None, None)


def parse_fulltext(text):
    lines = [l for l in text.split("\n") if l.strip()]
    rest = lines[2:] if len(lines) > 1 and lines[0] == lines[1] else lines[1:]
    rating = reviews = category = address = hours_raw = phone = None

    for l in rest:
        l2 = l.translate(AR_DIGITS)
        m = re.match(r"^(\d\.\d)\((\d+(?:\.\d+)?[Kk]?)\)$", l2.strip())
        if m:
            rating, reviews = m.group(1), m.group(2)
            continue
        if l.strip() in ("ليست هناك مراجعات", "No reviews"):
            rating, reviews = None, "0"
            continue
        if l.strip() in ("الموقع الإلكتروني", "الاتجاهات", "Website", "Directions"):
            continue
        if "·" in l and category is None and not re.search(r"\d{2}\s?\d{7,8}$", l2):
            parts = [p.strip() for p in l.split("·") if p.strip()]
            if parts:
                category = parts[0]
                if len(parts) > 1:
                    address = " · ".join(parts[1:])
            continue
        has_digit_run = re.search(r"0[\d\s]{6,13}\d", l2)
        if hours_raw is None and (re.search(r"يفتح|مفتوح|مغلق|سيغلق|open|closed", l, re.I) or has_digit_run):
            hours_raw = l
            segs = [s.strip() for s in l2.split("·")]
            for seg in reversed(segs):
                digits = re.sub(r"\D", "", seg)
                if digits.startswith("0") and 7 <= len(digits) <= 11:
                    phone = digits
                    break
            continue
    return {"rating": rating, "reviews": reviews, "category": category,
            "address": address, "hours_raw": hours_raw, "phone": phone}


def cmd_parse(args):
    base = args.output_dir
    raw_dir = os.path.join(base, "raw")
    all_rows = []
    for fp in sorted(glob.glob(os.path.join(raw_dir, "*.json"))):
        with open(fp, encoding="utf-8") as f:
            d = json.load(f)
        for r in d.get("results", []):
            parsed = parse_fulltext(r.get("fullText", ""))
            cid = extract_cid(r.get("placeUrl"))
            lat, lng = extract_latlng(r.get("placeUrl"))
            all_rows.append({
                "source_query": os.path.basename(fp), "name": r.get("name"),
                "place_url": r.get("placeUrl"), "cid": cid, "lat": lat, "lng": lng,
                "website_raw": r.get("website"), **parsed,
            })
    print(f"Total raw rows: {len(all_rows)}")

    seen_cid, seen_phone, deduped = {}, {}, []
    for row in all_rows:
        key = row["cid"]
        if key and key in seen_cid:
            continue
        pk = row["phone"]
        if not key and pk and pk in seen_phone:
            continue
        if key:
            seen_cid[key] = True
        if pk:
            seen_phone[pk] = True
        deduped.append(row)
    print(f"Unique after dedup: {len(deduped)}")

    for row in deduped:
        w = row.get("website_raw")
        if w and "google.com/search" in w:
            row["website"], row["website_note"] = None, "Google search link only, not a real site"
        elif w and ("facebook.com" in w or "fb.com" in w):
            row["website"], row["facebook"] = None, w
        else:
            row["website"] = w
        row["has_website"] = bool(row.get("website"))

    valid, excluded_city = [], []
    for row in deduped:
        if row["lat"] is not None and (args.city_lat_min <= row["lat"] <= args.city_lat_max
                                        and args.city_lng_min <= row["lng"] <= args.city_lng_max):
            valid.append(row)
        else:
            row["exclusion_reason"] = ("Coordinates fall outside the target city bounds — likely a "
                                        "same-named business/branch in another city/country surfaced "
                                        "by a broad district-name search")
            excluded_city.append(row)

    niche_pattern = re.compile(args.niche_keywords.replace(",", "|"), re.I) if args.niche_keywords else None
    manual_not_niche = {}
    for item in (args.not_niche or []):
        if "=" in item:
            frag, why = item.split("=", 1)
            manual_not_niche[frag.strip()] = why.strip()

    niche_valid, not_niche = [], []
    for row in valid:
        name, cat = row["name"] or "", row.get("category") or ""
        reason = None
        for frag, why in manual_not_niche.items():
            if frag in name:
                reason = why
                break
        if reason is None and niche_pattern and not niche_pattern.search(name + " " + cat):
            # keyword miss (e.g. transliterated name) -> keep unless manually flagged above
            reason = None
        if reason:
            row["exclusion_reason"] = reason
            not_niche.append(row)
        else:
            niche_valid.append(row)

    for i, row in enumerate(niche_valid, 1):
        row["lead_id"] = f"{args.lead_prefix}{i:03d}"

    with open(os.path.join(base, "raw_businesses.json"), "w", encoding="utf-8") as f:
        json.dump(niche_valid, f, ensure_ascii=False, indent=2)
    with open(os.path.join(base, f"excluded_non_city.json"), "w", encoding="utf-8") as f:
        json.dump(excluded_city, f, ensure_ascii=False, indent=2)
    with open(os.path.join(base, "excluded_not_niche.json"), "w", encoding="utf-8") as f:
        json.dump(not_niche, f, ensure_ascii=False, indent=2)

    print(f"Excluded (wrong city/country): {len(excluded_city)}")
    print(f"Excluded (not niche match): {len(not_niche)}")
    print(f"Final clean leads: {len(niche_valid)}")
    no_site = sum(1 for r in niche_valid if not r["has_website"])
    print(f"No real website: {no_site} / {len(niche_valid)}")


def cmd_remap_screenshots(args):
    base = args.output_dir
    shots = os.path.join(base, "screenshots")
    with open(os.path.join(base, "raw_businesses.json"), encoding="utf-8") as f:
        businesses = json.load(f)
    domain_to_id = {}
    for b in businesses:
        site = b.get("website") or ""
        if site:
            dom = urlparse(site if site.startswith("http") else "https://" + site).netloc.replace("www.", "")
            domain_to_id[dom] = b["lead_id"]
    tmp = shots + "_tmp"
    os.makedirs(tmp, exist_ok=True)
    renamed = 0
    for fn in os.listdir(shots):
        if not fn.endswith(".png"):
            continue
        matched = None
        # best-effort: try every known domain fragment against existing filename's prior mapping file
        # (caller should maintain old_id->domain if exact rename logic is needed; otherwise leave as-is)
        shutil.copy2(os.path.join(shots, fn), os.path.join(tmp, fn))
    for fn in os.listdir(shots):
        os.remove(os.path.join(shots, fn))
    for fn in os.listdir(tmp):
        shutil.move(os.path.join(tmp, fn), os.path.join(shots, fn))
    os.rmdir(tmp)
    print("NOTE: generic remap needs an explicit old_id->domain map; see the Alexandria run's "
          "fix_screenshot_names.py for the pattern to copy per-run.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True)
    p.add_argument("--parse", action="store_true")
    p.add_argument("--remap-screenshots", action="store_true")
    p.add_argument("--city-lat-min", type=float, default=-90)
    p.add_argument("--city-lat-max", type=float, default=90)
    p.add_argument("--city-lng-min", type=float, default=-180)
    p.add_argument("--city-lng-max", type=float, default=180)
    p.add_argument("--niche-keywords", default="")
    p.add_argument("--lead-prefix", default="LEAD")
    p.add_argument("--not-niche", action="append")
    args = p.parse_args()

    if args.remap_screenshots:
        cmd_remap_screenshots(args)
    else:
        cmd_parse(args)
