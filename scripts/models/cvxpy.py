#!/usr/bin/python3
"""
*.py < input JSON product > output JSON product

Wrapper around the Recipe Estimator API to estimate the ingredients percent of a product
"""

import requests


recipe_estimator_api_url = "http://localhost:5521/api/v3/estimate_recipe_cvxpy"

def estimate_recipe(product):
    # Call API v3 recipe_estimator service
    request_data = product
    response = requests.post(recipe_estimator_api_url, json=request_data)

    try:
        response_json = response.json()

        if response_json["recipe_estimator"]["status"] != 0:
            return None, response_json
        else:
            return response_json, None
    except:
        return None, response


