# -*- coding: utf-8 -*-
"""
Lead Hunter v2 - Phase 5: build a sales pack per lead.

Two verticals, selected with --vertical:
  b2b_software (default) - custom software/automation angle, hypotheses
    derived from audit.py's b2b_signals (branches/warehouse/portal/careers
    hiring). This is the general-purpose default for the Egypt B2B
    software-client prospecting use case.
  translation - the original translation-office website-selling angle
    (kept verbatim for backward compatibility with earlier runs).

Every "opportunity" a b2b_software pack states is phrased as a hypothesis
("ممكن", "فرصة محتملة") derived from an OBSERVED signal, never asserted as
a verified fact about the company's internal workflow - score.py's
b2b_signals are public-website observations, not an audit of their actual
operations. Pricing falls back to "يتطلب تحديد عبر مكالمة اكتشاف" (requires
a discovery call) whenever there isn't a clear scale signal to justify a
range - never a guessed number.

Usage: python build_sales_packs.py --output-dir <dir> \\
    --vertical b2b_software --service "..." --my-name "..." --my-company "..." \\
    --my-phone "..." --my-email "..." \\
    --price-low "..." --price-mid "..." --price-high "..." --currency "جنيه"
"""
import json, os, argparse


def money_range_or_discovery(score_entry, args):
    """Price only when a clear scale signal justifies it; otherwise say so."""
    sw = score_entry.get("score_software_fit", 0)
    web = score_entry.get("score_website_opportunity", 0)
    best = max(sw, web)
    if best >= 65:
        return f"{args.price_high} {args.currency} (نطاق أولي لمشروع بالحجم ده — يتطلب تأكيد عبر مكالمة اكتشاف قبل أي عرض سعر نهائي)"
    if best >= 45:
        return f"{args.price_mid} {args.currency} (نطاق أولي تقديري — يتطلب تحديد عبر مكالمة اكتشاف)"
    return "السعر يتطلب تحديد عبر مكالمة اكتشاف أولًا؛ الأدلة المتاحة حاليًا مش كفاية لتقدير نطاق موثوق."


