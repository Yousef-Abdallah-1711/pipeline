# -*- coding: utf-8 -*-
"""
Lead Hunter v2 - dual scoring: Score A (custom-software/digitization fit)
and Score B (website opportunity) are kept SEPARATE on purpose - a weak
website does not prove a company needs internal software, and a great
website does not rule it out. See references/upgrade-plan.md.

v1 compatibility: `total_score`/`tier` are still written (derived as the
higher of A/B, since that's the more commercially relevant one to sort
by for a mixed-vertical pipeline), so a v1 report template or CSV
consumer keeps working.

Usage: python score.py --output-dir <dir> \\
    [--directory-only ID1,ID2,...] [--out-of-niche "ID=reason" ...]

Tiers (same thresholds for both scores): A 80-100, B 65-79, C 45-64, D <45.
Edit the component weights directly in this file for a different market -
the structure (two independent scores, each with named components and a
one-line reason per component) is the part meant to stay fixed.
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


def tier_for(score):
    return "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 45 else "D"


def score_software_fit(b, a, biz):
    """Score A: custom software / digital-transformation fit, max 100.
    0-25 operational complexity, 0-25 workflow/integration relevance,
    0-15 scale, 0-15 growth/hiring signals, 0-10 contact accessibility,
    0-10 evidence quality/recency."""
    reasons = {}

    b2b = (a or {}).get("b2b_signals", {}) if a else {}
    complexity_hits = sum([
        bool(b2b.get("multi_branch_signal")),
        bool(b2b.get("warehouse_or_factory_signal")),
        bool(b2b.get("b2b_portal_signal")),
        (biz.get("category") or "").strip() != "" and any(
            k in (biz.get("category") or "") for k in ("مصنع", "توزيع", "لوجستيات", "صيانة", "تصدير", "استيراد")),
    ])
    complexity_pts = min(25, complexity_hits * 7)
    reasons["operational_complexity"] = f"{complexity_pts}/25 — {complexity_hits} public complexity signal(s) observed (branches/warehouse/portal/category)"

    relevance_hits = sum([
        bool(b2b.get("b2b_portal_signal")),
        bool(b2b.get("dealer_or_distributor_signal")),
        bool(b2b.get("quote_request_signal")),
    ])
    relevance_pts = min(25, relevance_hits * 9)
    reasons["workflow_relevance"] = f"{relevance_pts}/25 — {relevance_hits} B2B workflow signal(s) (dealer/portal/quote-request language) found on their own site"

    reviews = parse_review_count(biz.get("reviews"))
    rating = float(biz["rating"]) if biz.get("rating") else None
    scale_pts = 15 if reviews >= 100 else (10 if reviews >= 30 else (5 if reviews >= 5 else 0))
    reasons["business_scale"] = f"{scale_pts}/15 — based on {reviews} public Google reviews (a proxy, not a verified revenue/employee figure)"

    growth_pts = 10 if b2b.get("careers_tech_hiring_signal") else 0
    reasons["growth_hiring_signals"] = f"{growth_pts}/10 — " + (
        "careers page mentions a tech/ops/ERP-relevant role" if growth_pts else "no public hiring/expansion signal observed")

    contact_pts = 10 if biz.get("phone") else (5 if biz.get("website") else 0)
    reasons["contact_accessibility"] = f"{contact_pts}/10 — " + ("public phone number available" if biz.get("phone") else ("website only, no public phone" if biz.get("website") else "no reliable contact channel found"))

    evidence_sources = sum([bool(biz.get("website")), bool(a and a.get("reachable")), bool(biz.get("place_url"))])
    evidence_pts = min(10, evidence_sources * 4)
    reasons["evidence_quality"] = f"{evidence_pts}/10 — corroborated by {evidence_sources} independent source(s) (Maps listing / own website / audit)"

    total = complexity_pts + relevance_pts + scale_pts + growth_pts + contact_pts + evidence_pts
    return min(100, total), reasons


def score_website_opportunity(b, a):
    """Score B: website/web-platform opportunity, max 100.
    0-20 website availability/technical condition, 0-15 mobile usability,
    0-20 missing core business functionality, 0-20 missing B2B/customer/
    supplier capability, 0-15 business relevance/scale, 0-10 contact
    accessibility."""
    reasons = {}
    has_site = b.get("has_website")

    if not has_site:
        avail_pts = 20
        reasons["availability"] = "20/20 — no real owned website found (strongest, least ambiguous website-opportunity signal)"
    elif not (a or {}).get("reachable"):
        avail_pts = 18
        reasons["availability"] = "18/20 — listed website does not respond"
    else:
        rt = a.get("server_response_time_s", 0)
        avail_pts = 8 if rt >= 4 else (3 if rt >= 2.5 else 0)
        reasons["availability"] = f"{avail_pts}/20 — reachable, server responded in {rt}s (NOT a Lighthouse/mobile score, see SKILL.md)"

    if has_site and a and a.get("reachable"):
        mobile_pts = 0 if a.get("mobile_viewport_tag") else 15
        reasons["mobile_usability"] = f"{mobile_pts}/15 — " + ("no mobile viewport meta tag detected" if mobile_pts else "mobile viewport tag present")
    else:
        mobile_pts = 15 if has_site else 0
        reasons["mobile_usability"] = f"{mobile_pts}/15 — " + ("site unreachable, cannot confirm mobile support" if has_site else "no site to evaluate")

    if has_site and a and a.get("reachable"):
        missing_core = sum([not a.get("has_form"), not a.get("meta_description_present"), a.get("title_generic", False), a.get("h1_count", 1) == 0])
        core_pts = min(20, missing_core * 5)
        reasons["core_functionality"] = f"{core_pts}/20 — {missing_core} of 4 basics missing/weak (contact form, meta description, page title, H1)"
    else:
        core_pts = 20 if has_site else 10
        reasons["core_functionality"] = f"{core_pts}/20 — " + ("unreachable, cannot evaluate" if has_site else "no site; cannot even assess basics")

    if has_site and a and a.get("reachable"):
        b2b = a.get("b2b_signals", {}) or {}
        missing_b2b = sum([not b2b.get("b2b_portal_signal"), not a.get("has_whatsapp"), not a.get("has_tel_link")])
        b2b_pts = min(20, missing_b2b * 7)
        reasons["b2b_customer_capability"] = f"{b2b_pts}/20 — {missing_b2b} of 3 B2B/contact capabilities missing (customer portal language, WhatsApp, click-to-call)"
    else:
        b2b_pts = 15 if has_site else 15
        reasons["b2b_customer_capability"] = f"{b2b_pts}/20 — cannot evaluate without a reachable site"

    reviews = parse_review_count(b.get("reviews"))
    relevance_pts = 15 if reviews >= 50 else (10 if reviews >= 10 else 5)
    reasons["business_relevance"] = f"{relevance_pts}/15 — based on {reviews} public reviews as a scale proxy"

    contact_pts = 10 if b.get("phone") else 0
    reasons["contact_accessibility"] = f"{contact_pts}/10 — " + ("public phone available" if b.get("phone") else "no public phone found")

    total = avail_pts + mobile_pts + core_pts + b2b_pts + relevance_pts + contact_pts
    return min(100, total), reasons


def score_business(lead_id, businesses, audits, directory_only, out_of_niche):
    b = businesses[lead_id]
    a = audits.get(lead_id, {"audited": False})

    software_score, software_reasons = score_software_fit(b, a if a.get("audited") else None, b)
    website_score, website_reasons = score_website_opportunity(b, a if a.get("audited") else None)

    combined = max(software_score, website_score)

    return {
        "lead_id": lead_id,
        "score_software_fit": software_score,
        "score_software_fit_tier": tier_for(software_score),
        "score_software_fit_reasons": software_reasons,
        "score_website_opportunity": website_score,
        "score_website_opportunity_tier": tier_for(website_score),
        "score_website_opportunity_reasons": website_reasons,
        # v1 compatibility fields:
        "total_score": combined,
        "tier": tier_for(combined),
        "business_strength": None,
        "website_weakness": None,
        "contactability": 10 if b.get("phone") else 0,
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
    tier_counts_sw = {"A": 0, "B": 0, "C": 0, "D": 0}
    tier_counts_web = {"A": 0, "B": 0, "C": 0, "D": 0}
    for s in scores.values():
        tier_counts_sw[s["score_software_fit_tier"]] += 1
        tier_counts_web[s["score_website_opportunity_tier"]] += 1
    print("Software-fit tier distribution:", tier_counts_sw)
    print("Website-opportunity tier distribution:", tier_counts_web)
    for s in ranked[:15]:
        name = businesses[s["lead_id"]]["name"][:40]
        print(f"{s['lead_id']} SW {s['score_software_fit']:3d}({s['score_software_fit_tier']}) "
              f"WEB {s['score_website_opportunity']:3d}({s['score_website_opportunity_tier']})  {name}")


if __name__ == "__main__":
    main()
