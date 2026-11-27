#!/usr/bin/python3
"""
build_test_set.py --preset [preset name] --candidates [path of candidates JSONL.gz] [options]

Build an input test set from the candidates extracted from an Open Food Facts JSONL dump
by extract_candidates_from_jsonl.py.

For each candidate that matches the selection criteria (language, countries, date of last modification,
categories, complete nutrition facts etc.), this script:
- re-parses the ingredients text with a local Product Opener (parse_ingredients_text + extend_ingredients services),
  so that "percent" fields contain the values specified on the label (the "percent" fields in the dump
  are computed by the percent estimation and can be rescaled)
- checks that the specified percents are consistent (see specified_percent_check.py)
- keeps only the fields relevant to recipe estimation (see clean_input_test_sets.py)
- saves the product in test-sets/input/[test set name]/[code].json

Products are spread across categories: within each category, the most scanned products come first,
and we take at most --per-category-max products per category.

The script also writes a README.md with the parameters and statistics on the test set,
and a test_set_config.conf file read by compute_metrics.py.

Examples:

./scripts/build_test_set.py --list-presets
./scripts/build_test_set.py --preset fr-2026-specified --candidates candidates/candidates-20261005.jsonl.gz
./scripts/build_test_set.py --preset water-loss-crisps --candidates candidates/candidates-20261005.jsonl.gz --dry-run

"""

import argparse
import collections
import datetime
import gzip
import json
import os
import re
import shutil
import sys

import requests

from category_groups import get_category_groups
from clean_input_test_sets import filter_fields
from specified_percent_check import check_specified_percents, problem_type
from specified_quantities import get_specified_quantities

english_speaking_countries = ["en:united-kingdom", "en:ireland", "en:united-states", "en:canada", "en:australia", "en:new-zealand"]

cheese_ingredients_regex = r"cheese|emmental|mozzarella|parmigiano|parmesan|cheddar|comte|gouda|raclette|roquefort|feta|ricotta|mascarpone|gruyere|reblochon|camembert|brie|edam|grana-padano|pecorino|tomme|beaufort|cantal|munster|fromage"

# Declarations of quantities used per 100 g of finished product, typical of products that lost water
# e.g. "153 g de porc pour 100 g", "Préparé avec 50 g de fruits", "prepared with 140g of pork per 100g"
# (a quantity is required before "per 100 g" to avoid matching nutrition tables in the ingredients text)
per_100g_regex = r"\d+(?:[,.]\d+)? ?g (?:de |d'|of )?[^,.;:()]{0,40}(?:pour|per|for) 100 ?g|préparée? avec \d|élaborée? avec \d|prepared with \d|made with \d"

presets = {
    "fr-2026-specified": {
        "description": "Recent products sold in France with an ingredients list in French",
        "ingredients_lc": ["fr"],
        "countries": ["en:france"],
        "modified_after": "2025-01-01",
        "max_products": 1500,
        "per_category_max": 15,
    },
    "en-2026-specified": {
        "description": "Recent products sold in English speaking countries with an ingredients list in English",
        "ingredients_lc": ["en"],
        "countries": english_speaking_countries,
        "modified_after": "2025-01-01",
        "max_products": 1500,
        "per_category_max": 15,
    },
    "water-loss-processed-meat": {
        "description": "Processed meats (hams, sausages, dried meats), which can lose water during processing",
        "ingredients_lc": ["fr", "en"],
        "categories": ["en:prepared-meats", "en:hams", "en:sausages", "en:dried-meats"],
        "modified_after": "2023-01-01",
        "max_products": 500,
        "per_category_max": 60,
        "allow_sum_over_100": True,
        "include_specified_quantities": True,
    },
    "water-loss-crisps": {
        "description": "Crisps, which lose water when fried",
        "ingredients_lc": ["fr", "en"],
        "categories": ["en:crisps", "en:potato-crisps"],
        "modified_after": "2023-01-01",
        "max_products": 500,
        "per_category_max": 60,
        "allow_sum_over_100": True,
        "include_specified_quantities": True,
    },
    "water-loss-dried": {
        "description": "Dried fruits and vegetables and products declaring quantities used per 100 g of finished product",
        "ingredients_lc": ["fr", "en"],
        "categories": ["en:dried-fruits", "en:dried-vegetables", "en:dried-meats"],
        "text_regex": per_100g_regex,
        "modified_after": "2023-01-01",
        "max_products": 500,
        "per_category_max": 40,
        "allow_sum_over_100": True,
        "include_specified_quantities": True,
    },
    "with-cheese": {
        "description": "Cheeses, and products with a specified percent of cheese",
        "ingredients_lc": ["fr", "en"],
        "categories": ["en:cheeses"],
        "specified_ingredient_regex": cheese_ingredients_regex,
        "modified_after": "2023-01-01",
        "max_products": 500,
        "per_category_max": 25,
        "allow_sum_over_100": True,
    },
}

