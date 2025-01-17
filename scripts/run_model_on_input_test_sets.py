#!/usr/bin/python3
"""
run_model_input_test_sets.py [path to model executable] [path to store results] [paths of one or more input test sets]

The model executable must:
- accept a product JSON body as input in STDIN
- estimate ingredients percentages and store the result in the "percent_estimate" field of ingredients in the "ingredients" structure
- write the resulting product JSON to STDOUT

This script will go through each product JSON file of the specified input test sets to:
- Remove any specified "percent" or "percent_estimate" fields from the input ingredients
- Run the specified model on the product
- Save the resulting products in [path to store results]/[input test set name]/

Example:

./scripts/run_model_on_input_test_sets.py models/product_opener.py test-sets/results/product_opener/ test-sets/input/fr-les-mousquetaires-all-specified

"""

"""
import json
import sys
import os
import subprocess

import time

import concurrent.futures

from compute_metrics import compute_metrics_for_test_set

# Remove percent fields from ingredients, but keep a copy of percent in percent_hidden
def remove_percent_fields(ingredients):
    for ingredient in ingredients:
        # move percent to percent_hidden
        if "percent" in ingredient:
            ingredient["percent_hidden"] = ingredient["percent"]
        # remove percent, percent_min, percent_max, percent_estimate
        fields_to_remove = ["percent", "percent_min", "percent_max", "percent_estimate"]
        for field in fields_to_remove:
            if field in ingredient:
                del ingredient[field]
    return ingredients

# Check input parameters (existing model executable, and specified results path + at least 1 input test set), otherwise print usage
if len(sys.argv) < 3:
    print("Usage: run_model_input_test_sets.py [full path or name of model executable] [full path or name for results] [full paths or names of one or more input test sets]")
    sys.exit(1)

# If we were passed a model name (no path), assume it is in the models directory, and if there is no extension, assume it is a .py file
if "/" not in sys.argv[1]:
    if "." not in sys.argv[1]:
        sys.argv[1] += ".py"
    sys.argv[1] = "models/" + sys.argv[1]

model = sys.argv[1]

# If we were passed a results name (no path), assume it is in the test-sets/results directory
if "/" not in sys.argv[2]:
    sys.argv[2] = "test-sets/results/" + sys.argv[2]


results_path = sys.argv[2]

command = model.split(";")
for element in command:
    if not os.path.exists(element):
        print(f"{element} does not exist")
        sys.exit(1)

start_time = time.time()

# Go through each input test set directory
test_sets = sys.argv[3:] if len(sys.argv) > 3 else os.listdir('test-sets/input')
for test_set_name in test_sets:
    # If we have a test set path instead of a test set name, use the last component of the path as the test set name
    if "test-sets/input/" in test_set_name:
        test_set_name = test_set_name.split("test-sets/input/")[-1]

    print("Running model on test set " + test_set_name)

    # Test set name is the last component of the test set path, remove trailing / if any
    test_set_path = 'test-sets/input/' + test_set_name 

    # Create the results directory if it does not exist
    if not os.path.exists(results_path):
        os.makedirs(results_path)
    # Create the results directory for the test set if it does not exist
    if not os.path.exists(results_path + "/" + test_set_name):
        os.makedirs(results_path + "/" + test_set_name)

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
        
        # Remove any specified "percent" fields from the ingredients
        input_product["ingredients"] = remove_percent_fields(input_product["ingredients"])

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

            # Pretty save the resulting JSON structure over the input file for easy inspection of diffs
            result_path = results_path + "/" + test_set_name + "/" + test_name
            print("Saving output to " + result_path)
            with open(result_path, "w") as f:
                json.dump(result, f,  indent=4, ensure_ascii=False, sort_keys=True)
        except Exception as e:
            #print(result_json, file=sys.stderr)
            print("An issue occurred: " + str(e), file=sys.stderr)

        elapsed_time = time.time() - start_time
        print(f"\n -- Test set {test_set_name} completed in {elapsed_time:.2f} seconds. -- \n")

    compute_metrics_for_test_set(results_path, test_set_name)

    elapsed_time = time.time() - start_time
    print(f"\n -- Compute_metrics_for_test_set completed in {elapsed_time:.2f} seconds. -- \n")


"""











import json
import sys
import os
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor
from compute_metrics import compute_metrics_for_test_set

start_time = time.time()

# Function to remove percent fields from ingredients
def remove_percent_fields(ingredients):
    for ingredient in ingredients:
        if "percent" in ingredient:
            ingredient["percent_hidden"] = ingredient["percent"]
        fields_to_remove = ["percent", "percent_min", "percent_max", "percent_estimate"]
        for field in fields_to_remove:
            if field in ingredient:
                del ingredient[field]
    return ingredients

def process_product(path, model, results_path, test_set_name):
    test_name = path.split("/")[-1]

    with open(path, "r") as f:
        input_product = json.load(f)

    if "ingredients" not in input_product:
        print("Skipping product without ingredients: " + path)
        return

    input_product["ingredients"] = remove_percent_fields(input_product["ingredients"])
    print("Running model on product " + path)

    command = model.split(";")
    p = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    start_product_time = time.time()
    stdout, stderr = p.communicate(input=json.dumps(input_product))
    end_product_time = time.time()
    execution_time = end_product_time - start_product_time

    print(f"\n -- Temps écoulé : {execution_time:.2f} seconds. -- \n")

    if stderr:
        print(stderr.strip(), file=sys.stderr)

    result_json = stdout.strip()
    try:
        result = json.loads(result_json)

        # Add execution time to the result JSON
        result["pefap_execution_time"] = execution_time

        result_path = results_path + "/" + os.path.relpath(test_set_name, start="test-sets/input") + "/" + test_name
        print("✅ Saving output to " + result_path + "\n")
        with open(result_path, "w") as f:
            json.dump(result, f, indent=4, ensure_ascii=False, sort_keys=True)
    except Exception as e:
        print("❌ An issue occurred: " + str(e) + "\n", file=sys.stderr)

def main():
    if len(sys.argv) < 3:
        print("Usage: run_model_input_test_sets.py [full path or name of model executable] [full path or name for results] [full paths or names of one or more input test sets]")
        sys.exit(1)

    model = sys.argv[1]
    results_path = sys.argv[2]
    test_sets = sys.argv[3:] if len(sys.argv) > 3 else os.listdir('test-sets/input')

    for test_set_name in test_sets:
        test_set_path = test_set_name 
        if not os.path.exists(results_path):
            os.makedirs(results_path)
        if not os.path.exists(results_path + "/" + os.path.relpath(test_set_name, start="test-sets/input")):
            os.makedirs(results_path + "/" + os.path.relpath(test_set_name, start="test-sets/input"))

        paths = [test_set_path + "/" + f for f in os.listdir(test_set_path) if f.endswith(".json")]

        with ProcessPoolExecutor() as executor:
            futures = [executor.submit(process_product, path, model, results_path, test_set_name) for path in paths]
            for future in futures:
                future.result()  # This will raise any exception caught during processing

        compute_metrics_for_test_set(results_path, os.path.relpath(test_set_name, start="test-sets/input"))

if __name__ == '__main__':
    main()