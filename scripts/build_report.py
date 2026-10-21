# -*- coding: utf-8 -*-
"""
Lead Hunter - Phase 6: fill templates/report.html with this run's data and
write <output_dir>/leads-report.html (+ leads.csv next to it).

Usage: python build_report.py --output-dir <dir> \\
    --page-title "رادار عملاء <المدينة>" \\
    --h1 "<الفئة> في <المدينة>" \\
    --intro "..." (optional, a sensible default is generated if omitted)
"""
import json, os, time, csv, argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "..", "templates", "report.html")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True)
    p.add_argument("--page-title", default="رادار عملاء محتملين")
    p.add_argument("--h1", default="تقرير العملاء المحتملين")
    p.add_argument("--intro", default=None)
    args = p.parse_args()
    base = args.output_dir

    with open(os.path.join(base, "raw_businesses.json"), encoding="utf-8") as f:
        businesses = json.load(f)
    with open(os.path.join(base, "scores.json"), encoding="utf-8") as f:
        scores = json.load(f)
    with open(os.path.join(base, "audits.json"), encoding="utf-8") as f:
        audits = json.load(f)
    with open(os.path.join(base, "sales_pack.json"), encoding="utf-8") as f:
        packs = json.load(f)

    def load_or_empty(name):
        fp = os.path.join(base, name)
        if os.path.exists(fp):
            with open(fp, encoding="utf-8") as f:
                return json.load(f)
        return []

    excluded_city = load_or_empty("excluded_non_city.json")
    excluded_niche = load_or_empty("excluded_not_niche.json")

    shots_dir = os.path.join(base, "screenshots")
    screenshotted = set()
    if os.path.isdir(shots_dir):
        screenshotted = {fn[:-4] for fn in os.listdir(shots_dir) if fn.endswith(".png")}

    leads = []
    for b in businesses:
        lid = b["lead_id"]
        leads.append({**b, "score": scores.get(lid, {}), "audit": audits.get(lid, {}),
                      "pack": packs.get(lid, {}), "has_screenshot": lid in screenshotted})

    tier_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for l in leads:
        if l["score"].get("tier") in tier_counts:
            tier_counts[l["score"].get("tier")] += 1
    no_website_count = sum(1 for l in leads if not l.get("has_website"))
    rts = [l["audit"].get("server_response_time_s") for l in leads if l["audit"].get("server_response_time_s") is not None]
    avg_rt = round(sum(rts) / len(rts), 2) if rts else None

    cards = [
        (len(leads), "إجمالي العملاء (بعد التحقق من المدينة والمجال)"),
        (tier_counts["A"], "أولوية A"), (tier_counts["B"], "أولوية B"),
        (tier_counts["C"], "أولوية C"), (tier_counts["D"], "أولوية D"),
        (no_website_count, "بدون موقع إلكتروني حقيقي"),
        (f"{avg_rt if avg_rt is not None else '—'}s", "متوسط وقت استجابة الخادم (قياس حقيقي)"),
        (len(excluded_city), "تم استبعادهم (مدينة أخرى)"),
        (len(excluded_niche), "تم استبعادهم (خارج المجال)"),
    ]
    cards_html = "\n".join(
        f'      <div class="card"><div class="n">{v}</div><div class="l">{l}</div></div>' for v, l in cards)

    intro = args.intro or (
        f"تم اكتشاف العملاء عبر خرائط جوجل وفحص كل موقع إلكتروني حقيقي وجدناه ببيانات مقاسة فعليًا. "
        f"تاريخ الإصدار: {time.strftime('%Y-%m-%d')}. بيانات PageSpeed Insights (Lighthouse) لم تُستخدم في "
        f"هذا التقرير (غالبًا محظورة بدون مفتاح API) — لا توجد أي أرقام LCP/CLS مُختلقة؛ "
        f'"وقت استجابة الخادم" أدناه قياس حقيقي بديل، وليس بديلاً كاملاً عن Lighthouse.')

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()

    html = (template
            .replace("__PAGE_TITLE__", args.page_title)
            .replace("__PAGE_H1__", args.h1)
            .replace("__PAGE_INTRO__", intro)
            .replace("__CARDS_HTML__", cards_html)
            .replace("__DATA_JSON__", json.dumps(leads, ensure_ascii=False)))

    with open(os.path.join(base, "leads-report.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote leads-report.html, length: {len(html)}")

    headers = ["lead_id", "name", "category", "address", "phone", "rating", "reviews",
               "website", "facebook", "has_website", "reachable", "score", "tier", "status", "notes"]
    rows = []
    for b in businesses:
        lid = b["lead_id"]
        s, a = scores.get(lid, {}), audits.get(lid, {})
        rows.append({
            "lead_id": lid, "name": b["name"], "category": b.get("category") or "غير متوفر",
            "address": b.get("address") or "غير متوفر", "phone": b.get("phone") or "غير متوفر",
            "rating": b.get("rating") or "غير متوفر", "reviews": b.get("reviews") or "0",
            "website": b.get("website") or "غير متوفر", "facebook": b.get("facebook") or "",
            "has_website": "نعم" if b.get("has_website") else "لا",
            "reachable": "نعم" if a.get("reachable") else ("لا" if a.get("audited") else "غير مطبق"),
            "score": s.get("total_score", ""), "tier": s.get("tier", ""), "status": "جديد", "notes": "",
        })
    with open(os.path.join(base, "leads.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote leads.csv with {len(rows)} rows")


if __name__ == "__main__":
    main()
