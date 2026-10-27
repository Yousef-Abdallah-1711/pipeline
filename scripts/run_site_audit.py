"""Crawl and report on every discoverable public HTML page of one website.

Usage: python scripts/run_site_audit.py https://example.com
Requires requests and Playwright with Chromium installed.
"""
from __future__ import annotations
import argparse, json, re, time, html, urllib.robotparser
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
import xml.etree.ElementTree as ET
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

UA = "LeadHunterSiteAudit/1.0 (+public-site-audit; no forms submitted)"
TRACKING = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def normalize(url: str) -> str | None:
    try:
        p = urlsplit(url.strip())
        if p.scheme.lower() not in ("http", "https") or not p.hostname:
            return None
        host = p.hostname.lower().rstrip(".")
        netloc = host
        if p.port and not ((p.scheme == "https" and p.port == 443) or (p.scheme == "http" and p.port == 80)):
            netloc += f":{p.port}"
        path = re.sub(r"/{2,}", "/", p.path or "/")
        if path != "/": path = path.rstrip("/")
        query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in TRACKING and not k.lower().startswith("utm_")]
        return urlunsplit((p.scheme.lower(), netloc, path, urlencode(query, doseq=True), ""))
    except (ValueError, TypeError):
        return None


def base_host(host: str) -> str:
    return host.lower().removeprefix("www.")


def is_internal(url: str, host: str) -> bool:
    try:
        h = (urlsplit(url).hostname or "").lower().removeprefix("www.")
        root = base_host(host)
        return h == root or h.endswith("." + root)
    except Exception:
        return False


def get_text(page, selector):
    try: return page.locator(selector).all_text_contents()
    except Exception: return []


def ensure_html(url):
    path = urlsplit(url).path.lower()
    return not re.search(r"\.(?:pdf|jpe?g|png|gif|webp|svg|ico|css|js|xml|json|zip|docx?|xlsx?|pptx?|mp[34]|woff2?|ttf|eot)$", path)


def build_robots_and_sitemaps(root, session):
    robots_url = urljoin(root, "/robots.txt")
    robots_text = ""
    try:
        r = session.get(robots_url, timeout=15)
        if r.status_code < 400: robots_text = r.text[:2_000_000]
    except requests.RequestException: pass
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(robots_url); rp.parse(robots_text.splitlines())
    sitemap_urls = list(dict.fromkeys(re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots_text)))
    sitemap_urls.extend([urljoin(root, "/sitemap.xml"), urljoin(root, "/sitemap_index.xml")])
    found, seen = [], set()
    q = deque(sitemap_urls)
    while q:
        sm = normalize(q.popleft())
        if not sm or sm in seen or not is_internal(sm, urlsplit(root).hostname): continue
        seen.add(sm)
        try:
            r = session.get(sm, timeout=20)
            if r.status_code >= 400 or len(r.content) > 25_000_000: continue
            raw = r.content
            if b"<" not in raw[:100]:
                for line in r.text.splitlines():
                    u = normalize(line.strip())
                    if u: found.append(u)
                continue
            doc = ET.fromstring(raw)
            for el in doc.iter():
                if el.tag.lower().endswith("loc") and el.text:
                    u = normalize(el.text.strip())
                    if not u: continue
                    if el.text.strip().lower().endswith((".xml", ".xml.gz")) or "sitemapindex" in doc.tag.lower(): q.append(u)
                    elif is_internal(u, urlsplit(root).hostname) and ensure_html(u): found.append(u)
        except Exception: continue
    return rp, robots_url, bool(robots_text), list(dict.fromkeys(found)), sorted(seen)


