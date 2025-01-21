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
recipe_estimator_api_url = "http://localhost:8000/api/v3/estimate_recipe"
request_data = product
response = requests.post(recipe_estimator_api_url, json=request_data)

try:
    response_json = response.json()

    # Pretty print the resulting JSON structure over the input file for easy inspection of diffs
    print(json.dumps(response_json, indent=4))
except:
    print(response, file=sys.stderr)
