#!/usr/bin/python3
"""
function to compute metrics for a model on a test set

Used by:
- run_model_on_input_test_sets.py
- compute_metrics_for_model_on_test_sets.py

To compute metrics, we go through each product JSON file of the specified input test sets to:
- Compute accuracy metrics comparing the estimated "percent_estimate" field in the resulting product
to the "percent" field in the input product
- Store product level metrics in the resulting product
- Aggregate metrics by test set
"""

import json
import os
import csv
import math

from specified_percent_check import problem_type
from label_basis import get_problems, get_specified_values
from category_groups import get_category_groups
from specified_quantities import get_specified_quantities, get_ingredient_by_path

round_to_n = lambda x, n: x if x == 0 else round(x, -int(math.floor(math.log10(abs(x)))) + (n - 1))

def average(total, count):
    return round_to_n(total / count, 4) if count else 0

def add_missing_estimates_for_parent_ingredients(ingredients):
    # Add missing percent_estimate to parent ingredients by summing the percent_estimate of their children
    for ingredient in ingredients:
        if "ingredients" in ingredient:
            add_missing_estimates_for_parent_ingredients(ingredient["ingredients"])
            if "percent_estimate" not in ingredient:
                ingredient["percent_estimate"] = sum([sub_ingredient.get("percent_estimate", 0) for sub_ingredient in ingredient["ingredients"]])
            if "quantity_estimate" not in ingredient:
                sub_ingredient_quantity = sum([sub_ingredient.get("quantity_estimate", 0) for sub_ingredient in ingredient["ingredients"]])
                if sub_ingredient_quantity > 0:
                    ingredient["quantity_estimate"] = sub_ingredient_quantity