def inspect_page(page, requested_url, response, elapsed, evidence_dir, index):
    data = page.evaluate("""() => {
      const metas = [...document.querySelectorAll('meta')];
      const meta = n => (metas.find(x => (x.name||'').toLowerCase()===n.toLowerCase())||{}).content || '';
      const imgs=[...document.images];
      const links=[...document.querySelectorAll('a[href]')].map(a=>({href:a.href,text:(a.innerText||a.getAttribute('aria-label')||'').trim().slice(0,120)}));
      const resources=[...document.querySelectorAll('img[src],script[src],link[rel=stylesheet][href],iframe[src],video[src],source[src],audio[src]')].map(x=>x.src||x.href).filter(Boolean);
      const forms=[...document.forms].map(f=>({action:f.action,method:f.method,fields:f.querySelectorAll('input,select,textarea').length}));
      return {url:location.href,title:document.title||'',description:meta('description'),robots:meta('robots'),canonical:document.querySelector('link[rel=canonical]')?.href||'',lang:document.documentElement.lang||'',viewport:meta('viewport'),h1:[...document.querySelectorAll('h1')].map(x=>x.innerText.trim()).filter(Boolean),
       h2Count:document.querySelectorAll('h2').length,images:imgs.length,imagesMissingAlt:imgs.filter(x=>!x.hasAttribute('alt')).length,forms,links,resources,hasJsonLd:!!document.querySelector('script[type="application/ld+json"]'),
       httpResources:resources.filter(x=>location.protocol==='https:'&&x.startsWith('http:')).slice(0,100),scrollWidth:document.documentElement.scrollWidth,bodyText:document.body?.innerText||''};
    }""")
    data["requested_url"] = requested_url
    data["status"] = response.status if response else None
    data["navigation_seconds"] = round(elapsed, 3)
    data["screenshot_desktop"] = None
    data["screenshot_mobile"] = None
    data["failed_resources"] = getattr(page, "_audit_failed_resources", [])
    if response:
        stem=f"page-{index:05d}"
        try:
            path=evidence_dir/f"{stem}-desktop.png"; page.screenshot(path=str(path), full_page=False, animations="disabled"); data["screenshot_desktop"]=path.name
        except Exception: pass
        try:
            page.set_viewport_size({"width":390,"height":844})
            data["mobile_scroll_width"]=page.evaluate("document.documentElement.scrollWidth")
            data["mobile_overflow"]=data["mobile_scroll_width"]>390
            path=evidence_dir/f"{stem}-mobile.png"; page.screenshot(path=str(path), full_page=False, animations="disabled"); data["screenshot_mobile"]=path.name
        except Exception: data["mobile_overflow"]=None
        finally:
            try: page.set_viewport_size({"width":1440,"height":1000})
            except Exception: pass
    return data


def finding(fid, category, title, severity, pages, observation, impact, search, action, evidence_key):
    refs=[]
    for p in pages:
        for k in evidence_key:
            if p.get(k): refs.append({"url":p.get("url"),"screenshot":"evidence/"+p[k]})
    return {"id":fid,"category":category,"title":title,"severity":severity,"status":"verified","confidence":"high" if pages else "medium",
      "affected_urls":[p.get("url") for p in pages],"observation":observation,"evidence":refs,
      "customer_business_impact":impact,"search_impact":search,"recommendation":action}


