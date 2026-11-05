#!/usr/bin/python3
"""
extract_candidates_from_jsonl.py [path to Open Food Facts JSONL dump] [path of output candidates JSONL.gz]

Goes through an Open Food Facts JSONL export (openfoodfacts-products.jsonl.gz) and keeps only products
that have at least one ingredient with a specified percent (en:some-ingredients-with-specified-percent misc tag)
or a specified quantity (quantity_g field in ingredients or specific_ingredients).
Only the fields that can be useful to build test sets are kept, so that the output is small enough
to be quickly read many times by build_test_set.py.

Example:

./scripts/extract_candidates_from_jsonl.py ~/recipe-estimator/ingredients_distributions/openfoodfacts-products-20261005.jsonl.gz candidates/candidates-20261005.jsonl.gz

"""

import gzip
import json
import shutil
import subprocess
import sys
import time

# Fields used by the metrics and the models (see clean_input_test_sets.py), and fields used to select products
fields_to_keep = [
    "code",
    "allergens",
    "product_name",
    "brands",
    "brands_tags",
    "lang",
    "lc",
    "ingredients",
    "ingredients_text",
    "ingredients_lc",
    "ingredients_percent_analysis",
    "ingredients_with_specified_percent_n",
    "ingredients_with_specified_percent_sum",
    "ingredients_n",
    "unknown_ingredients_n",
    "nutriments",
    "nutrition_data_per",
    "misc_tags",
    "categories_tags",
    "labels_tags",
    "countries_tags",
    "data_quality_errors_tags",
    "percent_ingredients_with_ciqual_code",
    "percent_ingredients_with_ciqual_or_proxy_code",
    "schema_version",
    "specific_ingredients",
    "created_t",
    "last_modified_t",
    "unique_scans_n",
    "popularity_key",
]


def nutriments_from_nutrition(nutrition):
    """Convert the nutrition structure of schema version 1004 and later to the legacy nutriments structure
    (e.g. fat_100g) used by the models. We only keep values from the packaging, as sold, per 100g."""
    nutriments = {}
    aggregated_set = (nutrition or {}).get("aggregated_set") or {}
    if aggregated_set.get("per") != "100g" or aggregated_set.get("preparation") != "as_sold":
        return nutriments
    for nutrient, nutrient_data in (aggregated_set.get("nutrients") or {}).items():
        if nutrient_data.get("source") == "estimate" or not isinstance(nutrient_data.get("value"), (int, float)):
            continue
        nutriments[nutrient] = nutrient_data["value"]
        nutriments[nutrient + "_100g"] = nutrient_data["value"]
        nutriments[nutrient + "_unit"] = nutrient_data.get("unit", "")
    return nutriments


# Quick text filter before decoding the JSON: products with specified percents,
# or with specified quantities (e.g. "140 g de porc pour 100 g de produit fini")
markers = ['"en:some-ingredients-with-specified-percent"'.encode(), '"quantity_g"'.encode()]

if len(sys.argv) < 3:
    print("Usage: extract_candidates_from_jsonl.py [path to Open Food Facts JSONL dump] [path of output candidates JSONL.gz]")
    sys.exit(1)

dump_path = sys.argv[1]
output_path = sys.argv[2]

# pigz decompresses much faster than the gzip module
if shutil.which("pigz"):
    decompress = subprocess.Popen(["pigz", "-dc", dump_path], stdout=subprocess.PIPE)
    lines = decompress.stdout
else:
    lines = gzip.open(dump_path, "rb")

start_time = time.time()
products_n = 0
candidates_n = 0

with gzip.open(output_path, "wt", encoding="utf-8", compresslevel=6) as output:
    for line in lines:
        products_n += 1
        if products_n % 500000 == 0:
            print(f"{products_n} products read, {candidates_n} candidates, {time.time() - start_time:.0f}s", flush=True)
        if not any(marker in line for marker in markers):
            continue
        try:
            product = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not product.get("ingredients") or not product.get("ingredients_text"):
            continue
        candidate = {field: product[field] for field in fields_to_keep if field in product}
        if not candidate.get("nutriments") and product.get("nutrition"):
            candidate["nutriments"] = nutriments_from_nutrition(product["nutrition"])
            candidate["nutrition_data_per"] = "100g"
        # Keep the ingredients text in the language of the ingredients, as ingredients_text can be in another language
        ingredients_lc = product.get("ingredients_lc")
        if ingredients_lc and product.get("ingredients_text_" + ingredients_lc):
            candidate["ingredients_text_" + ingredients_lc] = product["ingredients_text_" + ingredients_lc]
        output.write(json.dumps(candidate, ensure_ascii=False) + "\n")
        candidates_n += 1

print(f"Done: {products_n} products read, {candidates_n} candidates saved to {output_path}, {time.time() - start_time:.0f}s")