def build_software_pack(lead_id, b, a, s, args):
    name = b["name"]
    b2b = (a.get("b2b_signals") or {}) if a.get("audited") else {}

    hypotheses, missing_info = [], []

    if b2b.get("multi_branch_signal") or b2b.get("warehouse_or_factory_signal"):
        hypotheses.append("فرصة محتملة لربط الفروع/المخازن في نظام واحد لمتابعة المخزون والطلبات بدل التنسيق اليدوي بينهم — ده افتراض مبني على إشارة عامة في موقعكم، محتاج تأكيد في مكالمة قصيرة.")
    if b2b.get("dealer_or_distributor_signal") and not b2b.get("b2b_portal_signal"):
        hypotheses.append("موقعكم بيذكر موزعين/مناديب بس مفيش بوابة إلكترونية واضحة ليهم — فرصة محتملة لبوابة طلبات للموزعين تقلل المكالمات والمتابعة اليدوية.")
    if b2b.get("quote_request_signal") and not b2b.get("b2b_portal_signal"):
        hypotheses.append("طلب عرض السعر حاليًا شكله بيتم بشكل مباشر/يدوي — فرصة محتملة لنموذج طلب منظم يجمع كل التفاصيل من أول مرة.")
    if b2b.get("careers_tech_hiring_signal"):
        hypotheses.append("لاحظنا إعلان وظيفة مرتبط بتكنولوجيا المعلومات/النظم على موقعكم، يعني على الأرجح في استثمار حالي في التقنية — فرصة تكامل مع أي نظام موجود بدل بناء من الصفر.")
    if not hypotheses:
        hypotheses.append("مفيش إشارة علنية واضحة على موقعكم عن تعقيد تشغيلي محدد لحد دلوقتي — الفرصة هنا افتراضية وتحتاج مكالمة اكتشاف قصيرة لمعرفة الصورة الحقيقية قبل أي اقتراح.")

    if not a.get("audited"):
        missing_info.append("لا يوجد موقع إلكتروني معروف للنشاط — مفيش مصدر عام نقدر نبني عليه فرضيات محددة.")
    elif not a.get("reachable"):
        missing_info.append("الموقع المعروف غير متاح وقت الفحص.")
    else:
        if not b2b.get("multi_branch_signal") and not b2b.get("warehouse_or_factory_signal"):
            missing_info.append("حجم العمليات الفعلي (عدد الفروع/المخازن) غير مؤكد من المصادر العامة.")
        if b2b.get("careers_tech_hiring_signal") is None:
            missing_info.append("لم نتمكن من فحص صفحة الوظائف (غير موجودة أو تعذر الوصول إليها).")

    hypotheses = hypotheses[:3]

    wa = (f"مساء الخير، معايا {args.my_name} من {args.my_company}.\n"
          f"شفت نشاط {name} ولاحظت نقطة حابب أشاركها معاكم.\n"
          f"{hypotheses[0]}\n"
          f"حابين تتكلموا دقيقتين تعرفوا تفاصيل أكتر؟ مفيش أي التزام.")

    email_subj = f"فرصة تطوير أنظمة داخلية لـ {name}"
    signature = f"{args.my_name}\n{args.my_company}\n{args.my_phone} | {args.my_email}"
    email_body = (f"تحية طيبة،\n\n"
                  f"{hypotheses[0]}\n\n"
                  f"دي فرضية مبنية على معلومات عامة، وحابين نتأكد منها معاكم في مكالمة قصيرة قبل أي اقتراح محدد.\n\n"
                  f"تحياتي،\n{signature}")

    return {
        "lead_id": lead_id,
        "summary": f"{name}" + (f"، تقييم {b['rating']} نجمة من {b['reviews']} مراجعة." if b.get("rating") else "، بدون تقييمات كافية بعد على جوجل."),
        "top_3_problems": hypotheses + ["—"] * (3 - len(hypotheses)),
        "software_opportunity_hypotheses": hypotheses,
        "evidence_gaps": missing_info,
        "likely_buyer_role": "مدير العمليات / مدير تكنولوجيا المعلومات (حسب حجم النشاط)",
        "business_impact": "فرضيات أثر تشغيلي محتمل (تقليل عمل يدوي، تحسين رؤية المخزون/الطلبات) — غير مؤكدة بدون مكالمة اكتشاف.",
        "whatsapp_message": wa,
        "email_subject": email_subj,
        "email_body": email_body,
        "follow_up_day3": f"صباح الخير، بس حابب أتابع معاك بخصوص {name} — لو عندك دقيقتين نتكلم في الفكرة، إحنا جاهزين.",
        "follow_up_day7": "أهلًا بيك تاني، حبيت أضيف نقطة كمان ممكن تفيدكم: " + (hypotheses[1] if len(hypotheses) > 1 else "فيه فرصة تانية ممكن تناسبكم حسب حجم العمليات.") + " تحب نتكلم فيها؟",
        "follow_up_day14": f"آخر متابعة بس من ناحيتي 🙂 لو حابين تتكلموا في أي وقت عن {name}، أنا موجود.",
        "call_opener": f"مساء الخير، معايا {args.my_name} من {args.my_company}. بنساعد شركات زي حضرتكم في أتمتة العمليات وربط الأنظمة، وعندي سؤال سريع عن طريقة شغلكم الحالية لو عندك دقيقتين.",
        "discovery_questions": [
            "إزاي بتتابعوا حركة المخزون/الطلبات دلوقتي — إكسيل، نظام جاهز، ولا شغل يدوي؟",
            "لو عندكم أكتر من فرع/مخزن، إزاي بتشوفوا الصورة الكاملة في مكان واحد؟",
            "فيه حاجة بتتكرر يدويًا كل يوم أو كل أسبوع ممكن تتعمل تلقائي؟",
            "العميل أو المورد بيتواصل معاكم إزاي لطلب عرض سعر أو متابعة طلب؟",
            "لو حد جديد دخل الفريق، هياخد وقت قد إيه لحد ما يفهم السيستم الحالي؟",
        ],
        "objections": [
            {"objection": "إحنا مش شايفين مشكلة في الطريقة الحالية", "answer": "ممكن فعلًا تكون الطريقة الحالية شغالة كويس — المكالمة هدفها بس نتأكد مش نفترض، ومفيش أي التزام بعدها."},
            {"objection": "عندنا نظام بالفعل", "answer": "ممتاز، في الحالة دي ممكن نشوف فرص تكامل أو تحسين على اللي موجود بدل استبدال كامل."},
            {"objection": "السعر هيبقى كام؟", "answer": "بيعتمد كليًا على حجم العمليات والمطلوب بالظبط، وده بالظبط اللي مكالمة الاكتشاف بتوضحه قبل أي رقم."},
        ],
        "recommended_offer": money_range_or_discovery(s, args),
        "best_channel": "واتساب أو مكالمة قصيرة",
        "best_time": "أوقات العمل الرسمية، بعيدًا عن بداية ونهاية اليوم",
    }