def compare_input_ingredients_to_resulting_ingredients(input_ingredients, resulting_ingredients, ingredients_stats, products_ingredients_csv_writer, test_name):
    # Compute difference metrics for each ingredient and nested sub ingredient comparing the input percent to the resulting percent_estimate

    total_difference = 0
    total_variance = 0
    total_specified_input_percent = 0
    number_of_ingredients_without_ciqual_code = 0
    # Difference between the quantity_estimate (quantity used for 100g of finished product, before water loss)
    # and the specified percent. For products that lost water, the label percent is the quantity used for 100g of product
    # (EU regulation 1169/2011 Annex VIII), so this is the relevant difference for those products.
    total_quantity_difference = 0
    number_of_specified_ingredients = 0

    # add missing percent_estimate to parent ingredients by summing the percent_estimate of their children
    add_missing_estimates_for_parent_ingredients(resulting_ingredients)

    for i, input_ingredient in enumerate(input_ingredients):
        if i >= len(resulting_ingredients):
            # Deal with PEFAP
            continue
        resulting_ingredient = resulting_ingredients[i]

        input_ingredient_id = input_ingredient['id']
        input_percent = 0
        input_percent_is_specified = False
        rounded_resulting_percent_estimate = 0
        rounded_resulting_quantity_estimate = None
        difference = 0
        variance = 0

        # If the resulting ingredient does not have a percent_estimate, we set it to 0 for metrics computation
        if "percent_estimate" in resulting_ingredient:
            # Round the computed percent to 3 significant figures so diffs aren't excessive
            rounded_resulting_percent_estimate = round_to_n(resulting_ingredient["percent_estimate"], 3)
            resulting_ingredient['percent_estimate'] = rounded_resulting_percent_estimate

        # Tried using quantity_estimate referring to https://bryantresearch.co.uk/foodlaw/label/quid-ex3-prepared-with.htm
        # but it just isn't reliable
        if "quantity_estimate" in resulting_ingredient:
            # Round the computed percent to 3 significant figures so diffs aren't excessive
            resulting_ingredient['quantity_estimate'] = round_to_n(resulting_ingredient["quantity_estimate"], 3)
            rounded_resulting_quantity_estimate = resulting_ingredient['quantity_estimate']

        # We compute metrics for known percent in the input product
        if "percent" in input_ingredient:
            input_percent = input_ingredient["percent"]
            input_percent_is_specified = True
            total_specified_input_percent += input_percent
            number_of_specified_ingredients += 1

            # Use rounded estimate here so results don't change if metrics are recalculated
            difference = abs(rounded_resulting_percent_estimate - input_percent)
            rounded_difference = round_to_n(difference, 3)
            # Store the difference at the ingredient level. 
            resulting_ingredient["difference"] = rounded_difference
            total_difference += difference
            variance = difference ** 2
            total_variance += variance
            # Models that do not estimate water loss do not have a quantity_estimate: quantity = percent
            if rounded_resulting_quantity_estimate is None:
                rounded_resulting_quantity_estimate = rounded_resulting_percent_estimate
            total_quantity_difference += abs(rounded_resulting_quantity_estimate - input_percent)
            # Write to summary CSV file.
            products_ingredients_csv_writer.writerow([test_name, input_ingredient['id'], input_percent, rounded_resulting_percent_estimate, rounded_difference, round_to_n(variance, 3)])
        
        # Compare sub ingredients if any
        if "ingredients" in input_ingredient and len(input_ingredient["ingredients"]) > 0:
            input_sub_ingredients = input_ingredient["ingredients"]
            # check that we also have sub ingredients in the resulting ingredient
            if "ingredients" not in resulting_ingredient:
                print(f"Error: missing sub ingredients in resulting ingredient for {input_ingredient['id']}")
                # seems to happen with PEFAP. The metrics comparison is not valid in this case.
                continue
            else:
                resulting_sub_ingredients = resulting_ingredient["ingredients"]

            (total_specified_input_percent, total_difference, total_variance, number_of_ingredients_without_ciqual_code, total_quantity_difference, number_of_specified_ingredients) = [x + y for x, y in zip(
                [total_specified_input_percent, total_difference, total_variance, number_of_ingredients_without_ciqual_code, total_quantity_difference, number_of_specified_ingredients],
                compare_input_ingredients_to_resulting_ingredients(input_sub_ingredients, resulting_sub_ingredients, ingredients_stats, products_ingredients_csv_writer, test_name))]
        else:
            # Aggregate stats for the ingredient
            # We only do it for leaf ingredients, as parent ingredients are not used in the linear solving

            ciqual_food_code = input_ingredient.get("ciqual_food_code")
            ciqual_proxy_food_code = input_ingredient.get("ciqual_proxy_food_code")
            if ciqual_food_code is None and ciqual_proxy_food_code is None:
                number_of_ingredients_without_ciqual_code += 1

            if input_ingredient_id not in ingredients_stats:
                ingredients_stats[input_ingredient_id] = {
                    'total_input_percent': 0,
                    "total_percent_estimate": 0,
                    "total_difference": 0,
                    "total_variance": 0,
                    "number_of_products": 0,
                    "number_of_products_where_specified": 0,
                    'is_in_taxonomy': input_ingredient.get('is_in_taxonomy'),
                    "ciqual_food_code": ciqual_food_code,
                    "ciqual_proxy_food_code": ciqual_proxy_food_code
                }
                
            ingredients_stats[input_ingredient_id]["total_percent_estimate"] += rounded_resulting_percent_estimate
            ingredients_stats[input_ingredient_id]["total_difference"] += difference
            ingredients_stats[input_ingredient_id]["total_variance"] += variance
            ingredients_stats[input_ingredient_id]["number_of_products"] += 1
            if input_percent_is_specified:
                ingredients_stats[input_ingredient_id]["number_of_products_where_specified"] += 1
                ingredients_stats[input_ingredient_id]["total_input_percent"] += input_percent

    return (total_specified_input_percent, total_difference, total_variance, number_of_ingredients_without_ciqual_code, total_quantity_difference, number_of_specified_ingredients)

def compare_input_product_to_resulting_product(input_product, resulting_product, ingredients_stats, products_ingredients_csv_writer, test_name):
    
    if not isinstance(input_product, dict) or not isinstance(resulting_product, dict):
        raise ValueError("Input product and resulting product must be dictionaries")
    
    if "ingredients" not in input_product:
        raise ValueError("Input product must have an 'ingredients' field")
    
    if "ingredients" not in resulting_product:
        raise ValueError("Resulting product must have an 'ingredients' field")
        
    (total_specified_input_percent, total_difference, total_variance, number_of_ingredients_without_ciqual_code, total_quantity_difference, number_of_specified_ingredients) = compare_input_ingredients_to_resulting_ingredients(input_product["ingredients"], resulting_product["ingredients"], ingredients_stats, products_ingredients_csv_writer, test_name)

    resulting_product["ingredients_metrics"] = {
        "total_specified_input_percent": round_to_n(total_specified_input_percent,3),
        "total_difference": round_to_n(total_difference,3),
        "total_variance": round_to_n(total_variance,3),
        "number_of_ingredients_without_ciqual_code": number_of_ingredients_without_ciqual_code,
        "total_quantity_difference": round_to_n(total_quantity_difference,3),
        "number_of_specified_ingredients": number_of_specified_ingredients,
    }
    # If we have some specified input percent, compute the relative difference
    if (total_specified_input_percent > 0):
        resulting_product["ingredients_metrics"]["relative_difference"] = round_to_n(total_difference / total_specified_input_percent,3)
    if (number_of_specified_ingredients > 0):
        resulting_product["ingredients_metrics"]["difference_per_specified_ingredient"] = round_to_n(total_difference / number_of_specified_ingredients,3)

    pass

