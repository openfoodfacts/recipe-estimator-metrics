#!/usr/bin/python3
"""
Check that the percent values specified on the label (the "percent" field of input ingredients)
are consistent with each other and with the order of the ingredients.

Used by:
- compute_metrics.py to decide which products to skip (instead of relying on Product Opener's
  ingredients_percent_analysis field, which depends on the model that produced the result,
  can be stale, and flags some valid products as impossible)
- build_test_set.py to exclude products with inconsistent percent values

The check only uses the specified percent values, it does not try to estimate unspecified ones:
- each specified percent must be > 0
- ingredients are listed by decreasing weight, so every ingredient before an ingredient with a
  specified percent p weighs at least p. The sum of those lower bounds must not exceed the total
  (100 for the top level). Ingredients under 2% can be listed in any order (EU regulation 1169/2011),
  so they do not constrain the ingredients before them.
- sub ingredients percent can be relative to the parent (sum to 100) or absolute (sum to the parent percent),
  we accept both.

Products that lost water (e.g. dried meats) can declare more than 100g of an ingredient per 100g of finished product.
With allow_sum_over_100, sums over 100 are accepted (but the order constraints are still checked).

Usage (prints the problems found for each product of the test sets):

./scripts/specified_percent_check.py test-sets/input/fr-1000-some-specified-popular
"""

import json
import os
import sys
import collections

# Tolerance in percentage points, for rounding on labels
TOLERANCE = 1.0
# Ingredients under this percent can be listed in any order
ANY_ORDER_THRESHOLD = 2


def check_level(ingredients, total, allow_sum_over_100, path, problems):
    # lower bound for the weight of each ingredient, based on its own percent
    # and on the percent of the ingredients that follow it
    lower_bounds = [0] * len(ingredients)
    for i, ingredient in enumerate(ingredients):
        percent = ingredient.get("percent")
        if percent is None:
            continue
        if percent <= 0:
            problems.append(f"{path}{ingredient.get('id')}: percent <= 0")
            continue
        lower_bounds[i] = max(lower_bounds[i], percent)
        if percent >= ANY_ORDER_THRESHOLD:
            for k in range(i):
                prior_percent = ingredients[k].get("percent")
                if prior_percent is not None and prior_percent + TOLERANCE < percent:
                    problems.append(f"{path}{ingredient.get('id')}: {percent}% is greater than previous {ingredients[k].get('id')} {prior_percent}%")
                lower_bounds[k] = max(lower_bounds[k], percent)

    if not allow_sum_over_100:
        sum_of_lower_bounds = sum(lower_bounds)
        if sum_of_lower_bounds > total + TOLERANCE:
            problems.append(f"{path}minimum sum of percents {round(sum_of_lower_bounds, 1)} is greater than {round(total, 1)}")


def check_ingredients(ingredients, total, allow_sum_over_100, path, problems):
    check_level(ingredients, total, allow_sum_over_100, path, problems)
    for ingredient in ingredients:
        sub_ingredients = ingredient.get("ingredients")
        if not sub_ingredients:
            continue
        sub_path = f"{path}{ingredient.get('id')} > "
        sub_problems = []
        # Sub ingredients percents may be relative to the parent, so we check against 100
        # (which is also an upper bound if they are absolute)
        check_ingredients(sub_ingredients, 100, allow_sum_over_100, sub_path, sub_problems)
        problems.extend(sub_problems)


def check_specified_percents(ingredients, allow_sum_over_100=False):
    """Return a list of problems found in the specified percents (empty list if consistent)"""
    problems = []
    check_ingredients(ingredients or [], 100, allow_sum_over_100, "", problems)
    return problems


def problem_type(problem):
    # Short type of a problem string, used to aggregate counts
    for problem_type in ["percent <= 0", "is greater than previous", "minimum sum of percents"]:
        if problem_type in problem:
            return problem_type
    return problem


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: specified_percent_check.py [paths of one or more input test sets]")
        sys.exit(1)

    for test_set_path in sys.argv[1:]:
        products_n = 0
        inconsistent_n = 0
        problem_types = collections.Counter()
        for file_name in sorted(os.listdir(test_set_path)):
            if not file_name.endswith(".json"):
                continue
            with open(os.path.join(test_set_path, file_name), "r") as f:
                product = json.load(f)
            products_n += 1
            problems = check_specified_percents(product.get("ingredients"))
            if problems:
                inconsistent_n += 1
                problem_types.update(set(problem_type(problem) for problem in problems))
                print(f"{product.get('code')}: {'; '.join(problems)}")
                print(f"    {(product.get('ingredients_text') or '')[:200]}")
        print(f"\n{test_set_path}: {inconsistent_n} products with inconsistent percents out of {products_n}")
        print(dict(problem_types))