def build_translation_pack(lead_id, b, a, s, args):
    """Legacy vertical - verbatim behavior from the original translation-
    office run, kept for backward compatibility."""
    name = b["name"]
    has_site = b.get("has_website")
    reachable = a.get("reachable")

    problems, impacts, hook = [], [], None
    if not has_site:
        problems.append("النشاط مش ظاهر بموقع إلكتروني خاص بيه على الإطلاق" +
                         (f" — بس قيد على خرائط جوجل وصفحة فيسبوك ({b['facebook']})." if b.get("facebook") else " — بس قيد على خرائط جوجل."))
        impacts.append("أي عميل بيدور عليكم في جوجل بره الخريطة مش هيلاقي حاجة يتأكد منها أو يشوف خدماتكم وأسعاركم.")
        hook = "no_website"
    elif not reachable:
        problems.append("الموقع المسجل في جوجل بتاعكم مش بيفتح حاليًا (تم اختباره وطلع نتيجة اتصال فاشلة).")
        impacts.append("نفس أثر عدم وجود موقع تقريبًا — أي حد يحاول يدخل من جوجل أو من كارت شغل هيلاقي صفحة ماتفتحش.")
        hook = "unreachable"
    else:
        rt = a.get("server_response_time_s", 0)
        if rt >= 4:
            problems.append(f"سيرفر الموقع رد بعد {rt} ثانية وقت الفحص — وقت استجابة بطيء بيخلي زوار يقفلوا الصفحة.")
            impacts.append("كل ثانية تأخير بتقلل فرصة إن الزائر يستنى ويكمل.")
            hook = hook or "slow"
        if not a.get("bilingual_ar_en"):
            problems.append("الموقع مش ثنائي اللغة بشكل واضح، وده بيقلل وصولكم لعملاء أجانب بيدوروا بالإنجليزي.")
            hook = hook or "not_bilingual"
        if not a.get("has_whatsapp"):
            problems.append("مفيش زرار واتساب في الموقع — القناة اللي أغلب العملاء بيفضلوها للتواصل السريع.")
            hook = hook or "no_whatsapp"
        if not a.get("has_form"):
            problems.append("مفيش نموذج تواصل/طلب مباشر على الموقع، يعني العميل مضطر يتصل بدل ما يبعت تفاصيله مباشرة.")
            hook = hook or "no_quote_form"
        if a.get("title_generic"):
            problems.append("عنوان الصفحة في جوجل عام جدًا من غير اسم النشاط أو كلمات بحث، وده بيقلل ظهوركم.")
        if not problems:
            problems.append("الموقع بشكل عام شغال وكويس؛ الفرصة في إضافات (رفع ملفات، تحسين سيو) مش في إصلاح عطل.")
            hook = hook or "polish"

    problems = (problems + ["—", "—"])[:3]

    templates = {
        "no_website": (f"مساء الخير، حضرتك صاحب {name}؟ أنا {args.my_name} من {args.my_company}، بنعمل مواقع متخصصة.\nلاحظت إن النشاط مش ظاهر بموقع إلكتروني لحد دلوقتي، بس بيانات تواصلكم على خرائط جوجل.\nده بيخلي ناس كتير بتدور عليكم مش بتلاقي حاجة تتأكد منها.\nحابب أبعتلك تقرير مجاني صغير يوضح الموضوع أكتر؟ مفيش أي التزام.",
                       f"موقع إلكتروني لـ {name} — ملاحظة سريعة"),
        "unreachable": (f"مساء الخير، معايا {args.my_name} من {args.my_company}.\nحاولنا ندخل موقع {name} على {b.get('website')} ولقيناه مش بيفتح حاليًا.\nأي عميل بيحاول يوصلكم من جوجل بيوصله لصفحة فاضية. حبينا نلفت نظركم — حابين تفاصيل أكتر؟",
                        f"موقع {name} مش بيفتح حاليًا"),
        "slow": (f"مساء الخير، معايا {args.my_name} من {args.my_company}.\nعملنا فحص سريع لموقع {name} ولقينا السيرفر بياخد وقت طويل نسبيًا يرد.\nده بيخلي زوار يسيبوا الصفحة قبل ما تفتح. حابب أبعتلك تقرير مجاني فيه التفاصيل؟",
                 f"سرعة موقع {name} محتاجة نظرة"),
        "not_bilingual": (f"مساء الخير، معايا {args.my_name} من {args.my_company}.\nشفت موقع {name}، شكله كويس، بس مش واضح إنه ثنائي اللغة.\nده ممكن يفوّت عليكم عملاء بيدوروا بالإنجليزي. حابب أشاركك ملاحظة بسيطة؟",
                          f"فرصة توسيع جمهور موقع {name}"),
        "no_whatsapp": (f"مساء الخير، معايا {args.my_name} من {args.my_company}.\nشفت موقع {name}، ولاحظت إنه مفيهوش زرار واتساب مباشر.\nحابب أوضحلك الفكرة في تقرير صغير مجاني؟",
                        f"إضافة واتساب لموقع {name}"),
        "no_quote_form": (f"مساء الخير، معايا {args.my_name} من {args.my_company}.\nشفت موقع {name}، ولاحظت إنه مفيهوش نموذج تواصل مباشر.\nحابب أشاركك فكرة بسيطة للتحسين؟",
                          f"نموذج تواصل مباشر لموقع {name}"),
        "polish": (f"مساء الخير، معايا {args.my_name} من {args.my_company}.\nشفت موقع {name} وشكله كويس بشكل عام.\nعندي كام فكرة بسيطة ممكن تضيف قيمة. حابب تسمعها في تقرير مجاني صغير؟",
                   f"أفكار بسيطة لتطوير موقع {name}"),
    }
    wa, subj = templates[hook]
    signature = f"{args.my_name}\n{args.my_company}\n{args.my_phone} | {args.my_email}"
    email_body = f"تحية طيبة،\n\n{wa.split(chr(10),1)[-1]}\n\nتحياتي،\n{signature}"

    return {
        "lead_id": lead_id,
        "summary": f"{name}" + (f"، تقييم {b['rating']} نجمة من {b['reviews']} مراجعة." if b.get("rating") else "، بدون تقييمات كافية بعد."),
        "top_3_problems": problems,
        "business_impact": " ".join(impacts) if impacts else "الموقع بيعمل بشكل مقبول؛ التحسينات المقترحة بتزود الحضور الرقمي مش بتعالج عطل قائم.",
        "whatsapp_message": wa,
        "email_subject": subj,
        "email_body": email_body,
        "follow_up_day3": f"صباح الخير، بس حابب أتابع معاك بخصوص {name} — لو حابب تشوف التقرير المجاني، إحنا جاهزين.",
        "follow_up_day7": "أهلًا بيك تاني، حبيت أضيف نقطة كمان لاحظتها: " + (problems[1] if problems[1] != "—" else "فيه فرصة بسيطة تانية ممكن تفيدكم.") + " تحب أشرحها؟",
        "follow_up_day14": f"آخر متابعة بس من ناحيتي 🙂 لو حابب التقرير المجاني لموقع {name} في أي وقت، أنا موجود.",
        "call_opener": f"مساء الخير، معايا {args.my_name} من {args.my_company}. عندي ملاحظة سريعة على حضور {name} حابب أشاركها معاك لو عندك دقيقتين.",
        "objections": [
            {"objection": "الموقع مش أولوية دلوقتي", "answer": "فاهم تمامًا، بس حتى تقرير مجاني بسيط ممكن يوريك فرص بسيطة ومفيش أي التزام بيه."},
            {"objection": "عندنا صفحة سوشيال ميديا وده كفاية", "answer": "السوشيال ميديا فعلًا قناة كويسة، بس الموقع بيدي ثقة أكبر لعملاء بيدوروا عليكم في جوجل مباشرة."},
            {"objection": "السعر هيبقى كام؟", "answer": "بيختلف حسب حجم النشاط والمطلوب بالظبط، بس التقرير المجاني هيوضح الصورة الأول من غير أي سعر أو التزام."},
        ],
        "recommended_offer": money_range_or_discovery(s, args),
        "best_channel": "واتساب",
        "best_time": "بعد الظهر (2-5 م)، بعيدًا عن وقت الذروة الصباحي للنشاط",
    }