def compare_specified_quantities(input_product, resulting_product):
    # Compare the quantities specified on the label for 100g of product (e.g. "140 g de porc pour 100 g de produit fini")
    # to the quantity_estimate of the matched ingredients (or percent_estimate if the model does not estimate quantities).
    # Must be called after compare_input_product_to_resulting_product, which adds missing estimates to parent ingredients.
    specified_quantities_metrics = []
    unmatched = 0
    for specified_quantity in get_specified_quantities(input_product):
        if not specified_quantity["paths"]:
            unmatched += 1
            continue
        quantity_estimate = 0
        specified_percent = None
        for path in specified_quantity["paths"]:
            resulting_ingredient = get_ingredient_by_path(resulting_product["ingredients"], path)
            if resulting_ingredient is not None:
                quantity_estimate += resulting_ingredient.get("quantity_estimate", resulting_ingredient.get("percent_estimate", 0))
            # Some products specify both a percent and a quantity for the same ingredient (e.g. "pork 91%" and "145 g of pork for 100 g")
            input_ingredient = get_ingredient_by_path(input_product["ingredients"], path)
            if input_ingredient is not None and "percent" in input_ingredient:
                specified_percent = (specified_percent or 0) + input_ingredient["percent"]
        specified_quantity_metrics = {
            "id": specified_quantity["id"],
            "matched_ingredients": [get_ingredient_by_path(input_product["ingredients"], path).get("id") for path in specified_quantity["paths"]],
            "source": specified_quantity["source"],
            "specified_quantity": specified_quantity["quantity_g"],
            "quantity_estimate": round_to_n(quantity_estimate, 3),
            "difference": round_to_n(abs(quantity_estimate - specified_quantity["quantity_g"]), 3),
        }
        if specified_percent is not None:
            specified_quantity_metrics["specified_percent"] = specified_percent
        specified_quantities_metrics.append(specified_quantity_metrics)

    resulting_product["ingredients_metrics"]["specified_quantities"] = specified_quantities_metrics
    resulting_product["ingredients_metrics"]["number_of_specified_quantities"] = len(specified_quantities_metrics)
    resulting_product["ingredients_metrics"]["number_of_unmatched_specified_quantities"] = unmatched
    resulting_product["ingredients_metrics"]["total_specified_quantity_difference"] = round_to_n(sum(metrics["difference"] for metrics in specified_quantities_metrics), 3)


label_bases = ["recipe_share", "per_100g", "ambiguous"]


def compare_label_basis(input_product, resulting_product, test_set_config):
    # Compare each specified percent to the estimate that corresponds to the basis of the label (see label_basis.py):
    # - recipe_share: share of the ingredient in the recipe, computed from the percent_estimate of the model
    #   rescaled so that top level ingredients sum to 100% (some models return percents that sum to more than 100%)
    # - per_100g: quantity used for 100 g of finished product: quantity_estimate (or percent_estimate if the model
    #   does not estimate quantities)
    # - ambiguous: both differences are computed
    # Must be called after compare_input_product_to_resulting_product, which adds missing estimates to parent ingredients.
    top_level_sum = sum(ingredient.get("percent_estimate", 0) for ingredient in resulting_product["ingredients"])
    recipe_share_factor = 100 / top_level_sum if top_level_sum > 0 else 1

    metrics = {basis: {"number_of_values": 0, "total_difference": 0} for basis in label_bases}
    metrics["ambiguous"]["total_difference_as_per_100g"] = 0
    metrics["unknown_relative"] = {"number_of_values": 0}
    for value in get_specified_values(input_product, test_set_config):
        basis = value["basis"]
        if basis == "unknown_relative":
            metrics[basis]["number_of_values"] += 1
            continue
        resulting_ingredient = get_ingredient_by_path(resulting_product["ingredients"], value["path"])
        if resulting_ingredient is None:
            continue
        percent_estimate = resulting_ingredient.get("percent_estimate", 0)
        recipe_share_estimate = percent_estimate * recipe_share_factor
        quantity_estimate = resulting_ingredient.get("quantity_estimate", percent_estimate)
        metrics[basis]["number_of_values"] += 1
        if basis == "per_100g":
            metrics[basis]["total_difference"] += abs(quantity_estimate - value["value"])
        else:
            metrics[basis]["total_difference"] += abs(recipe_share_estimate - value["value"])
        if basis == "ambiguous":
            metrics[basis]["total_difference_as_per_100g"] += abs(quantity_estimate - value["value"])

    for basis_metrics in metrics.values():
        for key in basis_metrics:
            if key.startswith("total_"):
                basis_metrics[key] = round_to_n(basis_metrics[key], 3)
    resulting_product["ingredients_metrics"]["label_basis"] = metrics


