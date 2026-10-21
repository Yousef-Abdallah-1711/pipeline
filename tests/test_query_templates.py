# -*- coding: utf-8 -*-
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from query_templates import generate_queries, PLAYBOOKS


class TestQueryGeneration(unittest.TestCase):
    def test_generates_both_languages(self):
        qs = generate_queries(["manufacturing"], ["الإسكندرية"])
        self.assertTrue(any("مصانع" in q for q in qs), "expected at least one Arabic query")
        self.assertTrue(any("manufacturer" in q or "manufacturers" in q for q in qs), "expected at least one English query")

    def test_no_duplicate_queries(self):
        qs = generate_queries(["manufacturing", "distribution"], ["الإسكندرية", "دمنهور"])
        self.assertEqual(len(qs), len(set(qs)), "generate_queries must not return duplicates")

    def test_unknown_category_raises(self):
        with self.assertRaises(KeyError):
            generate_queries(["not_a_real_category"], ["Cairo"])

    def test_empty_inputs_raise(self):
        with self.assertRaises(ValueError):
            generate_queries([], ["Cairo"])
        with self.assertRaises(ValueError):
            generate_queries(["manufacturing"], [])

    def test_every_playbook_has_both_languages_nonempty(self):
        for name, book in PLAYBOOKS.items():
            self.assertTrue(book.get("ar"), f"{name} missing Arabic terms")
            self.assertTrue(book.get("en"), f"{name} missing English terms")

    def test_scales_with_places(self):
        one_place = generate_queries(["manufacturing"], ["الإسكندرية"])
        two_places = generate_queries(["manufacturing"], ["الإسكندرية", "دمنهور"])
        self.assertEqual(len(two_places), len(one_place) * 2)


if __name__ == "__main__":
    unittest.main()
