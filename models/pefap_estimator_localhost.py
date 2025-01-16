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
#print(pefap_package_dir)

# Local configuration
if os.path.isdir(pefap_package_dir):
    sys.path.insert(0, pefap_package_dir)

    try: 
        # Local configuration
        from impacts_estimation import estimate_impacts
        
        # Check that we have an input product in JSON format in STDIN
        try:
            product = json.load(sys.stdin)
        except ValueError:
            print("Input product is not in JSON format", file=sys.stderr)

        # Calling the PEFAP algorithm
        impact_categories = ['EF single score', 'Climate change']
        #print("Estimating recipe")
        impact_estimation_result = estimate_impacts(product=product, impact_names=impact_categories)
        
        #print("Debugging :\n\n")
        #print(impact_estimation_result['ingredients_mass_share'])

        try:
            mass_share_dict = impact_estimation_result.get('ingredients_mass_share', {})

            # Mettre à jour les ingrédients avec leur part de masse estimée
            for ingredient in product["ingredients"]:
                ingredient_id = ingredient["id"]
                if ingredient_id in mass_share_dict:
                    ingredient["percent_estimate"] = mass_share_dict[ingredient_id]*100

            result_json = json.dumps(product, indent=4, ensure_ascii=False)

            print(result_json, file=sys.stdout)
        except :
            print(impact_estimation_result, file=sys.stderr)

    except :
        print("You need to add the PEFAP package (see README for further information.")
