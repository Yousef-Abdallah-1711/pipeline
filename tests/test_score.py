# -*- coding: utf-8 -*-
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from score import tier_for, score_software_fit, score_website_opportunity, score_business, parse_review_count


class TestTierBoundaries(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(tier_for(100), "A")
        self.assertEqual(tier_for(80), "A")
        self.assertEqual(tier_for(79), "B")
        self.assertEqual(tier_for(65), "B")
        self.assertEqual(tier_for(64), "C")
        self.assertEqual(tier_for(45), "C")
        self.assertEqual(tier_for(44), "D")
        self.assertEqual(tier_for(0), "D")


class TestReviewParsing(unittest.TestCase):
    def test_plain_number(self):
        self.assertEqual(parse_review_count("256"), 256)

    def test_k_suffix(self):
        self.assertEqual(parse_review_count("1.2K"), 1200)

    def test_missing(self):
        self.assertEqual(parse_review_count(None), 0)
        self.assertEqual(parse_review_count(""), 0)


class TestDualScoreIndependence(unittest.TestCase):
    """The whole point of v2 scoring: a bad website must not inflate the
    software-fit score, and a good website must not deflate the
    website-opportunity score to zero just because the business looks
    operationally complex."""

    def test_no_website_maxes_out_website_score_but_not_software_score(self):
        biz = {"name": "X", "category": "خدمة ترجمة", "rating": "4.0", "reviews": "5",
               "phone": "0100", "website": None, "has_website": False, "place_url": "x"}
        sw, _ = score_software_fit(biz, None, biz)
        web, _ = score_website_opportunity(biz, None)
        self.assertGreaterEqual(web, 50, "no website should score high on website-opportunity")
        self.assertLessEqual(sw, 50, "no website alone should NOT push software-fit score high without complexity signals")

    def test_complex_operations_site_scores_high_on_software_fit_even_if_website_is_fine(self):
        biz = {"name": "Factory Co", "category": "مصنع", "rating": "4.5", "reviews": "200",
               "phone": "0100", "website": "https://example.com", "has_website": True, "place_url": "x"}
        audit = {
            "audited": True, "reachable": True, "server_response_time_s": 0.5,
            "mobile_viewport_tag": True, "has_form": True, "meta_description_present": True,
            "title_generic": False, "h1_count": 1, "has_whatsapp": True, "has_tel_link": True,
            "b2b_signals": {"multi_branch_signal": True, "warehouse_or_factory_signal": True,
                             "b2b_portal_signal": False, "dealer_or_distributor_signal": True,
                             "quote_request_signal": True, "careers_tech_hiring_signal": True},
        }
        sw, _ = score_software_fit(biz, audit, biz)
        web, _ = score_website_opportunity(biz, audit)
        self.assertGreater(sw, 60, "strong operational-complexity signals should score well on software-fit")
        self.assertLess(web, 40, "a technically sound website should score LOW on website-opportunity regardless of software-fit")

    def test_scores_always_bounded(self):
        biz = {"name": "X", "category": "", "rating": "5.0", "reviews": "9999999", "phone": "0100",
               "website": "https://example.com", "has_website": True, "place_url": "x"}
        audit = {"audited": True, "reachable": False}
        sw, _ = score_software_fit(biz, audit, biz)
        web, _ = score_website_opportunity(biz, audit)
        self.assertTrue(0 <= sw <= 100)
        self.assertTrue(0 <= web <= 100)


class TestScoreBusinessCompatibilityFields(unittest.TestCase):
    def test_v1_compat_fields_present(self):
        businesses = {"L1": {"name": "X", "rating": "4.0", "reviews": "10", "phone": "0100",
                              "has_website": False, "place_url": "x"}}
        audits = {"L1": {"audited": False}}
        result = score_business("L1", businesses, audits, set(), {})
        self.assertIn("total_score", result)
        self.assertIn("tier", result)
        self.assertEqual(result["total_score"], max(result["score_software_fit"], result["score_website_opportunity"]))


if __name__ == "__main__":
    unittest.main()