default_options = {
    "description": "",
    "ingredients_lc": None,
    "countries": None,
    "modified_after": None,
    "categories": None,
    "text_regex": None,
    "specified_ingredient_regex": None,
    "max_products": 1000,
    "per_category_max": 20,
    "min_specified_percent_n": 1,
    "max_unknown_ingredients_ratio": 0.2,
    "require_fiber": False,
    "allow_sum_over_100": False,
    # Also select products that have no specified percent but specified quantities for 100 g of product
    # (e.g. "140 g de porc pour 100 g de produit fini"), and take them first in each category
    "include_specified_quantities": False,
}

# Nutrients needed by the models that estimate the recipe from the nutrition facts
required_nutrients = ["fat_100g", "saturated-fat_100g", "carbohydrates_100g", "sugars_100g", "proteins_100g", "salt_100g"]


def to_number(value):
    # Some numeric fields are strings in the exports
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def walk_ingredients(ingredients):
    for ingredient in ingredients or []:
        yield ingredient
        yield from walk_ingredients(ingredient.get("ingredients"))


def has_complete_nutrition(product, require_fiber):
    nutrients = product.get("nutriments") or {}
    if product.get("nutrition_data_per") not in (None, "100g"):
        return False
    if "energy-kcal_100g" not in nutrients and "energy_100g" not in nutrients:
        return False
    needed = required_nutrients + (["fiber_100g"] if require_fiber else [])
    return all(isinstance(nutrients.get(nutrient), (int, float)) for nutrient in needed)


def matches(product, options, modified_after_t):
    """Return the reason why a candidate is rejected, or None if it matches the selection criteria"""
    if options["ingredients_lc"] and product.get("ingredients_lc") not in options["ingredients_lc"]:
        return "ingredients_lc"
    if options["countries"] and not set(product.get("countries_tags") or []).intersection(options["countries"]):
        return "countries"
    if modified_after_t and to_number(product.get("last_modified_t")) < modified_after_t:
        return "modified_before"

    # Products need to match at least one of the categories, text or specified ingredient criteria, if any
    type_criteria = [options["categories"], options["text_regex"], options["specified_ingredient_regex"]]
    if any(type_criteria):
        matched = False
        if options["categories"] and set(product.get("categories_tags") or []).intersection(options["categories"]):
            matched = True
        if not matched and options["text_regex"] and re.search(options["text_regex"], product.get("ingredients_text") or "", re.IGNORECASE):
            matched = True
        if not matched and options["specified_ingredient_regex"]:
            for ingredient in walk_ingredients(product.get("ingredients")):
                if "percent" in ingredient and re.search(options["specified_ingredient_regex"], ingredient.get("id", "")):
                    matched = True
                    break
        if not matched:
            return "product_type"

    if not has_complete_nutrition(product, options["require_fiber"]):
        return "incomplete_nutrition"
    if to_number(product.get("ingredients_with_specified_percent_n")) < options["min_specified_percent_n"]:
        if not (options["include_specified_quantities"] and get_specified_quantities(product)):
            return "not_enough_specified_percents"
    ingredients_n = to_number(product.get("ingredients_n"))
    if ingredients_n < 2:
        return "single_ingredient"
    if to_number(product.get("unknown_ingredients_n")) > options["max_unknown_ingredients_ratio"] * ingredients_n:
        return "too_many_unknown_ingredients"
    return None


def category_key(product):
    # Most specific category, to spread products across categories
    categories = product.get("categories_tags") or []
    return categories[-1] if categories else "none"


def spread_across_categories(products, per_category_max, specified_quantities_first):
    """Order products so that we take the most scanned products of each category in turn
    (products with specified quantities first if specified_quantities_first)"""
    by_category = collections.defaultdict(list)
    for product in products:
        by_category[category_key(product)].append(product)
    for category_products in by_category.values():
        category_products.sort(key=lambda product: (
            specified_quantities_first and not get_specified_quantities(product),
            -to_number(product.get("unique_scans_n")),
            product["code"]))
    # Categories with the most scanned products first
    categories = sorted(by_category, key=lambda category: -sum(to_number(product.get("unique_scans_n")) for product in by_category[category]))
    ordered = []
    for rank in range(per_category_max):
        for category in categories:
            if rank < len(by_category[category]):
                ordered.append(by_category[category][rank])
    return ordered


