#!/usr/bin/python3
"""
add_percent_estimate_to_inputs.py [path to model executable] [paths of one or more input test sets]

The model executable must:
- accept a product JSON body as input in STDIN
- estimate ingredients percentages and store the result in the "percent_estimate" field of ingredients in the "ingredients" structure
- write the resulting product JSON to STDOUT

This script will go through each product JSON file of the specified input test sets to:
- Run the specified model on the product
- Calculate the percentage of ingredients that don't have a CIQUAL match
- Save the resulting products back to the [input test set name]

Example:

./scripts/add_percent_estimate_to_inputs.py product_opener_localhost fr-les-mousquetaires-all-specified

"""

import json
import sys
import os
import subprocess

import time

from compute_metrics import compute_metrics_for_test_set

# Calculate the percentage of ingredients with CIQUAL / proxy codes
def calculate_ciqual_percentages(ingredients):
    ciqual_total = 0
    ciqual_or_proxy_total = 0
    no_ciqual_count = 0
    for ingredient in ingredients:
        if "ingredients" in ingredient:
            (child_ciqual, child_proxy, child_count) = calculate_ciqual_percentages(ingredient["ingredients"])
            ciqual_total += child_ciqual
            ciqual_or_proxy_total += child_proxy
            no_ciqual_count += child_count
        else:
            percent_estimate = ingredient.get("percent_estimate", 0)
            if "ciqual_food_code" in ingredient:
                ciqual_total += percent_estimate
                ciqual_or_proxy_total += percent_estimate
            elif "ciqual_proxy_food_code" in ingredient:
                ciqual_or_proxy_total += percent_estimate
            else:
                no_ciqual_count += 1

    return (ciqual_total, ciqual_or_proxy_total, no_ciqual_count)

# Check input parameters (existing model executable, input test set), otherwise print usage
if len(sys.argv) < 2:
    print("add_percent_estimate_to_inputs.py [path to model executable] [paths of one or more input test sets]")
    sys.exit(1)

# If we were passed a model name (no path), assume it is in the models directory, and if there is no extension, assume it is a .py file
if "/" not in sys.argv[1]:
    if "." not in sys.argv[1]:
        sys.argv[1] += ".py"
    sys.argv[1] = "models/" + sys.argv[1]

model = sys.argv[1]

command = model.split(";")
for element in command:
    if not os.path.exists(element):
        print(f"{element} does not exist")
        sys.exit(1)

start_time = time.time()

# Go through each input test set directory
test_sets = sys.argv[2:] if len(sys.argv) > 2 else os.listdir('test-sets/input')
for test_set_name in test_sets:
    # If we have a test set path instead of a test set name, use the last component of the path as the test set name
    if "test-sets/input/" in test_set_name:
        test_set_name = test_set_name.split("test-sets/input/")[-1]

    print("Calculating estimates on test set " + test_set_name)

    # Test set name is the last component of the test set path, remove trailing / if any
    test_set_path = 'test-sets/input/' + test_set_name 

    # Go through each JSON file in the input test set directory
    for path in [test_set_path + "/" + f for f in os.listdir(test_set_path) if f.endswith(".json")]:

        # test name is the last component of the path
        test_name = path.split("/")[-1]

        with open(path, "r") as f:
            input_product = json.load(f)

        # Check if the product has an ingredients structure
        if "ingredients" not in input_product:
            print("Skipping product without ingredients: " + path)
            continue
        
        print("Running model on product " + path)

        # Define the command to be executed
        command = model.split(";")
        #print(command)

        # Create a Popen object
        p = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

        # Pass the input to the command
        stdout, stderr = p.communicate(input=json.dumps(input_product))

        # Handle errors if any
        if stderr:
            print(stderr.strip(), file=sys.stderr)

        # Get the output
        result_json = stdout.strip()

        try:
            result = json.loads(result_json)
            
            # Calculate the percentage of ingredients with CIQUAL codes
            (ciqual_total, ciqual_or_proxy_total, no_ciqual_count) = calculate_ciqual_percentages(result["ingredients"])
            result["percent_ingredients_with_ciqual_code"] = round(ciqual_total, 2)
            result["percent_ingredients_with_ciqual_or_proxy_code"] = round(ciqual_or_proxy_total, 2)
            if "ingredients_without_ciqual_codes_n" not in result:
                result["ingredients_without_ciqual_codes_n"] = no_ciqual_count

            print("Saving output to " + path)
            with open(path, "w") as f:
                json.dump(result, f,  indent=4, ensure_ascii=False, sort_keys=True)
        except Exception as e:
            #print(result_json, file=sys.stderr)
            print("An issue occurred: " + str(e), file=sys.stderr)

        elapsed_time = time.time() - start_time
        print(f"\n -- Test set {test_set_name} completed in {elapsed_time:.2f} seconds. -- \n")

    elapsed_time = time.time() - start_time
    print(f"\n -- Calculating estimates completed in {elapsed_time:.2f} seconds. -- \n")
