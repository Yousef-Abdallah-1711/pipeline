# -*- coding: utf-8 -*-
"""
Lead Hunter - Phase 5: build a sales pack per lead (summary, top-3 problems,
business impact, WhatsApp opener, email, 3 follow-ups, call opener + 3
objections, recommended package/price, best channel/time).

Defaults to Egyptian Arabic (the project's original use case: Rakmyat
Solutions selling bilingual translation-office websites). For a new
niche/language, edit the template strings below directly and tell the user
what you changed - e.g. swap "quote form" wording for "consultation booking"
for a law-firm niche, or translate templates to a different dialect/language.

Usage: python build_sales_packs.py --output-dir <dir> \\
    --service "..." --my-name "..." --my-company "..." \\
    --price-low "8,000 - 15,000" --price-mid "12,000 - 20,000" --price-high "18,000 - 30,000" --currency "جنيه"
"""
import json, os, argparse


def money_range(score_entry, args):
    pts = score_entry["business_strength_detail"]["reviews_pts"]
    if pts >= 15:
        return f"{args.price_high} {args.currency} (باقة متقدمة، نظرًا لحجم العميل وعدد التقييمات)"
    elif pts >= 8:
        return f"{args.price_mid} {args.currency} (باقة أساسية إلى متقدمة)"
    return f"{args.price_low} {args.currency} (باقة أساسية)"


