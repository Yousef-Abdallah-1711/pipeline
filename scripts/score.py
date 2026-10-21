# -*- coding: utf-8 -*-
"""
Lead Hunter - Phase 4: score each lead 0-100 and assign tier A-D.

Opportunity score = how much this business NEEDS a new site AND can afford it.
  Business strength (max 40): reviews (0-20), rating>=4.0 (0-10), contactable (0-10)
  Website weakness  (max 50): no website -> 50; else sum of weighted gaps (max 50)
Tiers: A 75+, B 55-74, C 35-54, D <35.

This rubric is meant to be edited per niche/market directly in this file -
e.g. raise the reviews divisor for a niche where 1000+ reviews is normal,
or change which weakness flags apply (see audit.py's niche-adaptation note).

Usage: python score.py --output-dir <dir> \\
    [--directory-only ID1,ID2,...] [--out-of-niche "ID=reason" ...]
"""
import json, os, argparse


def parse_review_count(s):
    if not s:
        return 0
    s = str(s).replace(",", "")
    if s.upper().endswith("K"):
        try:
            return int(float(s[:-1]) * 1000)
        except Exception:
            return 0
    try:
        return int(float(s))
    except Exception:
        return 0


def score_business(lead_id, businesses, audits, directory_only, out_of_niche):
    b = businesses[lead_id]
    a = audits.get(lead_id, {"audited": False})
    reviews = parse_review_count(b.get("reviews"))
    rating = float(b["rating"]) if b.get("rating") else None

    reviews_pts = min(20, round(reviews / 15)) if reviews else 0
    rating_pts = 10 if (rating and rating >= 4.0) else 0
    contact_pts = 10 if b.get("phone") else 0
    business_strength = reviews_pts + rating_pts + contact_pts

    if not b.get("has_website") or lead_id in directory_only:
        weakness, detail = 50, {"no_website": 50}
    elif not a.get("reachable"):
        weakness, detail = 46, {"site_unreachable": 46}
    else:
        d = {}
        rt = a.get("server_response_time_s", 0)
        d["slow_server_response"] = 12 if rt >= 5 else (6 if rt >= 2.5 else 0)
        d["not_mobile_friendly"] = 0 if a.get("mobile_viewport_tag") else 10
        d["not_bilingual"] = 0 if a.get("bilingual_ar_en") else 8
        d["no_quote_form"] = 0 if a.get("has_form") else 8
        d["no_whatsapp"] = 0 if a.get("has_whatsapp") else 4
        d["no_https_or_invalid"] = 0 if a.get("https_valid") else 4
        year = a.get("copyright_year")
        d["outdated_design_year"] = 4 if (year and int(year) <= 2019) else 0
        weakness, detail = sum(d.values()), d

    total = min(100, business_strength + weakness)
    tier = "A" if total >= 75 else "B" if total >= 55 else "C" if total >= 35 else "D"

    return {
        "lead_id": lead_id, "total_score": total, "tier": tier,
        "business_strength": business_strength,
        "business_strength_detail": {"reviews_pts": reviews_pts, "rating_pts": rating_pts, "contact_pts": contact_pts},
        "website_weakness": weakness, "website_weakness_detail": detail,
        "contactability": contact_pts,
        "flags": {"directory_listing_only": lead_id in directory_only,
                  "out_of_niche": out_of_niche.get(lead_id)},
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True)
    p.add_argument("--directory-only", default="", help="comma-separated lead_ids that are directory/aggregator pages, not an owned site")
    p.add_argument("--out-of-niche", action="append", default=[], help="lead_id=reason, repeatable")
    args = p.parse_args()
    base = args.output_dir

    with open(os.path.join(base, "raw_businesses.json"), encoding="utf-8") as f:
        businesses = {b["lead_id"]: b for b in json.load(f)}
    with open(os.path.join(base, "audits.json"), encoding="utf-8") as f:
        audits = json.load(f)

    directory_only = set(x for x in args.directory_only.split(",") if x)
    out_of_niche = dict(item.split("=", 1) for item in args.out_of_niche if "=" in item)

    scores = {lid: score_business(lid, businesses, audits, directory_only, out_of_niche) for lid in businesses}
    with open(os.path.join(base, "scores.json"), "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)

    ranked = sorted(scores.values(), key=lambda x: -x["total_score"])
    tier_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for s in ranked:
        tier_counts[s["tier"]] += 1
    print("Tier distribution:", tier_counts)
    for s in ranked[:15]:
        print(f"{s['lead_id']} tier {s['tier']} score {s['total_score']:3d}  {businesses[s['lead_id']]['name'][:45]}")


if __name__ == "__main__":
    main()
