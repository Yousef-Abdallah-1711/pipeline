# -*- coding: utf-8 -*-
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from discover import extract_cid, extract_latlng, parse_fulltext

SAMPLE_URL = ("https://www.google.com/maps/place/Example/data=!4m7!3m6!1s0x14f5c54ca219b0c9:0x8bece6b645380ef8"
              "!8m2!3d31.2191464!4d29.931364!16s%2Fg%2F11zbp0f5bb!19sChIJybAZokzF9RQR-A44Rbbm7Is")

SAMPLE_FULLTEXT_AR = ("مكتب ترجمة معتمد اسكندرية فاست ترانس\n"
                      "مكتب ترجمة معتمد اسكندرية فاست ترانس\n"
                      "4.9(106)\n"
                      "خدمة ترجمة · بجوار جزارة الكيال, 203 شارع بورسعيد\n"
                      "مغلق · يفتح يوم الأربعاء عند الساعة ١٠ ص · 012 08333943\n\n"
                      "الموقع الإلكتروني\n\nالاتجاهات")


class TestExtraction(unittest.TestCase):
    def test_extract_cid(self):
        self.assertEqual(extract_cid(SAMPLE_URL), "ChIJybAZokzF9RQR-A44Rbbm7Is")

    def test_extract_cid_missing(self):
        self.assertIsNone(extract_cid("https://example.com/no-cid-here"))
        self.assertIsNone(extract_cid(None))

    def test_extract_latlng(self):
        lat, lng = extract_latlng(SAMPLE_URL)
        self.assertAlmostEqual(lat, 31.2191464)
        self.assertAlmostEqual(lng, 29.931364)

    def test_extract_latlng_missing(self):
        lat, lng = extract_latlng("https://example.com/no-coords")
        self.assertIsNone(lat)
        self.assertIsNone(lng)

    def test_parse_fulltext_rating_and_reviews(self):
        parsed = parse_fulltext(SAMPLE_FULLTEXT_AR)
        self.assertEqual(parsed["rating"], "4.9")
        self.assertEqual(parsed["reviews"], "106")

    def test_parse_fulltext_phone_mobile_format(self):
        parsed = parse_fulltext(SAMPLE_FULLTEXT_AR)
        self.assertEqual(parsed["phone"], "01208333943")

    def test_parse_fulltext_phone_landline_short_prefix(self):
        # Alexandria landline: "03 " (2-digit prefix) + 7 digits - the
        # original regex only matched 3-digit (01X) prefixes and silently
        # dropped these; this is the regression this test guards against.
        text = "موقع تجريبي\nموقع تجريبي\n5.0(10)\nخدمة ترجمة\nمغلق · يفتح يوم الأربعاء عند الساعة ١٠ ص · 03 5416957"
        parsed = parse_fulltext(text)
        self.assertEqual(parsed["phone"], "035416957")

    def test_parse_fulltext_no_reviews(self):
        text = "اسم تجريبي\nاسم تجريبي\nليست هناك مراجعات\nخدمة ترجمة\n012 00000000"
        parsed = parse_fulltext(text)
        self.assertEqual(parsed["reviews"], "0")
        self.assertIsNone(parsed["rating"])


if __name__ == "__main__":
    unittest.main()
