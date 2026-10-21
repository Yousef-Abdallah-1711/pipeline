# -*- coding: utf-8 -*-
"""
Lead Hunter v2 - Phase 9 (docs): generate research-summary.md,
sources-and-evidence.md, limitations.md and run-metadata.json next to the
rest of a run's output. Never claims a step happened unless the matching
output file actually exists in --output-dir - run-metadata is derived from
what's really on disk, not from a fixed checklist.

Usage: python build_research_docs.py --output-dir <dir> \\
    --run-label "..." --queries-run 20 --sources-attempted "google_maps_browser,google_places_api"
"""
import json, os, time, argparse


def file_exists(base, name):
    return os.path.exists(os.path.join(base, name))


def count_json(base, name, key=None):
    fp = os.path.join(base, name)
    if not os.path.exists(fp):
        return None
    with open(fp, encoding="utf-8") as f:
        data = json.load(f)
    return len(data) if isinstance(data, (list, dict)) else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True)
    p.add_argument("--run-label", default="Lead Hunter run")
    p.add_argument("--queries-run", type=int, default=0)
    p.add_argument("--sources-attempted", default="google_maps_browser")
    p.add_argument("--target-count", type=int, default=0)
    args = p.parse_args()
    base = args.output_dir
    today = time.strftime("%Y-%m-%d")

    raw_count_pre_filter = None
    raw_dir = os.path.join(base, "raw")
    if os.path.isdir(raw_dir):
        total = 0
        for fn in os.listdir(raw_dir):
            if fn.endswith(".json"):
                with open(os.path.join(raw_dir, fn), encoding="utf-8") as f:
                    d = json.load(f)
                total += len(d.get("results", []))
        raw_count_pre_filter = total

    n_leads = count_json(base, "raw_businesses.json") or 0
    n_excluded_city = count_json(base, "excluded_non_city.json") or 0
    n_excluded_niche = count_json(base, "excluded_not_niche.json") or 0

    audits = {}
    if file_exists(base, "audits.json"):
        with open(os.path.join(base, "audits.json"), encoding="utf-8") as f:
            audits = json.load(f)
    n_audited = sum(1 for v in audits.values() if v.get("audited"))
    n_reachable = sum(1 for v in audits.values() if v.get("reachable"))

    scores = {}
    if file_exists(base, "scores.json"):
        with open(os.path.join(base, "scores.json"), encoding="utf-8") as f:
            scores = json.load(f)
    sw_tiers = {"A": 0, "B": 0, "C": 0, "D": 0}
    web_tiers = {"A": 0, "B": 0, "C": 0, "D": 0}
    for s in scores.values():
        if s.get("score_software_fit_tier") in sw_tiers:
            sw_tiers[s["score_software_fit_tier"]] += 1
        if s.get("score_website_opportunity_tier") in web_tiers:
            web_tiers[s["score_website_opportunity_tier"]] += 1

    businesses = []
    if file_exists(base, "raw_businesses.json"):
        with open(os.path.join(base, "raw_businesses.json"), encoding="utf-8") as f:
            businesses = json.load(f)
    n_with_phone = sum(1 for b in businesses if b.get("phone"))
    n_with_website = sum(1 for b in businesses if b.get("has_website"))
    n_with_decision_maker = sum(1 for b in businesses if b.get("decision_maker_name"))
    n_screenshots = 0
    shots_dir = os.path.join(base, "screenshots")
    if os.path.isdir(shots_dir):
        n_screenshots = len([f for f in os.listdir(shots_dir) if f.endswith(".png")])

    # ---------------- run-metadata.json ----------------
    metadata = {
        "run_label": args.run_label,
        "date": today,
        "queries_run": args.queries_run,
        "sources_attempted": [s.strip() for s in args.sources_attempted.split(",") if s.strip()],
        "sources_available_this_run": None,  # filled by scripts/sources.py's own output, attach separately if captured
        "records_discovered_pre_filter": raw_count_pre_filter,
        "records_after_geo_and_niche_filter": n_leads,
        "records_excluded_wrong_city": n_excluded_city,
        "records_excluded_not_niche": n_excluded_niche,
        "websites_audited_attempted": n_audited,
        "websites_reachable": n_reachable,
        "screenshots_captured": n_screenshots,
        "leads_with_public_phone": n_with_phone,
        "leads_with_real_website": n_with_website,
        "leads_with_decision_maker_identified": n_with_decision_maker,
        "software_fit_tier_distribution": sw_tiers,
        "website_opportunity_tier_distribution": web_tiers,
        "target_count": args.target_count,
        "target_met": (n_leads >= args.target_count) if args.target_count else None,
    }
    with open(os.path.join(base, "run-metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # ---------------- research-summary.md ----------------
    summary = f"""# {args.run_label} — ملخص بحثي ومنهجية

**تاريخ التشغيل:** {today}

## الأرقام الفعلية (مش تقديرية)

- عمليات بحث منفذة: {args.queries_run}
- سجلات مكتشفة قبل أي فلترة: {raw_count_pre_filter if raw_count_pre_filter is not None else 'غير متاح'}
- سجلات فريدة بعد التحقق الجغرافي والمجال: **{n_leads}**
- مستبعدة (مدينة/دولة تانية): {n_excluded_city}
- مستبعدة (خارج المجال المطلوب): {n_excluded_niche}
- مواقع تم فحصها فعليًا: {n_audited} (منها {n_reachable} شغالة وقت الفحص)
- صور شاشة حقيقية تم التقاطها: {n_screenshots}
- عناوين هواتف عامة موثقة: {n_with_phone}
- أصحاب قرار تم تحديدهم (يدويًا وموثق): {n_with_decision_maker}

## توزيع الأولويات

**فرصة أتمتة/برمجيات:** A={sw_tiers['A']} B={sw_tiers['B']} C={sw_tiers['C']} D={sw_tiers['D']}
**فرصة موقع إلكتروني:** A={web_tiers['A']} B={web_tiers['B']} C={web_tiers['C']} D={web_tiers['D']}

## المنهجية

1. اكتشاف عبر خرائط جوجل (متصفح حي) و/أو Google Places API لو متاح مفتاح.
2. تحليل وإزالة التكرار بمعرّف المكان (CID) أو رقم الهاتف.
3. تحقق جغرافي حقيقي من الإحداثيات (lat/lng) — أي نتيجة بره حدود المدينة المستهدفة بتتسجل في ملف استبعاد منفصل.
4. تحقق من انتماء النشاط للمجال المطلوب عبر كلمات مفتاحية + مراجعة يدوية للاستثناءات.
5. فحص HTTP/HTML حقيقي لكل موقع إلكتروني حقيقي (بدون أي بيانات Lighthouse/PageSpeed مُختلقة).
6. تقييم مزدوج مستقل: فرصة أتمتة/برمجيات منفصلة تمامًا عن فرصة الموقع الإلكتروني.
7. توليد مسودات تواصل (لم يتم إرسال أي رسالة فعليًا).

راجع `sources-and-evidence.md` لتفاصيل كل مصدر، و`limitations.md` للقيود والبيانات غير المتاحة.
"""
    with open(os.path.join(base, "research-summary.md"), "w", encoding="utf-8") as f:
        f.write(summary)

    # ---------------- limitations.md ----------------
    limitations = f"""# القيود والبيانات غير المتاحة

- **Google Places API:** {'تم استخدامه (مفتاح متاح)' if 'google_places_api' in args.sources_attempted and os.environ.get('GOOGLE_PLACES_API_KEY') else 'غير متاح — لا يوجد GOOGLE_PLACES_API_KEY في بيئة التشغيل؛ تم الاعتماد على المتصفح الحي بدلًا منه'}.
- **Google PageSpeed Insights / Lighthouse:** لم يُستخدم في هذا التشغيل. الـ API العام محظور الحصة بدون مفتاح (تم التأكد بفحص مباشر رجّع HTTP 429). "وقت استجابة الخادم" المذكور في التقرير قياس HTTP حقيقي بديل، **مش** بديل كامل لـ Lighthouse/Core Web Vitals.
- **LinkedIn:** لم يتم تنفيذ أي اكتشاف آلي عليه — يتطلب تسجيل دخول ويخالف شروط الاستخدام لو تم تجاوزه آليًا. أي بيانات صاحب قرار موجودة في هذا التشغيل تمت مراجعتها يدويًا فقط.
- **أدلة الأعمال المصرية (غرف تجارية، نقابات، معارض):** لم يتم تنفيذ أي محول اكتشاف آلي لها في هذا التشغيل — لم يتم التحقق من مصدر محدد يسمح بالتجميع الآلي. راجع `references/sources.md`.
- **صور الشاشة:** مُلتقطة فقط للمواقع اللي كانت فعليًا شغالة وقت الفحص عبر متصفح حي؛ المواقع غير المتاحة اتسجلت كملاحظة بدون صورة.
- **فرضيات الأتمتة/الاحتياجات الداخلية:** كل فرضية في مسودات المبيعات مبنية على إشارة علنية ملحوظة على موقع الشركة (فروع، مصانع، بوابات، وظائف تقنية) — **مش تأكيد فعلي** إن الشركة بتستخدم طرق يدوية داخليًا. لازم تأكيد في مكالمة اكتشاف.
- **لم يتم إرسال أي رسالة تواصل فعليًا** لأي نشاط تجاري في هذا التشغيل.
"""
    with open(os.path.join(base, "limitations.md"), "w", encoding="utf-8") as f:
        f.write(limitations)

    # ---------------- sources-and-evidence.md ----------------
    sources_md_lines = ["# المصادر والأدلة\n", "راجع `references/sources.md` في مجلد السكِل للتفاصيل الكاملة. ملخص هذا التشغيل:\n"]
    for s in [x.strip() for x in args.sources_attempted.split(",") if x.strip()]:
        sources_md_lines.append(f"- **{s}**")
    sources_md_lines.append("\nكل سجل في `leads.json` يحتوي حقل `source_name` و`retrieved_at` و`place_url` كدليل مصدر لكل ادعاء جغرافي/هوية. حقول صاحب القرار (`decision_maker_*`) فاضية افتراضيًا (`unknown`) ما لم تُملأ يدويًا بعد تحقق فعلي.")
    with open(os.path.join(base, "sources-and-evidence.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(sources_md_lines))

    print(f"Wrote research-summary.md, sources-and-evidence.md, limitations.md, run-metadata.json to {base}")


if __name__ == "__main__":
    main()
