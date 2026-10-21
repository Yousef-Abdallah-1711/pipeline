# -*- coding: utf-8 -*-
"""
Lead Hunter v2 - Arabic/English query generation for the Egypt B2B
software-prospect playbooks (references/industry-playbooks.md).

Kept as plain data + one small function so it's testable without a
browser or network - see tests/test_query_templates.py.
"""

PLAYBOOKS = {
    "manufacturing": {
        "ar": ["مصانع مواد غذائية", "مصانع بلاستيك", "مصانع أثاث", "مصانع مواد بناء", "مصنع قطع غيار صناعية"],
        "en": ["food manufacturers", "plastics manufacturer", "furniture factory",
               "building materials manufacturer", "industrial spare parts"],
    },
    "distribution": {
        "ar": ["شركات توزيع مواد غذائية", "موزعين أدوية", "توزيع قطع غيار سيارات", "شركة توزيع"],
        "en": ["FMCG distributor", "pharmaceutical distributor", "auto parts wholesaler", "food distribution company"],
    },
    "logistics": {
        "ar": ["شركات شحن ولوجستيات", "شركة نقل بضائع", "مخازن تخزين", "شركة توصيل"],
        "en": ["freight logistics company", "warehousing provider", "fleet operator", "last-mile delivery Egypt"],
    },
    "field_service": {
        "ar": ["شركة صيانة معدات صناعية", "صيانة تكييفات مركزية", "صيانة مصاعد", "شركة صيانة عامة"],
        "en": ["industrial maintenance company", "HVAC maintenance", "elevator servicing", "equipment maintenance Egypt"],
    },
    "pharma_medical": {
        "ar": ["شركة توزيع أدوية", "مستلزمات طبية بالجملة"],
        "en": ["pharmaceutical distributor Egypt", "medical supplies wholesaler"],
    },
    "import_export": {
        "ar": ["شركة استيراد وتصدير", "شركة تجارة عامة"],
        "en": ["import export company Egypt", "trading company Egypt"],
    },
    "construction_supply": {
        "ar": ["شركة توريد مواد بناء", "موزع مواد بناء", "شركة مقاولات توريدات"],
        "en": ["building materials supplier Egypt", "construction materials distributor"],
    },
}


def generate_queries(categories, places, country="Egypt"):
    """categories: list of PLAYBOOKS keys. places: list of city/district
    names (Arabic or English strings, used verbatim). Returns a flat,
    deduplicated list of query strings, Arabic and English, one per
    (category term x place). Order is deterministic for testability."""
    if not categories:
        raise ValueError("generate_queries requires at least one category")
    if not places:
        raise ValueError("generate_queries requires at least one place")

    queries = []
    seen = set()
    for cat in categories:
        if cat not in PLAYBOOKS:
            raise KeyError(f"unknown playbook category: {cat}")
        book = PLAYBOOKS[cat]
        for place in places:
            for term in book["ar"]:
                q = f"{term} {place}"
                if q not in seen:
                    seen.add(q)
                    queries.append(q)
            for term in book["en"]:
                q = f"{term} {place} {country}"
                if q not in seen:
                    seen.add(q)
                    queries.append(q)
    return queries


if __name__ == "__main__":
    import sys
    cats = sys.argv[1].split(",") if len(sys.argv) > 1 else ["manufacturing"]
    places = sys.argv[2].split(",") if len(sys.argv) > 2 else ["Alexandria"]
    for q in generate_queries(cats, places):
        print(q)
