#!/usr/bin/python3
# Iterate over results folder to get model names
# Iterate over each input and then add a result column for each model

import csv
import json
import os

results_path = 'test-sets/results/'
test_sets_path = 'test-sets/input/'

def count_ingredients(ingredients):
    count = 0
    for ingredient in ingredients:
        sub_ingredients = ingredient.get('ingredients', [])
        if len(sub_ingredients) > 0:
            count += count_ingredients(sub_ingredients)
        else:
            count += 1
    return count

        
with open(results_path + "products_stats.csv", "w", newline="") as products_csv:
    with open(results_path + "model_stats.csv", "w", newline="") as models_csv:
        products_csv_writer = csv.writer(products_csv)
        models_csv_writer = csv.writer(models_csv)

        models = []

        model_names = [f for f in sorted(os.listdir(results_path))if '.' not in f]
        for model_name in model_names:
            models.append(model_name)

        products_csv_writer.writerow(['test_set','product','ingredients_n','without_ciqual_n'] + models)
        models_csv_writer.writerow(['test_set'] + models)

        test_set_names = [f for f in sorted(os.listdir(test_sets_path))if '.' not in f]
        for test_set_name in test_set_names:
            print(test_set_name)
            test_set_path = test_sets_path + "/" + test_set_name + "/"
            test_paths = [test_set_path + f for f in sorted(os.listdir(test_set_path)) if f.endswith(".json")]
            for test_path in test_paths:
                product_name = test_path.split(test_set_path)[-1].split('.json')[0]
                try:
                    with open(test_path, "r") as f:
                        input_product = json.load(f)
                except:
                    continue

                row = [test_set_name, product_name, count_ingredients(input_product['ingredients']),input_product['ingredients_without_ciqual_codes_n']]
                for model_name in models:
                    # Read the corresponding resulting product
                    result_path = results_path + model_name + '/' + test_set_name + '/' + product_name + '.json'
                    try:
                        with open(result_path, "r") as f:
                            resulting_product = json.load(f)
                            row.append(resulting_product["ingredients_metrics"]["total_variance"])
                    except:
                        row.append('NA')

                products_csv_writer.writerow(row)

            summary_row = [test_set_name]
            for model_name in models:
                # Read the corresponding resulting product
                summary_path = results_path + model_name + '/' + test_set_name + '/results_summary.json'
                try:
                    with open(summary_path, "r") as f:
                        results_summary = json.load(f)
                        summary_row.append(results_summary['average_variance'])
                except:
                    summary_row.append('NA')
            models_csv_writer.writerow(summary_row)
                    
                
            
            
        
