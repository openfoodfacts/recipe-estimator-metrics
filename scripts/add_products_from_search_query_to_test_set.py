#!/usr/bin/python3
"""
add_products_from_search_query_to_test_set [product opener API search query url] [path of input test set]

This script loads the results of a search query URL, and saves individual product files in the specified input test set directory.

Example:

./scripts/add_products_from_search_query_to_test_set.py 'http://fr.openfoodfacts.localhost/misc/en:all-ingredients-with-specified-percent/owner/org-les-mousquetaires.json?no_cache=1' test-sets/input/fr-les-mousquetaires-all-specified

"""

import json
import sys
import os
import requests

# Print usage
if len(sys.argv) < 3:
    print("Usage: add_products_from_search_query_to_test_set.py [product opener API search query url] [path of input test set]")
    sys.exit(1)

search_url = sys.argv[1]
test_set_path = sys.argv[2]

# Create the test set directory if it doesn't exist
if not os.path.exists(test_set_path):
    os.makedirs(test_set_path)

# Load the products from the search query URL
# Set a user agent to avoid being blocked as a web crawling bot
headers = {
    "User-Agent": "openfoodfacts/recipe-estimator-metrics - add_products_from_search_query_to_test_set.py"
}
response = requests.get(search_url, headers=headers)
if response.status_code != 200:
    print("Error: could not load products from search query URL: " + search_url)
    sys.exit(1)
else:
    # print the response for debugging
    print(response.text)
    data = response.json()

    # Go through each product and save it in the input test set directory
    # Note: we use the barcode as the filename
    # Note: we use the pretty JSON dump for easy inspection of diffs
    # Note: we use the ensure_ascii=False option to avoid encoding issues with non-ASCII characters
    # Note: we use the sort_keys=True option to make the output deterministic 
    for product in data["products"]:
        with open(test_set_path + "/" + product["code"] + ".json", "w") as f:
            json.dump(product, f, indent=4, ensure_ascii=False, sort_keys=True)