def parse_ingredients(product, product_opener_url):
    """Re-parse the ingredients text with Product Opener, so that percent values are the ones on the label"""
    product_to_parse = {key: value for key, value in product.items() if key != "ingredients"}
    request_data = {
        "services": ["parse_ingredients_text", "extend_ingredients"],
        "fields": ["all"],
        "product": product_to_parse,
    }
    response = requests.post(product_opener_url, json=request_data, timeout=60)
    response.raise_for_status()
    response_json = response.json()
    if response_json.get("status") != "success" or "product" not in response_json:
        return None
    parsed_product = response_json["product"]
    # Keep selection fields that Product Opener may not return,
    # and the nutriments converted from the nutrition structure by extract_candidates_from_jsonl.py
    for field in ["last_modified_t", "unique_scans_n", "categories_tags", "countries_tags"]:
        if field in product and field not in parsed_product:
            parsed_product[field] = product[field]
    parsed_product["nutriments"] = product.get("nutriments", {})
    return parsed_product


def read_test_set_codes(test_set_names):
    codes = set()
    for test_set_name in test_set_names:
        test_set_path = test_set_name if "/" in test_set_name else "test-sets/input/" + test_set_name
        codes.update(file_name[:-5] for file_name in os.listdir(test_set_path) if file_name.endswith(".json"))
    return codes