def build_pack(lead_id, businesses, audits, scores, args):
    b = businesses[lead_id]
    a = audits.get(lead_id, {"audited": False})
    s = scores[lead_id]
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
        "no_website": {
            "wa": f"مساء الخير، حضرتك صاحب {name}؟ أنا {args.my_name} من {args.my_company}، بنعمل مواقع متخصصة.\nلاحظت إن النشاط مش ظاهر بموقع إلكتروني لحد دلوقتي، بس بيانات تواصلكم على خرائط جوجل.\nده بيخلي ناس كتير بتدور عليكم مش بتلاقي حاجة تتأكد منها.\nحابب أبعتلك تقرير مجاني صغير يوضح الموضوع أكتر؟ مفيش أي التزام.",
            "subj": f"موقع إلكتروني لـ {name} — ملاحظة سريعة",
        },
        "unreachable": {
            "wa": f"مساء الخير، معايا {args.my_name} من {args.my_company}.\nحاولنا ندخل موقع {name} على {b.get('website')} ولقيناه مش بيفتح حاليًا.\nأي عميل بيحاول يوصلكم من جوجل بيوصله لصفحة فاضية. حبينا نلفت نظركم — حابين تفاصيل أكتر؟",
            "subj": f"موقع {name} مش بيفتح حاليًا",
        },
        "slow": {
            "wa": f"مساء الخير، معايا {args.my_name} من {args.my_company}.\nعملنا فحص سريع لموقع {name} ولقينا السيرفر بياخد وقت طويل نسبيًا يرد.\nده بيخلي زوار يسيبوا الصفحة قبل ما تفتح. حابب أبعتلك تقرير مجاني فيه التفاصيل؟",
            "subj": f"سرعة موقع {name} محتاجة نظرة",
        },
        "not_bilingual": {
            "wa": f"مساء الخير، معايا {args.my_name} من {args.my_company}.\nشفت موقع {name}، شكله كويس، بس مش واضح إنه ثنائي اللغة.\nده ممكن يفوّت عليكم عملاء بيدوروا بالإنجليزي. حابب أشاركك ملاحظة بسيطة؟",
            "subj": f"فرصة توسيع جمهور موقع {name}",
        },
        "no_whatsapp": {
            "wa": f"مساء الخير، معايا {args.my_name} من {args.my_company}.\nشفت موقع {name}، ولاحظت إنه مفيهوش زرار واتساب مباشر.\nحابب أوضحلك الفكرة في تقرير صغير مجاني؟",
            "subj": f"إضافة واتساب لموقع {name}",
        },
        "no_quote_form": {
            "wa": f"مساء الخير، معايا {args.my_name} من {args.my_company}.\nشفت موقع {name}، ولاحظت إنه مفيهوش نموذج تواصل مباشر.\nحابب أشاركك فكرة بسيطة للتحسين؟",
            "subj": f"نموذج تواصل مباشر لموقع {name}",
        },
        "polish": {
            "wa": f"مساء الخير، معايا {args.my_name} من {args.my_company}.\nشفت موقع {name} وشكله كويس بشكل عام.\nعندي كام فكرة بسيطة ممكن تضيف قيمة. حابب تسمعها في تقرير مجاني صغير؟",
            "subj": f"أفكار بسيطة لتطوير موقع {name}",
        },
    }
    t = templates[hook]
    signature = f"{args.my_name}\n{args.my_company}\n{args.my_phone} | {args.my_email}"
    email_body = f"تحية طيبة،\n\n{t['wa'].split(chr(10),1)[-1]}\n\nتحياتي،\n{signature}"

    return {
        "lead_id": lead_id,
        "summary": f"{name}" + (f"، تقييم {b['rating']} نجمة من {b['reviews']} مراجعة." if b.get("rating") else "، بدون تقييمات كافية بعد."),
        "top_3_problems": problems,
        "business_impact": " ".join(impacts) if impacts else "الموقع بيعمل بشكل مقبول؛ التحسينات المقترحة بتزود الحضور الرقمي مش بتعالج عطل قائم.",
        "whatsapp_message": t["wa"],
        "email_subject": t["subj"],
        "email_body": email_body,
        "follow_up_day3": f"صباح الخير، بس حابب أتابع معاك بخصوص {name} — لو حابب تشوف التقرير المجاني، إحنا جاهزين.",
        "follow_up_day7": f"أهلًا بيك تاني، حبيت أضيف نقطة كمان لاحظتها: " + (problems[1] if problems[1] != "—" else "فيه فرصة بسيطة تانية ممكن تفيدكم.") + " تحب أشرحها؟",
        "follow_up_day14": f"آخر متابعة بس من ناحيتي 🙂 لو حابب التقرير المجاني لموقع {name} في أي وقت، أنا موجود.",
        "call_opener": f"مساء الخير، معايا {args.my_name} من {args.my_company}. عندي ملاحظة سريعة على حضور {name} حابب أشاركها معاك لو عندك دقيقتين.",
        "objections": [
            {"objection": "الموقع مش أولوية دلوقتي", "answer": "فاهم تمامًا، بس حتى تقرير مجاني بسيط ممكن يوريك فرص بسيطة ومفيش أي التزام بيه."},
            {"objection": "عندنا صفحة سوشيال ميديا وده كفاية", "answer": "السوشيال ميديا فعلًا قناة كويسة، بس الموقع بيدي ثقة أكبر لعملاء بيدوروا عليكم في جوجل مباشرة."},
            {"objection": "السعر هيبقى كام؟", "answer": "بيختلف حسب حجم النشاط والمطلوب بالظبط، بس التقرير المجاني هيوضح الصورة الأول من غير أي سعر أو التزام."},
        ],
        "recommended_offer": money_range(s, args),
        "best_channel": "واتساب",
        "best_time": "بعد الظهر (2-5 م)، بعيدًا عن وقت الذروة الصباحي للنشاط",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True)
    p.add_argument("--service", default="موقع إلكتروني متخصص")
    p.add_argument("--my-name", default="مريم")
    p.add_argument("--my-company", default="Rakmyat Solutions")
    p.add_argument("--my-phone", default="01023516495")
    p.add_argument("--my-email", default="info@rakmyat.online")
    p.add_argument("--price-low", default="8,000 - 15,000")
    p.add_argument("--price-mid", default="12,000 - 20,000")
    p.add_argument("--price-high", default="18,000 - 30,000")
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
    print(f"Built {len(packs)} sales packs.")


if __name__ == "__main__":
    main()
