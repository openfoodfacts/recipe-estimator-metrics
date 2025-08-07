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

round_to_n = lambda x, n: x if x == 0 else round(x, -int(math.floor(math.log10(abs(x)))) + (n - 1))

def add_missing_estimates_for_parent_ingredients(ingredients):
    # Add missing percent_estimate to parent ingredients by summing the percent_estimate of their children
    for ingredient in ingredients:
        if "ingredients" in ingredient:
            add_missing_estimates_for_parent_ingredients(ingredient["ingredients"])
            if "percent_estimate" not in ingredient:
                ingredient["percent_estimate"] = sum([sub_ingredient["percent_estimate"] for sub_ingredient in ingredient["ingredients"]])

def compare_input_ingredients_to_resulting_ingredients(input_ingredients, resulting_ingredients, ingredients_stats, products_ingredients_csv_writer, test_name):
    # Compute difference metrics for each ingredient and nested sub ingredient comparing the input percent to the resulting percent_estimate

    total_difference = 0
    total_specified_input_percent = 0
    number_of_ingredients_without_ciqual_code = 0

    # add missing percent_estimate to parent ingredients by summing the percent_estimate of their children
    add_missing_estimates_for_parent_ingredients(resulting_ingredients)

    for i, input_ingredient in enumerate(input_ingredients):
        resulting_ingredient = resulting_ingredients[i]

        input_ingredient_id = input_ingredient['id']
        input_percent = 0
        input_percent_is_specified = False
        rounded_resulting_percent_estimate = 0
        resulting_quantity_estimate = 0
        difference = 0

        # If the resulting ingredient does not have a percent_estimate, we set it to 0 for metrics computation
        if "percent_estimate" in resulting_ingredient:
            # Round the computed percent to 3 significant figures so diffs aren't excessive
            rounded_resulting_percent_estimate = round_to_n(resulting_ingredient["percent_estimate"], 3)
            resulting_ingredient['percent_estimate'] = rounded_resulting_percent_estimate        

        if "quantity_estimate" in resulting_ingredient:
            # Round the computed percent to 3 significant figures so diffs aren't excessive
            resulting_quantity_estimate = round_to_n(resulting_ingredient["quantity_estimate"], 3)
            resulting_ingredient['quantity_estimate'] = resulting_quantity_estimate

        # We compute metrics for known percent in the input product
        if "percent" in input_ingredient:
            input_percent = input_ingredient["percent"]
            input_percent_is_specified = True
            total_specified_input_percent += input_percent

            # Use rounded estimate here so results don't change if metrics are recalculated
            difference = abs(rounded_resulting_percent_estimate - input_percent)
            rounded_difference = round_to_n(difference, 3)
            # Store the difference at the ingredient level. 
            resulting_ingredient["difference"] = rounded_difference
            total_difference += difference
            # Write to summary CSV file.
            products_ingredients_csv_writer.writerow([test_name, input_ingredient['id'], input_percent, rounded_resulting_percent_estimate, rounded_difference])
        
        # Compare sub ingredients if any
        if "ingredients" in input_ingredient and len(input_ingredient["ingredients"]) > 0:
            input_sub_ingredients = input_ingredient["ingredients"]
            # check that we also have sub ingredients in the resulting ingredient
            if "ingredients" not in resulting_ingredient:
                print(f"Error: missing sub ingredients in resulting ingredient for {input_ingredient['id']}")
                # seems to happen with PEFAP. The metrics comparison is not valid in this case.
                #continue
            resulting_sub_ingredients = resulting_ingredient["ingredients"]
            (total_specified_input_percent, total_difference, number_of_ingredients_without_ciqual_code) = [x + y for x, y in zip(
                [total_specified_input_percent, total_difference, number_of_ingredients_without_ciqual_code],
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
                    "number_of_products": 0,
                    "number_of_products_where_specified": 0,
                    'is_in_taxonomy': input_ingredient.get('is_in_taxonomy'),
                    "ciqual_food_code": ciqual_food_code,
                    "ciqual_proxy_food_code": ciqual_proxy_food_code
                }
                
            ingredients_stats[input_ingredient_id]["total_percent_estimate"] += rounded_resulting_percent_estimate
            ingredients_stats[input_ingredient_id]["total_difference"] += difference
            ingredients_stats[input_ingredient_id]["number_of_products"] += 1
            if input_percent_is_specified:
                ingredients_stats[input_ingredient_id]["number_of_products_where_specified"] += 1
                ingredients_stats[input_ingredient_id]["total_input_percent"] += input_percent

    return (total_specified_input_percent, total_difference, number_of_ingredients_without_ciqual_code)

def compare_input_product_to_resulting_product(input_product, resulting_product, ingredients_stats, products_ingredients_csv_writer, test_name):
    
    if not isinstance(input_product, dict) or not isinstance(resulting_product, dict):
        raise ValueError("Input product and resulting product must be dictionaries")
    
    if "ingredients" not in input_product:
        raise ValueError("Input product must have an 'ingredients' field")
    
    if "ingredients" not in resulting_product:
        raise ValueError("Resulting product must have an 'ingredients' field")
        
    (total_specified_input_percent, total_difference, number_of_ingredients_without_ciqual_code) = compare_input_ingredients_to_resulting_ingredients(input_product["ingredients"], resulting_product["ingredients"], ingredients_stats, products_ingredients_csv_writer, test_name)

    resulting_product["ingredients_metrics"] = {
        "total_specified_input_percent": round_to_n(total_specified_input_percent,3),
        "total_difference": round_to_n(total_difference,3),
        "number_of_ingredients_without_ciqual_code": number_of_ingredients_without_ciqual_code,
    }
    # If we have some specified input percent, compute the relative difference
    if (total_specified_input_percent > 0):
        resulting_product["ingredients_metrics"]["relative_difference"] = round_to_n(total_difference / total_specified_input_percent,3)

    pass

def compute_metrics_for_test_set(results_path, test_set_name):
    # Compute average metrics for the test set
    test_set_total_difference = 0
    test_set_number_of_products = 0
    # and for products that have ciqual food codes or proxy food codes for all ingredients
    all_ciqual_test_set_total_difference = 0
    all_ciqual_test_set_number_of_products = 0

    # Compute aggregated stats (number of products and total difference) for each ingredient
    ingredients_stats = {}

    # Store the details of the metrics at the product + ingredient level, and at the product level
    result_set_path = results_path + "/" + test_set_name
    with open(result_set_path + "/products_stats.csv", "w", newline="") as products_csv, \
         open(result_set_path + "/products_ingredients_stats.csv", "w", newline="") as products_ingredients_csv:
        products_csv_writer = csv.writer(products_csv)
        products_csv_writer.writerow(['test_name', 'total_difference','number_of_ingredients_without_ciqual_code','ingredients_text'])
        products_ingredients_csv_writer = csv.writer(products_ingredients_csv)
        products_ingredients_csv_writer.writerow(['test_name','ingredient','percent','percent_estimate','difference'])

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
            with open(result_path, "r") as f:
                resulting_product = json.load(f)

            # Compute accuracy metrics comparing the estimated "percent_estimate" field in the resulting product
            # to the "percent" field in the input product
            compare_input_product_to_resulting_product(input_product, resulting_product, ingredients_stats, products_ingredients_csv_writer, test_name)

            # Remove fields that change between runs
            if "recipe_estimator" in resulting_product:
                if "time" in resulting_product["recipe_estimator"]:
                    del resulting_product["recipe_estimator"]["time"]

            # Store product level metrics in the resulting product
            with open(result_path, "w") as f:
                print("Saving metrics in result: " + result_path)
                json.dump(resulting_product, f,  indent=4, ensure_ascii=False, sort_keys=True)

            # Write to the products summary CSV file
            products_csv_writer.writerow([test_name, resulting_product["ingredients_metrics"]["total_difference"],
                                          resulting_product["ingredients_metrics"]["number_of_ingredients_without_ciqual_code"],
                                           resulting_product["ingredients_text"]])

            # Aggregate metrics by test set
            test_set_total_difference += resulting_product["ingredients_metrics"]["total_difference"]
            test_set_number_of_products += 1

            # Also compute metrics that consider only products which have ciqual food codes or proxy food codes for all ingredients
            # This is useful to see how well the model performs when all ingredients are known
            if resulting_product["ingredients_metrics"]["number_of_ingredients_without_ciqual_code"] == 0:
                all_ciqual_test_set_total_difference += resulting_product["ingredients_metrics"]["total_difference"]
                all_ciqual_test_set_number_of_products += 1


    # Compute average metrics for the test set, if the test set is not empty
    if test_set_number_of_products > 0:
        
        # Save the ingredients stats as a CSV file in the test set directory
        with open(results_path + "/" + test_set_name + "/ingredients_stats.csv", "w", newline="") as ingredients_stats_csv:
            ingredients_stats_csv_writer = csv.writer(ingredients_stats_csv)
            ingredients_stats_csv_writer.writerow(['ingredient','is_in_taxonomy','ciqual_food_code','ciqual_proxy_food_code', 'total_input_percent', 'total_percent_estimate','total_difference','relative_difference','number_of_products','number_of_products_where_specified'])
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
        try:
            all_ciqual_test_set_average_difference = all_ciqual_test_set_total_difference / all_ciqual_test_set_number_of_products
        except: 
            all_ciqual_test_set_average_difference = 0

        results_summary = {
            "test_set_name": test_set_name,
            "total_difference": round_to_n(test_set_total_difference,8),
            "number_of_products": test_set_number_of_products,
            "average_difference": round_to_n(test_set_average_difference,4),
            "all_ciqual_test_set_total_difference": round_to_n(all_ciqual_test_set_total_difference,8),
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
        print("Number of products: " + str(test_set_number_of_products))
        print("Average difference: " + str(round_to_n(test_set_average_difference,4)))
        print("All ciqual test set total difference: " + str(round_to_n(all_ciqual_test_set_total_difference,8)))
        print("All ciqual test set number of products: " + str(all_ciqual_test_set_number_of_products))
        print("All ciqual test set average difference: " + str(round_to_n(all_ciqual_test_set_average_difference,4)))
        print("Percent estimate with ciqual_food_code: " + str(percent_estimate_with_ciqual_food_code))
        print("Percent estimate with ciqual_proxy_food_code: " + str(percent_estimate_with_ciqual_proxy_food_code))
        print("Percent estimate with ciqual or ciqual_proxy_food_code: " + str(percent_estimate_with_ciqual_or_ciqual_proxy_food_code))