def analyze(pages, site_https):
    fs=[]
    def add(cat,title,sev,subset,obs,imp,seo,act,keys=("screenshot_desktop",)):
        if subset: fs.append(finding(f"F-{len(fs)+1:02d}",cat,title,sev,subset,obs,imp,seo,act,keys))
    if not site_https:
        add("security","الموقع لا يستخدم اتصالًا آمنًا","high",pages[:1],"الرابط النهائي للموقع يعمل ببروتوكول HTTP.","قد يظهر للزائر تحذير أمان، وقد لا يكون نقل البيانات محميًا.","إشارة ثقة وتجربة؛ لا نربطها وحدها بترتيب محدد.","تفعيل HTTPS وإعادة توجيه النسخة غير الآمنة.")
    checks=[
      ("missing-title",lambda p:not p.get("title"),"عنوان الصفحة غير موجود","medium","عنوان الصفحة مش ظاهر للزائر أو محرك البحث.","الزائر ومحركات البحث محتاجين عنوان واضح يعرفهم بموضوع الصفحة.","غيابه يضعف وضوح الصفحة في نتائج البحث، من غير ضمان لترتيب بعينه.","إضافة عنوان فريد وواضح لكل صفحة."),
      ("missing-description",lambda p:not p.get("description"),"وصف الصفحة ناقص","low","مفيش وصف تعريفي مسجل للصفحة.","الوصف الواضح يساعد في شرح محتوى الصفحة قبل فتحها.","قد يؤثر على طريقة عرض النتيجة، ومحرك البحث ممكن يختار نصًا بديلًا.","كتابة وصف مختصر وفريد للصفحات المهمة."),
      ("missing-h1",lambda p:len(p.get("h1",[]))==0,"العنوان الرئيسي للصفحة غير واضح","medium","الصفحة مافيهاش عنوان رئيسي واضح في بياناتها.","الزائر ممكن مايفهمش موضوع الصفحة بسرعة.","وضوح العناوين يساعد على فهم المحتوى، لكنه لا يضمن ترتيبًا أعلى.","إضافة عنوان رئيسي واحد يشرح محتوى الصفحة."),
      ("multiple-h1",lambda p:len(p.get("h1",[]))>1,"في أكتر من عنوان رئيسي في الصفحة","low","الصفحة فيها أكتر من عنوان رئيسي.","ترتيب العناوين بشكل أوضح يساعد الزائر على متابعة المحتوى.","ملاحظة تنظيمية؛ ما نعتبرهاش وحدها سببًا لهبوط الترتيب.","مراجعة ترتيب العناوين واستخدام عنوان رئيسي واضح."),
      ("missing-lang",lambda p:not p.get("lang"),"لغة الصفحة مش متعرفة بوضوح","low","لغة الصفحة مش محددة في وسم الصفحة.","أدوات القراءة وبعض المتصفحات ممكن ماتعرفش تنطق المحتوى باللغة المناسبة.","معلومة بنيوية تساعد على تفسير الصفحة؛ مش وعد بترتيب أعلى.","تحديد لغة كل صفحة حسب محتواها."),
      ("missing-viewport",lambda p:not p.get("viewport"),"إعداد عرض الموبايل ناقص","high","الصفحة مافيهاش إعداد واضح لعرضها على الموبايل.","ممكن المحتوى مايظهرش بالحجم المناسب على الشاشات الصغيرة.","تجربة الموبايل مهمة للزوار؛ راجع التأثير بعد الإصلاح.","إضافة إعداد عرض مناسب واختبار الصفحات على الموبايل."),
      ("mobile-overflow",lambda p:p.get("mobile_overflow") is True,"المحتوى أعرض من شاشة الموبايل","high","عرض المحتوى على الموبايل أكبر من عرض الشاشة.","الزائر ممكن يضطر يحرك الشاشة يمين وشمال أو يفوته جزء من المحتوى.","مشكلة استخدام على الموبايل؛ ما نعدش بترتيب معين.","مراجعة العناصر العريضة وضبط تخطيط الصفحة للموبايل.",("screenshot_mobile",)),
      ("missing-alt",lambda p:p.get("imagesMissingAlt",0)>0,"بعض الصور من غير وصف نصي","medium","في صور من غير نص بديل يشرح محتواها.","الزائر اللي بيستخدم قارئ شاشة ممكن مايعرفش الصورة بتعرض إيه.","الوصف النصي يساعد أدوات القراءة ومحركات البحث على فهم الصور.","إضافة نص بديل مفيد للصور المهمة."),
      ("http-resources",lambda p:len(p.get("httpResources",[]))>0,"في موارد بتتحمل باتصال غير آمن","medium","لقينا موارد HTTP داخل صفحة HTTPS.","المتصفح ممكن يحجب موارد أو يعرض الصفحة بشكل غير مكتمل.","مشكلة سلامة وتحميل؛ نقيس الأثر بعد إصلاح الروابط.","تحديث روابط الموارد لتستخدم HTTPS."),
    ]
    for cat,pred,title,sev,obs,imp,seo,act,*rest in checks:
        subset=[p for p in pages if p.get("status") and p["status"]<400 and pred(p)]
        add(cat,title,sev,subset,obs,imp,seo,act,rest[0] if rest else ("screenshot_desktop",))
    broken=[p for p in pages if p.get("status") and p["status"]>=400]
    add("broken-pages","في صفحات داخلية بتفتح بخطأ","high",broken,"بعض الروابط الداخلية رجعت حالة HTTP خطأ عند فتحها.","الزائر ممكن يوصل لطريق مسدود بدل المعلومات اللي بيدور عليها.","الروابط المعطلة تضر تجربة التصفح وقد تعطل الوصول للمحتوى.","تصحيح الرابط أو تحويله للصفحة المناسبة.")
    resource_pages=[p for p in pages if p.get("failed_resources")]
    add("broken-resources","في صور أو ملفات داخلية مش بتتحمل","medium",resource_pages,"المتصفح سجل موارد داخلية رجعت خطأ أثناء تحميل الصفحات.","ممكن صورة أو جزء من شكل الصفحة ما يظهرش للزائر.","الموارد المعطلة ممكن تضعف تجربة الصفحة؛ نراجع كل مورد قبل استنتاج أثر بحث مباشر.","تصحيح مسار المورد أو استبداله، ثم مراجعة الصفحة بعد الإصلاح.")
    duplicate_titles={}
    for p in pages:
        t=p.get("title","").strip().lower()
        if t: duplicate_titles.setdefault(t,[]).append(p)
    dup=[p for group in duplicate_titles.values() if len(group)>1 for p in group]
    add("duplicate-title","في صفحات كتير بنفس العنوان","medium",dup,"لقينا عنوان متكرر على أكتر من صفحة.","العناوين المتشابهة بتصعب التمييز بين الصفحات.","العنوان الفريد بيوضح موضوع كل صفحة لمحركات البحث والزائر.","كتابة عنوان مختلف يعبّر عن محتوى كل صفحة.")
    return fs