def build_pack(lead_id, businesses, audits, scores, args):
    b = businesses[lead_id]
    a = audits.get(lead_id, {"audited": False})
    s = scores[lead_id]
    if args.vertical == "translation":
        return build_translation_pack(lead_id, b, a, s, args)
    return build_software_pack(lead_id, b, a, s, args)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True)
    p.add_argument("--vertical", choices=["b2b_software", "translation"], default="b2b_software")
    p.add_argument("--service", default="تطوير أنظمة وأتمتة عمليات مخصصة")
    p.add_argument("--my-name", default="مريم")
    p.add_argument("--my-company", default="Rakmyat Solutions")
    p.add_argument("--my-phone", default="01023516495")
    p.add_argument("--my-email", default="info@rakmyat.online")
    p.add_argument("--price-low", default="30,000 - 60,000")
    p.add_argument("--price-mid", default="60,000 - 120,000")
    p.add_argument("--price-high", default="120,000+")
    p.add_argument("--currency", default="جنيه")
    args = p.parse_args()
    base = args.output_dir

    with open(os.path.join(base, "raw_businesses.json"), encoding="utf-8") as f:
        businesses = {b["lead_id"]: b for b in json.load(f)}
    with open(os.path.join(base, "audits.json"), encoding="utf-8") as f:
        audits = json.load(f)
    with open(os.path.join(base, "scores.json"), encoding="utf-8") as f:
        scores = json.load(f)

    packs = {lid: build_pack(lid, businesses, audits, scores, args) for lid in businesses}
    with open(os.path.join(base, "sales_pack.json"), "w", encoding="utf-8") as f:
        json.dump(packs, f, ensure_ascii=False, indent=2)
    print(f"Built {len(packs)} sales packs (vertical={args.vertical}).")


if __name__ == "__main__":
    main()
