#!/usr/bin/python3
"""
*.py < input JSON product > output JSON product

Wrapper around the Recipe Estimator API to estimate the ingredients percent of a product
"""

import requests
import json
import sys

# Check that we have an input product in JSON format in STDIN
try:
    product = json.load(sys.stdin)
except ValueError:
    print("Input product is not in JSON format", file=sys.stderr)

# Call API v3 recipe_estimator service
recipe_estimator_api_url = "http://localhost:5521/api/v3/estimate_recipe_scipy"
request_data = {"product": product}
response = requests.post(recipe_estimator_api_url, json=request_data)

try:
    response_json = response.json()
    product_data = response_json.get("product", {})

    if product_data.get("recipe_estimator", {}).get("status", 0) != 0:
        print(json.dumps(response_json, indent=4), file=sys.stderr)
    else:
        print(json.dumps(product_data, indent=4))
except Exception as e:
    print(f"Error processing response: {e}", file=sys.stderr)
    print(response, file=sys.stderr)