def compute_metrics_for_test_set(results_path, test_set_name):
    # Compute average metrics for the test set
    test_set_total_difference = 0
    test_set_total_variance = 0
    test_set_number_of_products = 0
    skipped_products = 0
    skipped_products_problems = {}
    # Average of the product differences per specified ingredient,
    # so that products with many specified percents do not weigh more than products with few
    # (the average of relative_difference is not used as it is dominated by products with small specified percents)
    test_set_total_difference_per_specified_ingredient = 0
    test_set_number_of_products_with_specified_ingredients = 0
    test_set_total_quantity_difference = 0
    # Metrics by group of categories
    category_groups_stats = {}
    # Specified quantities for 100g of product (see specified_quantities.py)
    test_set_number_of_products_with_specified_quantities = 0
    test_set_number_of_specified_quantities = 0
    test_set_number_of_unmatched_specified_quantities = 0
    test_set_total_specified_quantity_difference = 0
    test_set_number_of_specified_quantities_with_specified_percent = 0
    # Differences by basis of the specified percents (see label_basis.py)
    label_basis_stats = {basis: {"number_of_products": 0, "number_of_values": 0, "total_difference": 0} for basis in label_bases}
    label_basis_stats["ambiguous"]["total_difference_as_per_100g"] = 0
    label_basis_stats["unknown_relative"] = {"number_of_values": 0}
    # and for products that have ciqual food codes or proxy food codes for all ingredients
    all_ciqual_test_set_total_difference = 0
    all_ciqual_test_set_total_variance = 0
    all_ciqual_test_set_number_of_products = 0

    # Compute aggregated stats (number of products and total difference) for each ingredient
    ingredients_stats = {}

    # Optional test set configuration written by build_test_set.py
    test_set_config = {}
    test_set_config_path = 'test-sets/input/' + test_set_name + '/test_set_config.conf'
    if os.path.exists(test_set_config_path):
        with open(test_set_config_path, "r") as f:
            test_set_config = json.load(f)

    # Store the details of the metrics at the product + ingredient level, and at the product level
    result_set_path = results_path + "/" + test_set_name
    with open(result_set_path + "/products_stats.csv", "w", newline="") as products_csv, \
         open(result_set_path + "/products_ingredients_stats.csv", "w", newline="") as products_ingredients_csv:
        products_csv_writer = csv.writer(products_csv)
        products_csv_writer.writerow(['test_name', 'total_difference','total_variance','number_of_ingredients_without_ciqual_code','ingredients_text','relative_difference','difference_per_specified_ingredient','total_quantity_difference','total_specified_quantity_difference'])
        products_ingredients_csv_writer = csv.writer(products_ingredients_csv)
        products_ingredients_csv_writer.writerow(['test_name','ingredient','percent','percent_estimate','difference','variance'])

        # Go through each JSON file in the input test set directory. Sort so that summary results order is consistent

        for test_name in sorted(os.listdir(result_set_path)):

            # Read the input product
            test_path = 'test-sets/input/' + test_set_name + '/' + test_name
            try:
                with open(test_path, "r") as f:
                    input_product = json.load(f)
            except:
                continue

            # Read the corresponding resulting product
            result_path = result_set_path + '/' + test_name
            print("Computing metrics for " + result_path)
            try:
                with open(result_path, "r") as f:
                    resulting_product = json.load(f)
            except:
                with open(result_path, "r", encoding = 'cp1252') as f:
                    resulting_product = json.load(f)

            # Skip products for which the specified percents of the input product are inconsistent.
            # Those are most likely data errors or ingredient parsing errors.
            # We remove them as they often result in huge differences that are in fact meaningless.
            # e.g. "Cacao maigre (beurre de cacao 11%), en poudre, sucre, arôme, Cacao 70%"
            # -> the last Cacao 70% is counted as an actual ingredient with a known 70%, while it indicates the cocoa % of the first ingredient.
            # The check is done on the input product so that all models are evaluated on the same products
            # (the ingredients_percent_analysis field of the result depends on the model).
            # Products that lose moisture can have specified percents that sum to more than 100% (see label_basis.py)
            problems = get_problems(input_product, test_set_config)
            if problems:
                skipped_products += 1
                for problem in set(problem_type(problem) for problem in problems):
                    skipped_products_problems[problem] = skipped_products_problems.get(problem, 0) + 1
                print("Skipping product with inconsistent specified percents: " + result_path + ": " + "; ".join(problems))
                continue

            # Compute accuracy metrics comparing the estimated "percent_estimate" field in the resulting product
            # to the "percent" field in the input product
            compare_input_product_to_resulting_product(input_product, resulting_product, ingredients_stats, products_ingredients_csv_writer, test_name)
            compare_specified_quantities(input_product, resulting_product)
            compare_label_basis(input_product, resulting_product, test_set_config)

            # Remove fields that change between runs
            if "recipe_estimator" in resulting_product:
                if "time" in resulting_product["recipe_estimator"]:
                    del resulting_product["recipe_estimator"]["time"]

            # Store product level metrics in the resulting product
            with open(result_path, "w") as f:
                print("Saving metrics in result: " + result_path)
                json.dump(resulting_product, f,  indent=4, ensure_ascii=False, sort_keys=True)

            # Write to the products summary CSV file
            products_csv_writer.writerow([test_name,
                                          resulting_product["ingredients_metrics"]["total_difference"],
                                          resulting_product["ingredients_metrics"]["total_variance"],
                                          resulting_product["ingredients_metrics"]["number_of_ingredients_without_ciqual_code"],
                                          resulting_product["ingredients_text"],
                                          resulting_product["ingredients_metrics"].get("relative_difference", ""),
                                          resulting_product["ingredients_metrics"].get("difference_per_specified_ingredient", ""),
                                          resulting_product["ingredients_metrics"]["total_quantity_difference"],
                                          resulting_product["ingredients_metrics"]["total_specified_quantity_difference"]])

            # Aggregate specified quantities metrics
            if resulting_product["ingredients_metrics"]["number_of_specified_quantities"] > 0:
                test_set_number_of_products_with_specified_quantities += 1
            test_set_number_of_specified_quantities += resulting_product["ingredients_metrics"]["number_of_specified_quantities"]
            test_set_number_of_unmatched_specified_quantities += resulting_product["ingredients_metrics"]["number_of_unmatched_specified_quantities"]
            test_set_total_specified_quantity_difference += resulting_product["ingredients_metrics"]["total_specified_quantity_difference"]
            test_set_number_of_specified_quantities_with_specified_percent += sum(1 for metrics in resulting_product["ingredients_metrics"]["specified_quantities"] if "specified_percent" in metrics)

            # Aggregate differences by basis of the specified percents
            label_basis_metrics = resulting_product["ingredients_metrics"]["label_basis"]
            for basis, basis_metrics in label_basis_metrics.items():
                basis_stats = label_basis_stats[basis]
                if basis_metrics["number_of_values"] > 0 and "number_of_products" in basis_stats:
                    basis_stats["number_of_products"] += 1
                for key, value in basis_metrics.items():
                    basis_stats[key] += value

            for group in get_category_groups(input_product.get("categories_tags")):
                if group not in category_groups_stats:
                    category_groups_stats[group] = {"number_of_products": 0, "total_difference": 0, "total_difference_per_specified_ingredient": 0, "total_quantity_difference": 0,
                                                    "recipe_share_number_of_products": 0, "recipe_share_total_difference": 0,
                                                    "ambiguous_number_of_products": 0, "ambiguous_total_difference": 0, "ambiguous_total_difference_as_per_100g": 0}
                group_stats = category_groups_stats[group]
                if label_basis_metrics["recipe_share"]["number_of_values"] > 0:
                    group_stats["recipe_share_number_of_products"] += 1
                    group_stats["recipe_share_total_difference"] += label_basis_metrics["recipe_share"]["total_difference"]
                if label_basis_metrics["ambiguous"]["number_of_values"] > 0:
                    group_stats["ambiguous_number_of_products"] += 1
                    group_stats["ambiguous_total_difference"] += label_basis_metrics["ambiguous"]["total_difference"]
                    group_stats["ambiguous_total_difference_as_per_100g"] += label_basis_metrics["ambiguous"]["total_difference_as_per_100g"]

            # Products with only specified quantities (and no specified percent) are not counted in the percent metrics
            if resulting_product["ingredients_metrics"]["number_of_specified_ingredients"] == 0:
                continue

            # Aggregate metrics by test set
            test_set_total_difference += resulting_product["ingredients_metrics"]["total_difference"]
            test_set_total_variance += resulting_product["ingredients_metrics"]["total_variance"]
            test_set_number_of_products += 1
            test_set_total_quantity_difference += resulting_product["ingredients_metrics"]["total_quantity_difference"]
            if "difference_per_specified_ingredient" in resulting_product["ingredients_metrics"]:
                test_set_total_difference_per_specified_ingredient += resulting_product["ingredients_metrics"]["difference_per_specified_ingredient"]
                test_set_number_of_products_with_specified_ingredients += 1

            for group in get_category_groups(input_product.get("categories_tags")):
                group_stats = category_groups_stats[group]
                group_stats["number_of_products"] += 1
                group_stats["total_difference"] += resulting_product["ingredients_metrics"]["total_difference"]
                group_stats["total_difference_per_specified_ingredient"] += resulting_product["ingredients_metrics"].get("difference_per_specified_ingredient", 0)
                group_stats["total_quantity_difference"] += resulting_product["ingredients_metrics"]["total_quantity_difference"]

            # Also compute metrics that consider only products which have ciqual food codes or proxy food codes for all ingredients
            # This is useful to see how well the model performs when all ingredients are known
            if resulting_product["ingredients_metrics"]["number_of_ingredients_without_ciqual_code"] == 0:
                all_ciqual_test_set_total_difference += resulting_product["ingredients_metrics"]["total_difference"]
                all_ciqual_test_set_total_variance += resulting_product["ingredients_metrics"]["total_variance"]
                all_ciqual_test_set_number_of_products += 1


    # Compute average metrics for the test set, if the test set is not empty
    if test_set_number_of_products > 0:
        
        # Save the ingredients stats as a CSV file in the test set directory
        with open(results_path + "/" + test_set_name + "/ingredients_stats.csv", "w", newline="") as ingredients_stats_csv:
            ingredients_stats_csv_writer = csv.writer(ingredients_stats_csv)
            ingredients_stats_csv_writer.writerow(['ingredient','is_in_taxonomy','ciqual_food_code','ciqual_proxy_food_code', 'total_input_percent', 'total_percent_estimate','total_difference','total_variance','relative_difference','number_of_products','number_of_products_where_specified'])
            # sort ingredients by id for easy diffs
            for ingredient_id in sorted(ingredients_stats.keys()):
                ingredient_stats = ingredients_stats[ingredient_id]
                # If we have some specified input percent, compute the relative difference
                if (ingredient_stats["total_input_percent"] > 0):
                     ingredient_stats["relative_difference"] = round_to_n(ingredient_stats["total_difference"] / ingredient_stats["total_input_percent"],3)
                ingredients_stats_csv_writer.writerow([ingredient_id, 
                                                       ingredient_stats["is_in_taxonomy"],
                                                       ingredient_stats["ciqual_food_code"],
                                                       ingredient_stats["ciqual_proxy_food_code"],
                                                       round_to_n(ingredient_stats["total_input_percent"], 3),
                                                       round_to_n(ingredient_stats["total_percent_estimate"], 3),
                        round_to_n(ingredient_stats["total_difference"], 3),
                        round_to_n(ingredient_stats["total_variance"], 3),
                        ingredient_stats.get("relative_difference", ""),
                          ingredient_stats["number_of_products"], 
                          ingredient_stats["number_of_products_where_specified"]])

        # Compute the % of leaf ingredients that have a ciqual_food_code, a ciqual_proxy_food_code, or one or the other
        # weighted by percent_estimate.
        total_percent_estimate = 0
        total_percent_estimate_with_ciqual_food_code = 0
        total_percent_estimate_with_ciqual_proxy_food_code = 0
        total_percent_estimate_with_ciqual_or_ciqual_proxy_food_code = 0

        for ingredient_id in ingredients_stats.keys():
            ingredient_stats = ingredients_stats[ingredient_id]
            total_percent_estimate += ingredient_stats["total_percent_estimate"]
            if ingredient_stats["ciqual_food_code"] is not None:
                total_percent_estimate_with_ciqual_food_code += ingredient_stats["total_percent_estimate"]
            if ingredient_stats["ciqual_proxy_food_code"] is not None:
                total_percent_estimate_with_ciqual_proxy_food_code += ingredient_stats["total_percent_estimate"]
            if ingredient_stats["ciqual_food_code"] is not None or ingredient_stats["ciqual_proxy_food_code"] is not None:
                total_percent_estimate_with_ciqual_or_ciqual_proxy_food_code += ingredient_stats["total_percent_estimate"]
                
        percent_estimate_with_ciqual_food_code = round_to_n(100 * total_percent_estimate_with_ciqual_food_code / total_percent_estimate, 3)
        percent_estimate_with_ciqual_proxy_food_code = round_to_n(100 * total_percent_estimate_with_ciqual_proxy_food_code / total_percent_estimate, 3)
        percent_estimate_with_ciqual_or_ciqual_proxy_food_code = round_to_n(100 * total_percent_estimate_with_ciqual_or_ciqual_proxy_food_code / total_percent_estimate, 3)

        # Save a summary of the results in the test set directory        
        test_set_average_difference = test_set_total_difference / test_set_number_of_products
        test_set_average_variance = test_set_total_variance / test_set_number_of_products
        test_set_average_quantity_difference = test_set_total_quantity_difference / test_set_number_of_products
        test_set_average_difference_per_specified_ingredient = 0
        if test_set_number_of_products_with_specified_ingredients > 0:
            test_set_average_difference_per_specified_ingredient = test_set_total_difference_per_specified_ingredient / test_set_number_of_products_with_specified_ingredients

        average_specified_quantity_difference = 0
        if test_set_number_of_specified_quantities > 0:
            average_specified_quantity_difference = test_set_total_specified_quantity_difference / test_set_number_of_specified_quantities

        label_basis_summary = {}
        for basis, basis_stats in label_basis_stats.items():
            if basis == "unknown_relative":
                label_basis_summary[basis] = basis_stats
                continue
            label_basis_summary[basis] = {
                "number_of_products": basis_stats["number_of_products"],
                "number_of_values": basis_stats["number_of_values"],
                "average_difference": average(basis_stats["total_difference"], basis_stats["number_of_products"]),
                "average_difference_per_value": average(basis_stats["total_difference"], basis_stats["number_of_values"]),
            }
        label_basis_summary["ambiguous"]["average_difference_as_per_100g"] = average(label_basis_stats["ambiguous"]["total_difference_as_per_100g"], label_basis_stats["ambiguous"]["number_of_products"])
        label_basis_summary["ambiguous"]["average_difference_per_value_as_per_100g"] = average(label_basis_stats["ambiguous"]["total_difference_as_per_100g"], label_basis_stats["ambiguous"]["number_of_values"])

        category_groups_summary = {}
        for group in sorted(category_groups_stats):
            group_stats = category_groups_stats[group]
            category_groups_summary[group] = {
                "number_of_products": group_stats["number_of_products"],
                "average_difference": average(group_stats["total_difference"], group_stats["number_of_products"]),
                "average_difference_per_specified_ingredient": average(group_stats["total_difference_per_specified_ingredient"], group_stats["number_of_products"]),
                "average_quantity_difference": average(group_stats["total_quantity_difference"], group_stats["number_of_products"]),
                "recipe_share_number_of_products": group_stats["recipe_share_number_of_products"],
                "recipe_share_average_difference": average(group_stats["recipe_share_total_difference"], group_stats["recipe_share_number_of_products"]),
                "ambiguous_number_of_products": group_stats["ambiguous_number_of_products"],
                "ambiguous_average_difference_as_recipe_share": average(group_stats["ambiguous_total_difference"], group_stats["ambiguous_number_of_products"]),
                "ambiguous_average_difference_as_per_100g": average(group_stats["ambiguous_total_difference_as_per_100g"], group_stats["ambiguous_number_of_products"]),
            }
        try:
            all_ciqual_test_set_average_difference = all_ciqual_test_set_total_difference / all_ciqual_test_set_number_of_products
            all_ciqual_test_set_average_variance = all_ciqual_test_set_total_variance / all_ciqual_test_set_number_of_products
        except: 
            all_ciqual_test_set_average_difference = 0
            all_ciqual_test_set_average_variance = 0

        results_summary = {
            "test_set_name": test_set_name,
            "total_difference": round_to_n(test_set_total_difference,8),
            "total_variance": round_to_n(test_set_total_variance,8),
            "number_of_products": test_set_number_of_products,
            "skipped_products": skipped_products,
            "skipped_products_problems": skipped_products_problems,
            "average_difference_per_specified_ingredient": round_to_n(test_set_average_difference_per_specified_ingredient,4),
            "average_quantity_difference": round_to_n(test_set_average_quantity_difference,4),
            "category_groups": category_groups_summary,
            # Main metric: average difference for specified percents that are recipe shares (see label_basis.py)
            "average_recipe_share_difference": label_basis_summary["recipe_share"]["average_difference"],
            "label_basis": label_basis_summary,
            "number_of_products_with_specified_quantities": test_set_number_of_products_with_specified_quantities,
            "number_of_specified_quantities": test_set_number_of_specified_quantities,
            "number_of_unmatched_specified_quantities": test_set_number_of_unmatched_specified_quantities,
            "number_of_specified_quantities_with_specified_percent": test_set_number_of_specified_quantities_with_specified_percent,
            "average_specified_quantity_difference": round_to_n(average_specified_quantity_difference,4),
            "average_difference": round_to_n(test_set_average_difference,4),
            "average_variance": round_to_n(test_set_average_variance,4),
            "all_ciqual_test_set_total_difference": round_to_n(all_ciqual_test_set_total_difference,8),
            "all_ciqual_test_set_total_variance": round_to_n(all_ciqual_test_set_total_variance,8),
            "all_ciqual_test_set_number_of_products": all_ciqual_test_set_number_of_products,
            "all_ciqual_test_set_average_difference": round_to_n(all_ciqual_test_set_average_difference,4),
            "percent_estimate_with_ciqual_food_code": percent_estimate_with_ciqual_food_code,
            "percent_estimate_with_ciqual_proxy_food_code": percent_estimate_with_ciqual_proxy_food_code,
            "percent_estimate_with_ciqual_or_ciqual_proxy_food_code": percent_estimate_with_ciqual_or_ciqual_proxy_food_code
        }

        # Save the results summary in the test set directory
        with open(results_path + "/" + test_set_name + "/results_summary.json", "w") as f:
            print("Saving results summary in test set directory: " + test_name)
            json.dump(results_summary, f,  indent=4, ensure_ascii=False, sort_keys=True)                

        # Print the results summary
        print("Results summary for test set " + test_set_name + ":")
        print("Total difference: " + str(round_to_n(test_set_total_difference,8)))
        print("Total variance: " + str(round_to_n(test_set_total_variance,8)))
        print("Number of products: " + str(test_set_number_of_products))
        print("Skipped products: " + str(skipped_products))
        print("Average difference: " + str(round_to_n(test_set_average_difference,4)))
        print("Average variance: " + str(round_to_n(test_set_average_variance,4)))
        print("Average difference per specified ingredient: " + str(round_to_n(test_set_average_difference_per_specified_ingredient,4)))
        print("Average quantity difference: " + str(round_to_n(test_set_average_quantity_difference,4)))
        print("Specified quantities (for 100g of product): " + str(test_set_number_of_specified_quantities) + " in " + str(test_set_number_of_products_with_specified_quantities) + " products, "
              + str(test_set_number_of_unmatched_specified_quantities) + " not matched to ingredients, "
              + str(test_set_number_of_specified_quantities_with_specified_percent) + " with a specified percent for the same ingredient")
        print("Average specified quantity difference: " + str(round_to_n(average_specified_quantity_difference,4)))
        print("All ciqual test set total difference: " + str(round_to_n(all_ciqual_test_set_total_difference,8)))
        print("All ciqual test set total variance: " + str(round_to_n(all_ciqual_test_set_total_variance,8)))
        print("All ciqual test set number of products: " + str(all_ciqual_test_set_number_of_products))
        print("All ciqual test set average difference: " + str(round_to_n(all_ciqual_test_set_average_difference,4)))
        print("All ciqual test set average variance: " + str(round_to_n(all_ciqual_test_set_average_variance,4)))
        print("Percent estimate with ciqual_food_code: " + str(percent_estimate_with_ciqual_food_code))
        print("Percent estimate with ciqual_proxy_food_code: " + str(percent_estimate_with_ciqual_proxy_food_code))
        print("Percent estimate with ciqual or ciqual_proxy_food_code: " + str(percent_estimate_with_ciqual_or_ciqual_proxy_food_code))
        print("Average recipe share difference (main metric, " + str(label_basis_summary["recipe_share"]["number_of_products"]) + " products): " + str(label_basis_summary["recipe_share"]["average_difference"]))
        print("Per 100 g of finished product (" + str(label_basis_summary["per_100g"]["number_of_products"]) + " products): " + str(label_basis_summary["per_100g"]["average_difference"]))
        print("Ambiguous, products that lose moisture (" + str(label_basis_summary["ambiguous"]["number_of_products"]) + " products): " + str(label_basis_summary["ambiguous"]["average_difference"]) + " as recipe share, "
              + str(label_basis_summary["ambiguous"]["average_difference_as_per_100g"]) + " as per 100 g")
        print("Category groups (number of products, average difference, average difference per specified ingredient):")
        for group, group_summary in category_groups_summary.items():
            print(f"  {group}: {group_summary['number_of_products']}, {group_summary['average_difference']}, {group_summary['average_difference_per_specified_ingredient']}")