def write_readme(test_set_path, test_set_name, options, command, candidates_path, stats, products):
    languages = collections.Counter(product.get("ingredients_lc") for product in products)
    groups = collections.Counter(group for product in products for group in get_category_groups(product.get("categories_tags")))
    categories = collections.Counter(category_key(product) for product in products)
    specified_n = collections.Counter(min(sum(1 for ingredient in walk_ingredients(product.get("ingredients")) if "percent" in ingredient), 5) for product in products)

    lines = [
        f"# {test_set_name}",
        "",
        options["description"],
        "",
        f"Generated on {datetime.date.today().isoformat()} from `{os.path.basename(candidates_path)}` with:",
        "",
        "```",
        command,
        "```",
        "",
        "## Selection criteria",
        "",
    ]
    lines += [f"- {key}: {value}" for key, value in options.items() if key != "description" and value not in (None, False)]
    lines += ["", "## Selection statistics", ""]
    lines += [f"- {key}: {value}" for key, value in stats.items()]
    lines += ["", "## Products", "", f"- number of products: {len(products)}"]
    lines += [f"- ingredients languages: {dict(languages.most_common())}"]
    lines += [f"- number of ingredients with specified percent (5 = 5 or more): {dict(sorted(specified_n.items()))}"]
    lines += [f"- products with specified quantities for 100 g of product: {sum(1 for product in products if get_specified_quantities(product))}"]
    lines += ["", "### Category groups", ""] + [f"- {group}: {count}" for group, count in groups.most_common()]
    lines += ["", "### Most frequent categories", ""] + [f"- {category}: {count}" for category, count in categories.most_common(30)]
    with open(test_set_path + "/README.md", "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preset", choices=sorted(presets), help="named set of selection criteria")
    parser.add_argument("--list-presets", action="store_true", help="print the presets and exit")
    parser.add_argument("--candidates", help="candidates JSONL.gz file generated by extract_candidates_from_jsonl.py")
    parser.add_argument("--name", help="test set name (default: preset name)")
    parser.add_argument("--ingredients-lc", type=lambda s: s.split(","), help="comma separated ingredients languages")
    parser.add_argument("--countries", type=lambda s: s.split(","), help="comma separated countries tags (any)")
    parser.add_argument("--modified-after", help="YYYY-MM-DD")
    parser.add_argument("--categories", type=lambda s: s.split(","), help="comma separated categories tags (any)")
    parser.add_argument("--text-regex", help="regular expression to match on the ingredients text")
    parser.add_argument("--specified-ingredient-regex", help="regular expression to match on the id of an ingredient with a specified percent")
    parser.add_argument("--max-products", type=int)
    parser.add_argument("--per-category-max", type=int)
    parser.add_argument("--min-specified-percent-n", type=int)
    parser.add_argument("--max-unknown-ingredients-ratio", type=float)
    parser.add_argument("--require-fiber", action="store_true", default=None)
    parser.add_argument("--allow-sum-over-100", action="store_true", default=None, help="accept specified percents that sum to more than 100 (water loss)")
    parser.add_argument("--exclude-test-sets", type=lambda s: s.split(","), default=[], help="comma separated test sets whose products are excluded")
    parser.add_argument("--product-opener-url", default="http://world.openfoodfacts.localhost/api/v3/product_services")
    parser.add_argument("--no-parse", action="store_true", help="do not re-parse the ingredients with Product Opener (percent values from the dump may be rescaled)")
    parser.add_argument("--overwrite", action="store_true", help="remove the existing test set directory first")
    parser.add_argument("--dry-run", action="store_true", help="only print selection statistics")
    args = parser.parse_args()

    if args.list_presets:
        for preset_name, preset in presets.items():
            print(f"{preset_name}: {json.dumps(preset, ensure_ascii=False)}")
        return

    if not args.candidates or not (args.preset or args.name):
        parser.error("--candidates and --preset (or --name) are required")

    options = dict(default_options)
    options.update(presets.get(args.preset, {}))
    for key in default_options:
        value = getattr(args, key, None)
        if value is not None:
            options[key] = value

    test_set_name = args.name or args.preset
    test_set_path = "test-sets/input/" + test_set_name
    modified_after_t = None
    if options["modified_after"]:
        modified_after_t = int(datetime.datetime.fromisoformat(options["modified_after"]).replace(tzinfo=datetime.timezone.utc).timestamp())
    excluded_codes = read_test_set_codes(args.exclude_test_sets)

    # Select the candidates that match the criteria
    stats = collections.Counter()
    selected = []
    with gzip.open(args.candidates, "rt", encoding="utf-8") as f:
        for line in f:
            product = json.loads(line)
            stats["candidates"] += 1
            if product["code"] in excluded_codes:
                stats["rejected: in excluded test set"] += 1
                continue
            reason = matches(product, options, modified_after_t)
            if reason:
                stats["rejected: " + reason] += 1
                continue
            selected.append(product)
    stats["matching the criteria"] = len(selected)
    print(json.dumps(stats, indent=2))

    ordered = spread_across_categories(selected, options["per_category_max"], options["include_specified_quantities"])
    stats["after limiting products per category"] = len(ordered)
    print(f"{len(ordered)} products after limiting to {options['per_category_max']} products per category")
    if args.dry_run:
        return

    if os.path.exists(test_set_path):
        if not args.overwrite:
            print(f"Error: {test_set_path} already exists, use --overwrite to replace it")
            sys.exit(1)
        shutil.rmtree(test_set_path)
    os.makedirs(test_set_path)

    # Parse, check and save products until we reach the maximum number of products
    products = []
    inconsistent_types = collections.Counter()
    for product in ordered:
        if len(products) >= options["max_products"]:
            break
        if not args.no_parse:
            try:
                parsed_product = parse_ingredients(product, args.product_opener_url)
            except requests.RequestException as e:
                print(f"Error: could not parse ingredients of {product['code']} with {args.product_opener_url}: {e}")
                sys.exit(1)
            if not parsed_product or not parsed_product.get("ingredients"):
                stats["rejected: parsing failed"] += 1
                continue
            product = parsed_product
        has_specified_quantities = options["include_specified_quantities"] and bool(get_specified_quantities(product))
        if not any("percent" in ingredient for ingredient in walk_ingredients(product["ingredients"])) and not has_specified_quantities:
            stats["rejected: no specified percent after parsing"] += 1
            continue
        problems = check_specified_percents(product["ingredients"], allow_sum_over_100=options["allow_sum_over_100"])
        if problems:
            stats["rejected: inconsistent specified percents"] += 1
            inconsistent_types.update(set(problem_type(problem) for problem in problems))
            continue
        product = filter_fields(product)
        # Computed by Product Opener on the dump data, not reliable (see specified_percent_check.py)
        product.pop("ingredients_percent_analysis", None)
        with open(f"{test_set_path}/{product['code']}.json", "w") as f:
            json.dump(product, f, indent=4, ensure_ascii=False, sort_keys=True)
        products.append(product)
        if len(products) % 100 == 0:
            print(f"{len(products)} products saved")

    stats["saved"] = len(products)
    for problem, count in inconsistent_types.items():
        stats["inconsistent: " + problem] = count

    with open(test_set_path + "/test_set_config.conf", "w") as f:
        json.dump({"allow_sum_over_100": options["allow_sum_over_100"]}, f, indent=4)
    command = " ".join(["./scripts/build_test_set.py"] + sys.argv[1:])
    write_readme(test_set_path, test_set_name, options, command, args.candidates, stats, products)
    print(json.dumps(stats, indent=2))
    print(f"Saved {len(products)} products in {test_set_path}")


if __name__ == "__main__":
    main()
