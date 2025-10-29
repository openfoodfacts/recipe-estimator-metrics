#!/usr/bin/python3
"""
add_product_codes_to_test_set

This script loads the products listed in product_codes.txt into the current folder.

"""

import json
import sys
import os
import requests

# Load the products from the search query URL
# Set a user agent to avoid being blocked as a web crawling bot
headers = {
    "User-Agent": "openfoodfacts/recipe-estimator-metrics - add_product_codes_to_test_set.py"
}

with open("product_codes.txt", "r") as codes_file:
    lines = codes_file.readlines()
    
for line in lines:
    code = line.strip()
    search_url = f"https://world.openfoodfacts.org/api/v2/product/{code}"
    response = requests.get(search_url, headers=headers)
    if response.status_code != 200:
        print(f"Error: could not load {code}")
    else:
        # print the response for debugging
        # print(response.text)
        data = response.json()
        if data['status'] != 1:
            print(f"Error: {code}: {data.get('status_verbose')}")
        else:
            # Save the product in the current directory
            # Note: we use the barcode as the filename
            # Note: we use the pretty JSON dump for easy inspection of diffs
            # Note: we use the ensure_ascii=False option to avoid encoding issues with non-ASCII characters
            # Note: we use the sort_keys=True option to make the output deterministic 
            product = data["product"]
            nutrients = product.get('nutriments')
            countries = product.get('countries_tags')
            if nutrients and countries and nutrients.get('carbohydrates_100g') and nutrients.get('fat_100g') and nutrients.get('proteins_100g'):
                for country_tag in countries:
                    country = country_tag.split(':')[1]
                    if not os.path.exists(country):
                        os.makedirs(country)

                    with open(f"{country}/{code}.json", "w") as f:
                        json.dump(product, f, indent=4, ensure_ascii=False, sort_keys=True)
            else:
                print(f"Skipping {code} as it does not have basic nutrients")
