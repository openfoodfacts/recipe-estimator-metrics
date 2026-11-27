#!/usr/bin/python3
"""
Broad groups of Open Food Facts categories, used to report metrics by type of product
(compute_metrics.py) and to select products for specialized test sets (build_test_set.py).

A product can be in several groups (e.g. a chocolate spread is in "spreads" and "chocolates").
"""

category_groups = {
    "cheeses": ["en:cheeses"],
    "processed meats": ["en:prepared-meats", "en:hams", "en:sausages", "en:dried-meats"],
    "crisps": ["en:crisps", "en:potato-crisps"],
    "dried fruits and vegetables": ["en:dried-fruits", "en:dried-vegetables"],
    "meals": ["en:meals"],
    "soups": ["en:soups"],
    "sauces": ["en:sauces"],
    "yogurts and dairy desserts": ["en:yogurts", "en:dairy-desserts"],
    "biscuits and cakes": ["en:biscuits-and-cakes"],
    "breads": ["en:breads"],
    "breakfast cereals": ["en:breakfast-cereals"],
    "chocolates": ["en:chocolates"],
    "spreads": ["en:spreads"],
    "jams": ["en:jams"],
    "fats": ["en:fats"],
    "fishes and seafood": ["en:fishes", "en:seafood"],
    "plant-based milks": ["en:plant-based-milks", "en:plant-based-beverages"],
    "beverages": ["en:beverages"],
}


def get_category_groups(categories_tags):
    """Return the list of groups that the product categories belong to"""
    categories = set(categories_tags or [])
    return [group for group, tags in category_groups.items() if categories.intersection(tags)]
