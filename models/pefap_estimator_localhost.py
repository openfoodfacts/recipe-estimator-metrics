#!/usr/bin/python3
"""
*.py < input JSON product > output JSON product

This code uses the PEFAP Estimator to estimate the ingredients percent of a product
"""

import os
import sys
import json
import sys

pefap_package_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../PEFAP_estimator"))

print(pefap_package_dir)

# Local configuration
if os.path.isdir(pefap_package_dir):
    sys.path.insert(0, pefap_package_dir)

    print(pefap_package_dir)
    try: 
        # Local configuration
        from impacts_estimation import estimate_impacts
        
        path = "../test-sets/input/fr-62-products-10-specified-ingredients/20298036.json"
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), path))
        
        with open(file_path, 'r') as f:
            product = json.load(f)
            
        # Calling the PEFAP algorithm
        impact_categories = ['EF single score', 'Climate change']
        print("Estimating recipe")
        impact_estimation_result = estimate_impacts(product=product, impact_names=impact_categories)
        
        #print(impact_estimation_result['ingredients_mass_share'])

    except Exception as e:
        print("An error occured..") 
        raise
# Online configuration
else :
    # Checking that we have an input product in JSON format in STDIN
    try:
        product = json.load(sys.stdin)
    except ValueError:
        print("Input product is not in JSON format", file=sys.stderr)
    
    # Calling the PEFAP algorithm
    impact_estimation_result = estimate_impacts(product=product, impact_names=impact_categories)
    
    # 
    try:
        response_json = impact_estimation_result['ingredients_mass_share']

        # Merging results with json
        
        print(response_json, file=sys.stderr)
    except:
        print(impact_estimation_result, file=sys.stderr)

