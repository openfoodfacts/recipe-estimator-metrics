#!/usr/bin/python3
"""
Determine on which basis the percents specified on the label are expressed, so that they can be compared
to the right estimate of the models.

EU regulation 1169/2011 Annex VIII and the Commission Notice on QUID (2017/C 393/05):
- general rule (point 3): the percent is the share of the ingredient in the recipe at the time the ingredients
  are added (mixing bowl). It corresponds to the recipe share of the models (percent estimates that sum to 100%).
- foods that have lost moisture following heat treatment or other treatment (point 4(a), e.g. cakes, biscuits, pies,
  dry cured meats): the percent is the quantity of the ingredient used, related to the finished product, and above 100%
  it is expressed as the weight of ingredient used to prepare 100 g of finished product. It corresponds to the
  quantity_estimate of the models (quantity used for 100 g of finished product).

In practice, many labels of products that lost moisture still indicate recipe shares (e.g. crisps with
"pommes de terre 62%, huile de tournesol 37%"), so for those products a specified percent is ambiguous.

Basis of each specified percent:
- "recipe_share": the product is not in a category of products that lose moisture
- "per_100g": the product is in a category of products that lose moisture (or in a test set that allows sums over 100%),
  and the specified percents sum to more than 100%, which is only possible with point 4(a)
- "ambiguous": other specified percents of products in a category of products that lose moisture
- "unknown_relative": percent of a sub ingredient that is relative to its parent ingredient (e.g. "chocolate (cocoa 70%)"),
  but the percent of the parent ingredient is unknown, so we cannot compute the absolute percent

Percents of sub ingredients can be relative to the parent ingredient or absolute (relative to the whole product):
- if the parent percent is known: the sub ingredient percents are absolute if their sum is less than the parent percent,
  otherwise they are relative and converted to absolute percents
- if the parent percent is unknown: the sub ingredient percent is relative if it is greater than the maximum possible
  percent of the parent ingredient (based on the order of ingredients)

Usage (prints the basis of the specified percents of each product of the test sets):

./scripts/label_basis.py test-sets/input/fr-2026-specified
"""

import collections
import json
import os
import sys

from specified_percent_check import check_specified_percents, problem_type, TOLERANCE

# Categories of products that usually lose moisture during their manufacture
moisture_loss_categories = [
    "en:biscuits-and-cakes", "en:breads", "en:pies", "en:pastries", "en:viennoiseries", "en:crackers",
    "en:dry-sausages", "en:cured-hams", "en:dried-hams", "en:dried-meats", "en:chorizo",
    "en:crisps", "en:potato-crisps", "en:dried-fruits", "en:dried-vegetables", "en:fruit-pastes",
]


def is_moisture_loss_product(product):
    return bool(set(product.get("categories_tags") or []).intersection(moisture_loss_categories))


def specified_percents_sum_over_100(ingredients):
    # The order of ingredients and the specified percents imply a total over 100%
    return any(problem_type(problem) == "minimum sum of percents" for problem in check_specified_percents(ingredients))


def get_problems(product, test_set_config=None):
    """Problems with the specified percents of the input product, for which we skip the product.
    Sums over 100% are accepted for products that lose moisture (point 4(a)) and for test sets that allow them."""
    allow_sum_over_100 = (test_set_config or {}).get("allow_sum_over_100", False) or is_moisture_loss_product(product)
    return check_specified_percents(product.get("ingredients"), allow_sum_over_100=allow_sum_over_100)


def get_specified_values(product, test_set_config=None):
    """Return the list of specified percents of the input product:
    [{"path", "id", "label_percent", "value", "basis", "relative"}]
    value is the absolute percent (relative percents of sub ingredients are converted when the parent percent is known)"""
    moisture_loss = is_moisture_loss_product(product) or (test_set_config or {}).get("allow_sum_over_100", False)
    per_100g = moisture_loss and specified_percents_sum_over_100(product.get("ingredients"))
    if per_100g:
        basis = "per_100g"
    elif moisture_loss:
        basis = "ambiguous"
    else:
        basis = "recipe_share"

    values = []

    def walk(ingredients, path, parent_percent, parent_max):
        # parent_percent: absolute percent of the parent ingredient if specified, parent_max: maximum possible percent
        specified = [ingredient["percent"] for ingredient in ingredients if isinstance(ingredient.get("percent"), (int, float))]
        relative = False
        if path and specified:
            if parent_percent is not None:
                relative = sum(specified) > parent_percent + TOLERANCE
            else:
                relative = max(specified) > parent_max + TOLERANCE
        total = parent_percent if parent_percent is not None else parent_max
        previous_max = total
        for i, ingredient in enumerate(ingredients):
            label_percent = ingredient.get("percent")
            ingredient_path = path + (i,)
            # Maximum percent from the order of ingredients: an ingredient is at most the previous ingredient,
            # and at most total / (rank + 1). We ignore it for products whose percents sum to more than 100%.
            ingredient_max = total if per_100g else min(previous_max, total / (i + 1))
            ingredient_percent = None
            if isinstance(label_percent, (int, float)):
                ingredient_basis = basis
                value = label_percent
                if relative:
                    if parent_percent is not None:
                        value = label_percent * parent_percent / 100
                    else:
                        ingredient_basis = "unknown_relative"
                        value = None
                values.append({
                    "path": ingredient_path,
                    "id": ingredient.get("id"),
                    "label_percent": label_percent,
                    "value": value,
                    "basis": ingredient_basis,
                    "relative": relative,
                })
                if value is not None:
                    ingredient_percent = value
                    ingredient_max = value
            if not per_100g:
                previous_max = ingredient_max
            if ingredient.get("ingredients"):
                walk(ingredient["ingredients"], ingredient_path, ingredient_percent, ingredient_max)

    walk(product.get("ingredients") or [], (), None, 100)
    return values


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: label_basis.py [paths of one or more input test sets]")
        sys.exit(1)

    for test_set_path in sys.argv[1:]:
        test_set_config = {}
        if os.path.exists(test_set_path + "/test_set_config.conf"):
            with open(test_set_path + "/test_set_config.conf", "r") as f:
                test_set_config = json.load(f)
        counts = collections.Counter()
        products = collections.Counter()
        for file_name in sorted(os.listdir(test_set_path)):
            if not file_name.endswith(".json"):
                continue
            with open(os.path.join(test_set_path, file_name), "r") as f:
                product = json.load(f)
            if get_problems(product, test_set_config):
                counts["skipped (inconsistent)"] += 1
                continue
            values = get_specified_values(product, test_set_config)
            for basis in set(value["basis"] for value in values):
                products[basis] += 1
            for value in values:
                counts[value["basis"]] += 1
                if value["relative"] and value["value"] is not None:
                    counts["relative converted to absolute"] += 1
                if value["basis"] in ("per_100g", "unknown_relative") or (value["relative"] and value["value"] is not None):
                    print(f"{product.get('code')}: {value['basis']} {value['id']} {value['label_percent']}% -> {value['value']}  | {(product.get('ingredients_text') or '')[:120]}")
        print(f"\n{test_set_path}: values {dict(counts)}, products {dict(products)}")
