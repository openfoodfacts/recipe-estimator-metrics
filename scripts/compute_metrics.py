#!/usr/bin/python3
"""
compute_metrics_for_model_on_test_sets [path of model results] [paths of one or more input test sets]

This scriptwill go through each product JSON file of the specified input test sets to:
- Compute accuracy metrics comparing the estimated "percent_estimate" field in the resulting product
to the "percent" field in the input product
- Store product level metrics in the resulting product
- Aggregate metrics by test set

Example:

./scripts/compute_metrics_for_model_on_test_sets.py test-sets/results/product_opener/ test-sets/input/fr-les-mousquetaires-all-specified
"""

import json
import os
import csv
import math

round_to_n = lambda x, n: x if x == 0 else round(x, -int(math.floor(math.log10(abs(x)))) + (n - 1))

def compare_input_ingredients_to_resulting_ingredients(input_ingredients, resulting_ingredients, ingredients_stats, details_csv_writer, test_name):
    # Compute difference metrics for each ingredient and nested sub ingredient comparing the input percent to the resulting percent_estimate

    total_difference = 0
    total_specified_input_percent = 0

    for i, input_ingredient in enumerate(input_ingredients):
        resulting_ingredient = resulting_ingredients[i]
        # We compute metrics for known percent in the input product
        if "percent" in input_ingredient:
            input_ingredient_id = input_ingredient['id']
            input_percent = input_ingredient["percent"]
            total_specified_input_percent += input_percent
            # If the resulting ingredient does not have a percent_estimate, we set it to 0 for metrics computation
            if "percent_estimate" in resulting_ingredient:
                resulting_percent_estimate = resulting_ingredient["percent_estimate"]
                # Round the computed percent to 3 significant figures so diffs aren't excessive
                rounded_resulting_percent_estimate = round_to_n(resulting_percent_estimate, 3)
                resulting_ingredient['percent_estimate'] = rounded_resulting_percent_estimate
            else:
                resulting_percent_estimate = 0
                rounded_resulting_percent_estimate = 0
                
            difference = abs(resulting_percent_estimate - input_percent)
            rounded_difference = round_to_n(difference, 3)
            # Store the difference at the ingredient level. 
            resulting_ingredient["difference"] = rounded_difference
            total_difference += difference
            # Write to summary CSV file.
            details_csv_writer.writerow([test_name, input_ingredient['id'], input_percent, rounded_resulting_percent_estimate, rounded_difference])
            # Aggregate stats for the ingredient
            if input_ingredient_id not in ingredients_stats:
                ingredients_stats[input_ingredient_id] = {
                    "total_input_percent": 0,
                    "total_percent_estimate": 0,
                    "total_difference": 0,
                    "number_of_products": 0,
                    "ciqual_food_code": input_ingredient.get("ciqual_food_code"),
                    "ciqual_proxy_food_code": input_ingredient.get("ciqual_proxy_food_code")
                }
            ingredients_stats[input_ingredient_id]["total_input_percent"] += input_percent
            ingredients_stats[input_ingredient_id]["total_percent_estimate"] += resulting_percent_estimate
            ingredients_stats[input_ingredient_id]["total_difference"] += difference
            ingredients_stats[input_ingredient_id]["number_of_products"] += 1
        
        # Compare sub ingredients if any
        if "ingredients" in input_ingredients:
            input_sub_ingredients = input_ingredient["ingredients"]
            resulting_sub_ingredients = resulting_ingredient["ingredients"]
            (total_specified_input_percent, total_difference) = [x + y for x, y in zip(
                [total_specified_input_percent, total_difference],
                compare_input_ingredients_to_resulting_ingredients(input_sub_ingredients, resulting_sub_ingredients, details_csv_writer, test_name))]

    return (total_specified_input_percent, total_difference)

