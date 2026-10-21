# -*- coding: utf-8 -*-
"""
Lead Hunter - Phase 3: audit every business's real website with measured
(never invented) HTTP/HTML signals. No Lighthouse/PSI scores are fabricated;
server_response_time_s is a real measurement but is NOT a substitute for a
mobile Lighthouse/PSI score - always label it as such in any report text.

Usage: python audit.py --output-dir <dir>

Niche adaptation: the "has_form" / "has_file_upload_field" checks are generic
(works for quote-request forms, consultation-booking forms, contact forms).
For a niche where the key conversion action isn't a form (e.g. "book a table"
widget, a booking-calendar iframe), add a targeted regex/selector check here
and note what you added when reporting back to the user.
"""
import json, re, time, urllib.request, urllib.error, ssl, os, argparse
from urllib.parse import urljoin
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 LeadHunterAudit/1.0")
ctx = ssl.create_default_context()


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        body = resp.read()
        return {"ok": True, "status": resp.status, "final_url": resp.geturl(),
                "headers": dict(resp.getheaders()), "body": body, "scheme": "https",
                "elapsed_s": round(time.time() - t0, 2)}
    except Exception as e_https:
        try:
            url2 = url.replace("https://", "http://", 1) if url.startswith("https://") else url
            req2 = urllib.request.Request(url2, headers={"User-Agent": UA})
            resp2 = urllib.request.urlopen(req2, timeout=timeout)
            body = resp2.read()
            return {"ok": True, "status": resp2.status, "final_url": resp2.geturl(),
                    "headers": dict(resp2.getheaders()), "body": body, "scheme": "http",
                    "https_error": str(e_https), "elapsed_s": round(time.time() - t0, 2)}
        except Exception as e_http:
            return {"ok": False, "error_https": str(e_https), "error_http": str(e_http),
                    "elapsed_s": round(time.time() - t0, 2)}


def detect_platform(html_text):
    h = html_text.lower()
    if "wp-content" in h or "wp-includes" in h or "wordpress" in h:
        return "WordPress"
    if "wixstatic.com" in h or "wix.com" in h:
        return "Wix"
    if "cdn.shopify.com" in h:
        return "Shopify"
    if "squarespace" in h:
        return "Squarespace"
    if "webflow" in h:
        return "Webflow"
    return "Custom/Unknown"


def find_copyright_year(text):
    years = re.findall(r"(?:©|&copy;|Copyright)\s*(\d{4})", text, re.I)
    if not years:
        years = re.findall(r"(\d{4})\s*©", text)
    return years[0] if years else None


def audit_one(site):
    entry = {"audited": True, "url_tested": site}
    r = fetch(site)
    if not r["ok"]:
        entry.update({"reachable": False, "error": r})
        return entry

    entry["reachable"] = True
    entry["http_status"] = r["status"]
    entry["final_url"] = r["final_url"]
    entry["scheme"] = r["scheme"]
    entry["https_valid"] = r["scheme"] == "https"
    entry["https_error"] = r.get("https_error")
    entry["server_response_time_s"] = r["elapsed_s"]
    headers = r["headers"]
    try:
        html_text = r["body"].decode("utf-8")
    except Exception:
        html_text = r["body"].decode("utf-8", "ignore")
    try:
        soup = BeautifulSoup(html_text, "lxml")
    except Exception:
        soup = BeautifulSoup(html_text, "html.parser")

    mixed_content = False
    if entry["https_valid"]:
        for tag, attr in [("img", "src"), ("script", "src"), ("link", "href")]:
            for el in soup.find_all(tag):
                if (el.get(attr) or "").startswith("http://"):
                    mixed_content = True
                    break
            if mixed_content:
                break
    entry["mixed_content"] = mixed_content

    entry["mobile_viewport_tag"] = bool(soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)}))
    html_tag = soup.find("html")
    entry["declared_lang"] = (html_tag.get("lang") if html_tag else None) or ""
    sample = soup.get_text(" ", strip=True)[:5000]
    has_ar = bool(re.search(r"[؀-ۿ]", sample))
    has_en = bool(re.search(r"\b[A-Za-z]{4,}\b", sample))
    entry["has_arabic_content"] = has_ar
    entry["has_english_content"] = has_en
    entry["bilingual_ar_en"] = has_ar and has_en

    forms = soup.find_all("form")
    entry["has_form"] = len(forms) > 0
    entry["form_count"] = len(forms)
    entry["has_file_upload_field"] = bool(soup.find_all("input", attrs={"type": re.compile("^file$", re.I)}))

    low = html_text.lower()
    entry["has_whatsapp"] = bool(re.search(r"(wa\.me/|api\.whatsapp\.com)", low))
    entry["has_tel_link"] = bool(soup.find("a", href=re.compile(r"^tel:", re.I)))
    tel_pos = low.find("tel:")
    entry["phone_link_early_in_html"] = (0 <= tel_pos < len(low) * 0.4) if tel_pos >= 0 else False

    title = soup.title.string.strip() if soup.title and soup.title.string else None
    entry["title"] = title
    entry["title_generic"] = (not title) or title.strip().lower() in ("home", "untitled", "homepage", "الرئيسية")
    desc_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    entry["meta_description"] = desc_tag.get("content").strip() if desc_tag and desc_tag.get("content") else None
    entry["meta_description_present"] = bool(entry["meta_description"])
    entry["h1_count"] = len(soup.find_all("h1"))
    entry["structured_data_present"] = len(soup.find_all("script", type="application/ld+json")) > 0

    try:
        sm = fetch(urljoin(entry["final_url"], "/sitemap.xml"), timeout=8)
        entry["sitemap_present"] = sm.get("ok") and sm.get("status") == 200
    except Exception:
        entry["sitemap_present"] = False

    entry["copyright_year"] = find_copyright_year(html_text)
    entry["platform"] = detect_platform(html_text)
    entry["security_headers"] = {"hsts": bool(headers.get("Strict-Transport-Security")),
                                  "csp": bool(headers.get("Content-Security-Policy"))}

    emails = [e for e in set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html_text))
              if not e.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"))]
    entry["public_email"] = emails[0] if emails else None
    wa_numbers = re.findall(r"wa\.me/(\d+)", html_text)
    entry["whatsapp_number"] = wa_numbers[0] if wa_numbers else None
    entry["social_links"] = sorted(set(re.findall(
        r"https?://(?:www\.)?(?:facebook|instagram|linkedin|twitter|x)\.com/[^\s\"'<>]+", html_text)))[:5]
    return entry


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True)
    p.add_argument("--sleep", type=float, default=0.8)
    args = p.parse_args()
    base = args.output_dir

    with open(os.path.join(base, "raw_businesses.json"), encoding="utf-8") as f:
        businesses = json.load(f)

    results, done = {}, 0
    for b in businesses:
        lid, site = b["lead_id"], b.get("website")
        if not site:
            results[lid] = {"audited": False, "reason": "no_website"}
            continue
        entry = audit_one(site)
        results[lid] = entry
        done += 1
        status = "UNREACHABLE" if not entry.get("reachable") else f"OK ({entry.get('server_response_time_s')}s, {entry.get('platform')})"
        print(f"[{done}] {lid} {status}: {b['name'][:40]}")
        time.sleep(args.sleep)

    with open(os.path.join(base, "audits.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nDone. Audited {sum(1 for v in results.values() if v.get('audited'))} businesses with websites.")


if __name__ == "__main__":
    main()