def build_html(data, outdir, client=False):
    findings=data["findings"]
    if client:
        sev={"high":0,"medium":1,"low":2}
        findings=sorted(findings,key=lambda f:(sev.get(f["severity"],3),f["id"]))[:10]
    items=[]
    for f in findings:
        ev="".join(f'<a class="shot" href="{html.escape(e["screenshot"])}"><img src="{html.escape(e["screenshot"])}" alt="دليل مرئي للملاحظة {html.escape(f["id"])}"></a>' for e in f["evidence"][:2] if (outdir/e["screenshot"]).exists())
        urls="، ".join(f'<a href="{html.escape(u)}"><bdi dir="ltr">{html.escape(u)}</bdi></a>' for u in f["affected_urls"][:5])
        items.append(f'''<article class="finding"><div class="top"><span class="tag">{html.escape(f['id'])} · {html.escape(f['severity'])}</span><h2>{html.escape(f['title'])}</h2></div><p><b>اللي رصدناه:</b> {html.escape(f['observation'])}</p><p><b>أثره على العميل:</b> {html.escape(f['customer_business_impact'])}</p><p><b>علاقته بالظهور في البحث:</b> {html.escape(f['search_impact'])}</p><p><b>الخطوة المقترحة:</b> {html.escape(f['recommendation'])}</p><p class="urls">الصفحات: {urls}</p><div class="shots">{ev}</div></article>''')
    rows=[]
    for p in data["pages"]:
        body_text=html.escape(p.get("bodyText", ""))
        body_panel=f'<details><summary>النص الظاهر اللي اتقرا ({len(p.get("bodyText", ""))} حرف)</summary><pre>{body_text}</pre></details>'
        rows.append(f'<tr><td><a href="{html.escape(p["url"])}">{html.escape(p["url"])}</a>{body_panel}</td><td>{p.get("status") or "تعذر الوصول"}</td><td>{html.escape(p.get("title") or "بدون عنوان")}</td><td>{len(p.get("h1",[]))}</td><td>{p.get("navigation_seconds","-")}</td></tr>')
    findings_title_class="findings-title" if findings else ""
    title="ملخص مشاكل الموقع" if client else "تقرير فحص الموقع وفرص التحسين"
    subtitle="ملخص مبسط للعميل" if client else "تقرير كامل، صفحات تمت مراجعتها، وأدلة قابلة للتتبع"
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} | {html.escape(data['site']['host'])}</title><style>
@page{{size:A4;margin:14mm}}*{{box-sizing:border-box}}body{{margin:0;font-family:Arial,Tahoma,sans-serif;color:#18332d;background:#f6f9f7;line-height:1.65}}.wrap{{max-width:1150px;margin:auto;padding:28px}}header{{background:#126b55;color:white;border-radius:16px;padding:32px;margin-bottom:22px}}header h1{{margin:0 0 5px;font-size:30px}}header p{{margin:0;color:#e6f4ee}}.stats{{display:flex;flex-wrap:wrap;gap:10px;margin-top:20px}}.stats span,.tag{{background:#eaf3ef;color:#126b55;padding:6px 11px;border-radius:20px;font-size:13px}}h2{{margin:0 0 8px}}.finding,.panel{{background:white;border:1px solid #dce6e2;border-radius:12px;padding:20px;margin:14px 0;break-inside:avoid}}.top{{display:flex;align-items:center;gap:12px}}.top h2{{font-size:20px}}.finding p{{margin:8px 0}}.shots{{display:flex;gap:12px;flex-wrap:wrap}}.shot{{display:block;max-width:48%;border:1px solid #dce6e2;border-radius:8px;overflow:hidden}}.shot img{{display:block;width:100%;max-height:330px;object-fit:contain}}a{{color:#126b55;overflow-wrap:anywhere}}table{{width:100%;border-collapse:collapse;font-size:13px;direction:rtl}}th,td{{border-bottom:1px solid #dce6e2;padding:9px;text-align:right;vertical-align:top}}details pre{{white-space:pre-wrap;max-height:45vh;overflow:auto;font:inherit;color:#52645f}}summary{{cursor:pointer;color:#126b55}}.note{{color:#64736f;font-size:13px}}@media print{{body{{background:white}}.wrap{{padding:0}}.findings-title{{break-before:page}}.finding,.panel{{box-shadow:none}}a{{color:#18332d;text-decoration:none}}}}
</style></head><body><div class="wrap"><header><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)} · {html.escape(data['site']['host'])}</p><div class="stats"><span>صفحات اكتُشفت: <bdi dir="ltr">{data['coverage']['discovered']}</bdi></span><span>صفحات اتفحصت: <bdi dir="ltr">{data['coverage']['reviewed']}</bdi></span><span>تعذر الوصول: <bdi dir="ltr">{data['coverage']['failed']}</bdi></span><span>ملاحظات موثقة: <bdi dir="ltr">{len(findings)}</bdi></span></div></header><section class="panel"><h2>النطاق والطريقة</h2><p>الرابط: <a href="{html.escape(data['site']['canonical_url'])}"><bdi dir="ltr">{html.escape(data['site']['canonical_url'])}</bdi></a></p><p>بدأ الفحص: <bdi dir="ltr">{html.escape(data['run']['started_at'])}</bdi> · المنطقة الزمنية: UTC</p><p>اكتشف الزاحف الصفحات العامة من الروابط الداخلية وملفات Sitemap. ده مش بيشمل الصفحات غير المرتبطة أو المحمية بتسجيل دخول.</p><p class="note">قياس زمن التحميل هنا قياس تنقل للصفحة، مش نتيجة Lighthouse أو PageSpeed. ما اتبعتش نماذج أو طلبات شراء.</p></section><h2 class="{findings_title_class}">الملاحظات</h2>{''.join(items) if items else '<p>ما ظهرتش ملاحظات آلية قابلة للإثبات في النطاق اللي اتفحص.</p>'}<section class="panel"><h2>قائمة الصفحات المكتشفة والمراجعة</h2><p class="note">العدد النهائي يتأثر بوجود Sitemap، والروابط العامة، وقواعد robots.txt. أي صفحات لا تظهر في هذه المصادر لا يمكن اعتبارها مغطاة.</p><div style="overflow:auto"><table><thead><tr><th>الرابط</th><th>الحالة</th><th>عنوان الصفحة</th><th>عدد العناوين الرئيسية</th><th>زمن التنقل (ثانية)</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section><section class="panel"><h2>المراجع والمنهج</h2><p>المراجع الأولية لكل ملاحظة هي روابط الصفحات المتأثرة ولقطات الشاشة المرفقة معها. سجلات الصفحات الكاملة موجودة في <code>audit-data.json</code>.</p><p class="note">النتائج الآلية تحتاج مراجعة بشرية للسياق قبل اعتبارها توصية نهائية. الأداء الميداني، المبيعات، والتحويلات تحتاج بيانات من مالك الموقع.</p></section></div></body></html>'''


def write_package(data, outdir):
    (outdir/"audit-data.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    full=build_html(data,outdir,False)
    (outdir/"index.html").write_text(full,encoding="utf-8")
    pdf_html=build_html(data,outdir,True)
    pdf_html=pdf_html.replace("@page{size:A4;margin:14mm}","@page{size:A4;margin:12mm}")
    pdf_path=outdir/"client-brief.pdf"
    print_source=outdir/".client-brief-print.html"
    print_source.write_text(pdf_html,encoding="utf-8")
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={"width":1200,"height":900})
        page.goto(print_source.resolve().as_uri(),wait_until="load")
        page.locator("table").evaluate("el => el.closest('section').remove()")
        page.emulate_media(media="print")
        page.pdf(path=str(pdf_path),format="A4",print_background=True,prefer_css_page_size=True)
        browser.close()
    print_source.unlink(missing_ok=True)
    summary=f"# ملخص فحص الموقع\n\n- الموقع: {data['site']['canonical_url']}\n- وقت الفحص: {data['run']['started_at']} UTC\n- الصفحات المكتشفة: {data['coverage']['discovered']}\n- الصفحات التي تمت مراجعتها: {data['coverage']['reviewed']}\n- الصفحات التي تعذر الوصول إليها: {data['coverage']['failed']}\n- الملاحظات الموثقة: {len(data['findings'])}\n\nالنتائج مبنية على الصفحات العامة التي أمكن اكتشافها من الروابط وملفات Sitemap. لم يتم اختبار تسجيل الدخول أو إرسال النماذج.\n"
    (outdir/"audit-summary.md").write_text(summary,encoding="utf-8")
    roadmap="# خارطة التنفيذ المقترحة\n\nمرتبة حسب الأولوية الظاهرة في الفحص. تقديرات الأثر مش نتائج مبيعات مضمونة.\n\n"
    for f in sorted(data["findings"],key=lambda x:{"high":0,"medium":1,"low":2}.get(x["severity"],3)):
        roadmap+=f"## {f['id']} — {f['title']}\n\n- الأولوية: {f['severity']}\n- الصفحات: {', '.join(f['affected_urls'][:5])}\n- الخطوة: {f['recommendation']}\n\n"
    (outdir/"implementation-roadmap.md").write_text(roadmap,encoding="utf-8")
    source_lines=["# المصادر وطريقة الفحص", "",f"- رابط البداية: {data['site']['canonical_url']}",f"- تاريخ ووقت الفحص: {data['run']['started_at']} UTC",f"- عدد الصفحات المكتشفة: {data['coverage']['discovered']}",f"- عدد الصفحات التي اتفحصت: {data['coverage']['reviewed']}",f"- صفحات تعذر الوصول إليها: {data['coverage']['failed']}","- الاكتشاف: روابط الموقع العامة + ملفات Sitemap المتاحة + الصفحات المرتبطة داخليًا.","- لقطة شاشة سطح المكتب: 1440 × 1000. لقطة الموبايل: 390 × 844.","- لم يتم تسجيل الدخول أو إرسال نماذج أو تغيير أي محتوى بالموقع.","", "## ملفات Sitemap"]+[f"- {u}" for u in data['sitemaps']]+["", "## صفحات تمت مراجعتها"]+[f"- {p['url']} (HTTP {p['status']})" for p in data['pages']]+["", "## مراجع رسمية إضافية"]+[f"- {r['title']}: {r['url']}" for r in data.get('official_references',[])]
    (outdir/"sources-and-method.md").write_text("\n".join(source_lines)+"\n",encoding="utf-8")
    (outdir/"README.md").write_text(f"# Site audit package — {data['site']['host']}\n\n- [Complete HTML report](index.html)\n- [Client PDF](client-brief.pdf)\n- [Summary](audit-summary.md)\n- [Implementation roadmap](implementation-roadmap.md)\n- [Structured evidence and measurements](audit-data.json)\n- [Sources and method](sources-and-method.md)\n- Screenshots: `evidence/`\n",encoding="utf-8")


def main():
    ap=argparse.ArgumentParser(description="Crawl discoverable public pages and create a website audit package.")
    ap.add_argument("url",nargs="?",help="Website URL, for example https://example.com")
    ap.add_argument("--from-data",help="Rebuild reports from an edited audit-data.json without crawling again")
    ap.add_argument("--output-dir",help="Output directory; default website-audits/<domain-slug>/<UTC-run-time>")
    ap.add_argument("--max-pages",type=int,default=0,help="Optional crawl cap; 0 means no artificial page cap")
    args=ap.parse_args()
    if args.from_data:
        data_path=Path(args.from_data).resolve()
        if not data_path.is_file(): ap.error(f"Audit data file not found: {data_path}")
        data=json.loads(data_path.read_text(encoding="utf-8"))
        write_package(data,data_path.parent)
        print(f"Reports rebuilt from reviewed data: {data_path.parent}")
        return
    if not args.url: ap.error("Provide a website URL or --from-data")
    start=normalize(args.url if "://" in args.url else "https://"+args.url)
    if not start: ap.error("Provide a valid http(s) website URL")
    host=urlsplit(start).hostname
    slug=re.sub(r"[^a-z0-9.-]+","-",base_host(host)).strip("-") or "website"
    started=datetime.now(timezone.utc).isoformat(timespec="seconds")
    outdir=Path(args.output_dir) if args.output_dir else Path.cwd()/"website-audits"/slug/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outdir=outdir.resolve()
    if args.output_dir and outdir.exists(): ap.error(f"Output directory already exists: {outdir}")
    if not args.output_dir:
        suffix=1; base=outdir
        while outdir.exists():
            outdir=base.with_name(base.name+f"-{suffix:02d}"); suffix+=1
    evidence_dir=outdir/"evidence"; evidence_dir.mkdir(parents=True,exist_ok=False)
    session=requests.Session(); session.headers.update({"User-Agent":UA})
    robots,robots_url,robots_found,sitemap_pages,sitemaps=build_robots_and_sitemaps(start,session)
    queue=deque([start]+sitemap_pages); queued=set(); pages=[]; skipped=[]
    print(f"[1/4] discovered {len(sitemap_pages)} sitemap URLs; crawling internal links")
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        context=browser.new_context(viewport={"width":1440,"height":1000},device_scale_factor=1,locale="ar-EG")
        page=context.new_page()
        while queue:
            url=normalize(queue.popleft())
            if not url or url in queued or not is_internal(url,host) or not ensure_html(url): continue
            queued.add(url)
            if args.max_pages and len(pages)>=args.max_pages:
                skipped.append({"url":url,"reason":"max_pages limit"}); continue
            if not robots.can_fetch(UA,url):
                skipped.append({"url":url,"reason":"disallowed by robots.txt"}); continue
            t0=time.monotonic(); response=None
            page._audit_failed_resources=[]
            def capture_failure(res):
                try:
                    req=res.request
                    if res.status>=400 and is_internal(res.url,host) and req.resource_type not in ("document","xhr","fetch"):
                        page._audit_failed_resources.append({"url":res.url,"status":res.status,"type":req.resource_type})
                except Exception: pass
            page.on("response",capture_failure)
            try:
                response=page.goto(url,wait_until="domcontentloaded",timeout=30000)
                try: page.wait_for_load_state("networkidle",timeout=2500)
                except PlaywrightTimeout: pass
                if not is_internal(page.url,host):
                    skipped.append({"url":url,"reason":f"redirected outside the audited site to {page.url}"})
                    continue
                content_type=(response.headers.get("content-type","") if response else "").lower()
                if content_type and "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                    skipped.append({"url":url,"reason":f"non-HTML content type: {content_type}"})
                    continue
                elapsed=time.monotonic()-t0
                item=inspect_page(page,url,response,elapsed,evidence_dir,len(pages)+1)
                pages.append(item)
                for link in item.get("links",[]):
                    candidate=normalize(link.get("href",""))
                    if candidate and is_internal(candidate,host) and ensure_html(candidate) and candidate not in queued:
                        queue.append(candidate)
            except Exception as e:
                pages.append({"url":url,"requested_url":url,"status":getattr(response,"status",None),"error":str(e)[:500],"navigation_seconds":round(time.monotonic()-t0,3)})
            finally:
                page.remove_listener("response",capture_failure)
            if len(pages)%25==0: print(f"  crawled {len(pages)} unique public URLs; queue {len(queue)}")
        browser.close()
    print(f"[2/4] reviewed {len(pages)} unique URLs; {len(skipped)} skipped or capped")
    pages.sort(key=lambda x:x.get("url",""))
    root_page=next((p for p in pages if p.get("requested_url")==start),None)
    findings=analyze(pages,bool(root_page and root_page.get("url","").startswith("https://")))
    run={"started_at":started,"completed_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),"timezone":"UTC","command":"run_site_audit.py","max_pages":args.max_pages,"user_agent":UA,"robots_url":robots_url,"robots_file_found":robots_found}
    successful=sum(1 for p in pages if p.get("status") and p["status"]<400)
    data={"schema_version":"1.0","run":run,"site":{"input_url":args.url,"canonical_url":start,"host":host},"coverage":{"discovered":len(queued),"reviewed":len(pages),"successful":successful,"failed":len(pages)-successful,"skipped":len(skipped),"all_discoverable_public_pages":not args.max_pages and not skipped},"sitemaps":sitemaps,"pages":pages,"skipped_pages":skipped,"findings":findings,"official_references":[],"notes":["Crawl covers unique same-site public HTML URLs found in sitemaps and rendered internal links.","Orphan pages absent from links and sitemaps, login-protected routes, and infinite application states cannot be inferred as pages by a public crawl.","Navigation timings are browser measurements, not Lighthouse, PageSpeed, or field-user data."]}
    print(f"[3/4] wrote {len(findings)} evidence-backed automated findings; building HTML/PDF package")
    write_package(data,outdir)
    print(f"[4/4] complete: {outdir}")
    print(f"Pages reviewed: {len(pages)}; failed: {data['coverage']['failed']}; findings: {len(findings)}; client PDF: {outdir/'client-brief.pdf'}")

if __name__=="__main__": main()