def compare_input_product_to_resulting_product(input_product, resulting_product, ingredients_stats, details_csv_writer, test_name):
    
    if not isinstance(input_product, dict) or not isinstance(resulting_product, dict):
        raise ValueError("Input product and resulting product must be dictionaries")
        
    (total_specified_input_percent, total_difference) = compare_input_ingredients_to_resulting_ingredients(input_product["ingredients"], resulting_product["ingredients"], ingredients_stats, details_csv_writer, test_name)

    resulting_product["ingredients_metrics"] = {
        "total_specified_input_percent": round_to_n(total_specified_input_percent,3),
        "total_difference": round_to_n(total_difference,3)
    }
    # If we have some specified input percent, compute the relative difference
    if (total_specified_input_percent > 0):
        resulting_product["ingredients_metrics"]["relative_difference"] = round_to_n(total_difference / total_specified_input_percent,3)

    pass

def compute_metrics_for_test_set(results_path, test_set_name):
    # Compute average metrics for the test set
    test_set_total_difference = 0
    test_set_number_of_products = 0

    # Compute aggregated stats (number of products and total difference) for each ingredient
    ingredients_stats = {}


    result_set_path = results_path + "/" + test_set_name
    with open(result_set_path + "/results_details.csv", "w", newline="") as details_csv:
        details_csv_writer = csv.writer(details_csv)
        details_csv_writer.writerow(['test_name','ingredient','percent','percent_estimate','difference'])

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
            with open(result_path, "r") as f:
                resulting_product = json.load(f)

            # Compute accuracy metrics comparing the estimated "percent_estimate" field in the resulting product
            # to the "percent" field in the input product
            print("Computing metrics for " + result_path)
            compare_input_product_to_resulting_product(input_product, resulting_product, ingredients_stats, details_csv_writer, test_name)

            # Store product level metrics in the resulting product
            with open(result_path, "w") as f:
                print("Saving metrics in result: " + result_path)
                json.dump(resulting_product, f,  indent=4, ensure_ascii=False, sort_keys=True)

            # Aggregate metrics by test set
            test_set_total_difference += resulting_product["ingredients_metrics"]["total_difference"]
            test_set_number_of_products += 1

    # Compute average metrics for the test set, if the test set is not empty
    if test_set_number_of_products > 0:
        test_set_average_difference = test_set_total_difference / test_set_number_of_products

        results_summary = {
            "test_set_name": test_set_name,
            "total_difference": round_to_n(test_set_total_difference,3),
            "number_of_products": test_set_number_of_products,
            "average_difference": round_to_n(test_set_average_difference,3)
        }

        # Save the results summary in the test set directory
        with open(results_path + "/" + test_set_name + "/results_summary.json", "w") as f:
            print("Saving results summary in test set directory: " + test_name)
            json.dump(results_summary, f,  indent=4, ensure_ascii=False, sort_keys=True)

        # Save the ingredients stats as a CSV file in the test set directory
        with open(results_path + "/" + test_set_name + "/ingredients_stats.csv", "w", newline="") as ingredients_stats_csv:
            ingredients_stats_csv_writer = csv.writer(ingredients_stats_csv)
            ingredients_stats_csv_writer.writerow(['ingredient','ciqual_food_code','ciqual_proxy_food_code','total_input_percent','total_percent_estimate','total_difference','number_of_products'])
            for ingredient_id in ingredients_stats:
                ingredient_stats = ingredients_stats[ingredient_id]
                ingredients_stats_csv_writer.writerow([ingredient_id, ingredient_stats["ciqual_food_code"],
                                                       ingredient_stats["ciqual_proxy_food_code"],
                                                       round_to_n(ingredient_stats["total_input_percent"], 3),
                                                       round_to_n(ingredient_stats["total_percent_estimate"], 3),
                        round_to_n(ingredient_stats["total_difference"], 3), ingredient_stats["number_of_products"]])

        print("Test set " + test_set_name)
        print("number of products: " +  str(test_set_number_of_products))
        print("total difference:" + str(test_set_total_difference))
        print("average difference: " + str(test_set_average_difference))

