#!/usr/bin/python3
"""
*.py < input JSON product > output JSON product

This code uses the PEFAP Estimator to estimate the ingredients percent of a product
"""

import os
import sys
import json
import sys
import time

pefap_package_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../PEFAP_estimator"))
#print(pefap_package_dir)

setup = 1 #0 for debugging on this file (__main__), 1 for use as a package 

# Local configuration
if os.path.isdir(pefap_package_dir):
    sys.path.insert(0, pefap_package_dir)

    if (setup == 0):
        try :
            # Local configuration
            from impacts_estimation import estimate_impacts

            # Gettting the product pieces of information 
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            input_file = "../test-sets/input/nutella/nutella-ferrero.json"
            #input_file = "../test-sets/input/test2/test_martin.json"
            
            path_to_input_file = os.path.normpath(os.path.join(script_dir, input_file))
            #print(path_to_input_file)
            
            try:
                with open(path_to_input_file, "r", encoding="utf-8") as file:
                    product = json.load(file)
                print("\n✅ JSON chargé avec succès !")
            except json.FileNotFoundError:
                print("❌ Erreur : Fichier introuvable !")
            except json.JSONDecodeError:
                print("❌ Erreur : Le fichier ne contient pas un JSON valide !")
            
            # Calling the PEFAP algorithm
            print("\n --- CALLING PEFAP --- \n")
            impact_categories = ['EF single score', 'Climate change']

            start_product_time = time.time()
            impact_estimation_result = estimate_impacts(product=product, impact_names=impact_categories)
            end_product_time = time.time()
            execution_time = end_product_time - start_product_time

            print("\n --- RESULT --- \n")
            print(impact_estimation_result.get('ingredients_mass_share', {}))
            
            # Définir un chemin relatif pour stocker le fichier
            output_file_path = os.path.normpath("../test-sets/results/pefap_estimator/output_test_martin/output_test_martin.json")
            path_to_output_file = os.path.normpath(os.path.join(script_dir, output_file_path))

            # Créer le dossier parent s'il n'existe pas
            output_dir = os.path.dirname(path_to_output_file)
            os.makedirs(output_dir, exist_ok=True)
            
            # Convertir le dictionnaire impact_estimation_result en une chaîne JSON
            result_json = json.dumps(impact_estimation_result, indent=4, ensure_ascii=False)
            with open(path_to_output_file, "w", encoding="utf-8") as json_file:
                json_file.write(result_json)

            try:            
                mass_share_dict = impact_estimation_result.get('ingredients_mass_share', {})

                # Mettre à jour les ingrédients avec leur part de masse estimée
                for ingredient in product["ingredients"]:
                    ingredient_id = ingredient["id"]
                    if ingredient_id in mass_share_dict:
                        ingredient["percent_estimate"] = mass_share_dict[ingredient_id]*100
            
            except Exception as e:
                print(e)
                #print(impact_estimation_result, file=sys.stderr)
        except Exception as e:
            print(e)
            #print("You need to add the PEFAP package (see README for further information.")

    else :
        try: 
            from impacts_estimation import estimate_impacts
        
            # Check that we have an input product in JSON format in STDIN
            try:
                product = json.load(sys.stdin)
            except ValueError:
                print("Input product is not in JSON format", file=sys.stderr)

            # Calling the PEFAP algorithm
            impact_categories = ['EF single score', 'Climate change']
            start_product_time = time.time()
            impact_estimation_result = estimate_impacts(product=product, impact_names=impact_categories)
            end_product_time = time.time()
            execution_time = end_product_time - start_product_time
        
            #print("Debugging :\n\n")
            #print(impact_estimation_result['ingredients_mass_share'])

            try:            
                mass_share_dict = impact_estimation_result.get('ingredients_mass_share', {})

                def update_ingredient_percentages(ingredients_list, mass_share_dict):
                    seen_ingredients = set()  # Track ingredients that have already been assigned a percentage

                    for ingredient in ingredients_list:
                        ingredient_id = ingredient.get("id")
                        has_sub_ingredients = "ingredients" in ingredient and isinstance(ingredient["ingredients"], list)

                        if ingredient_id in mass_share_dict:
                            if ingredient_id not in seen_ingredients:
                                ingredient["percent_estimate"] = mass_share_dict[ingredient_id] * 100
                                seen_ingredients.add(ingredient_id)  # Mark as assigned
                            else:
                                ingredient["percent_estimate"] = 0  # Set to 0 for duplicate occurrences
                        elif not has_sub_ingredients:
                            # If ingredient is not in mass_share_dict and has no sub-ingredients, set percent_estimate = 0
                            ingredient["percent_estimate"] = 0

                        # Recursively update sub-ingredients if they exist
                        if has_sub_ingredients:
                            update_ingredient_percentages(ingredient["ingredients"], mass_share_dict)

                update_ingredient_percentages(product["ingredients"], mass_share_dict)

                # Add execution time to the result JSON
                impact_estimation_result["pefap_execution_time"] = execution_time

                product["pefap_data"] = impact_estimation_result

                result_json = json.dumps(product, indent=4, ensure_ascii=False)

                print(result_json, file=sys.stdout)
            except :
                print("An error occured : PEFAP didn't give any results.", file=sys.stderr)
                #print(impact_estimation_result, file=sys.stderr)

        except :
            print("You need to add the PEFAP package (see README for further information).")
