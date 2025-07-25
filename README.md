# recipe-estimator-metrics

Metrics framework for recipe estimation (estimation of the percentage of each ingredient and sub ingredient)

Note that a recipe estimate is for the content before possible water loss (due to transformation like cooking for example).

# Test sets

The test-sets/input directory contains test sets with products that have some or all of the ingredients percent values specified.

To evaluate a model accuracy, we remove some or all specified percent values, run the model to estimate the missing percent values, and then compare the estimated percent values with the specified percent values.

The test-sets/results directory contains the results of some models and some test sets.

# Metrics

The main metric we compute and want to optimize is the ingredient weight difference.
For each product, for each ingredient that has a specified percent value, we compute the absolute difference between the estimated percent value and the specified percent value. We then sum the absolute differences for all ingredients.

## What we compute

On each product:
* we have:
  * models might add a specific entry to report some informations
    * it's the case for recipe estimator (in `recipe_estimator`) 
* we will report in `ingredients_metrics`:
  * `total_difference` (float): sum of difference
  * `total_specified_input_percent` (float): the sum of the percentage for known ingredients (given on the packaging)
  * `relative_difference` (float): sum(difference) / total_specified_input_percent (only if total_specified_input_percent is not 0) 
  * `number_of_ingredients_without_ciqual_code`

On each ingredient, in the product:
* as input, we have:
  * percent_estimate - the percent of this ingredient in the recipe
  * quantity_estimate - the quantity we estimated of the product (sum of quantity might be more than 100g due to evaporation)
* per ingredients we add:
  * `difference`: abs(percent_estimate - real percent) if we know real percent  

And we will globaly report:
* total_difference
* number_of_products
* average_difference
and some more data


## Metrics for subsets of the test sets

The percent estimation models run on sometimes noisy data:
- the ingredient list can be incorrect (mispellings, OCR issues, extra strings before or after the list etc.)
- the parsed ingredient structure can be incorrect (in particular mismatched parenthesis will result in incorrect nested sub ingredients)
- not all ingredients can be matched to known ingredients in the Open Food Facts ingredients taxonomy
- not all ingredients in the taxonomy have an association to the CIQUAL database from which we get nutrient data for the ingredient (which is a key input for the Recipe estimator model)

For those reasons, we report metrics for different sub sets:

### All products

The complete set of products is the most representative for the percent analysis that runs for all products on Open Food Facts.

### Products with 100% of their ingredients matched to the ingredients taxonomy

This is a good indication that we have a correct text ingredient list, and that we could correctly parse it to construct the list of ingredients and sub ingredients.

To be implemented in the metrics framework.

### Products with 100% of their ingredients matched to CIQUAL

This is the best case scenario for the Recipe Estimator, as we are likely to have a correct ingredient list correctly parsed, and we also have nutrient data for all ingredients.

# Models

The models directory contains executable files for each model we want to evaluate.

The executable file for each model expects the JSON of one product in STDIN, and outputs the resulting product (with added percent_estimate field for some or all ingredients) to STDOUT.
In most cases, the executable file is just a wrapper for an API or local service.

We currently have 3 models:

## Product Opener model

The current ingredient percent estimation models runs in [Product Opener](https://github.com/openfoodfacts/openfoodfacts-server), which is the backend of Open Food Facts.
The model is simplistic: it computes the possible minimum and maximum ranges for each ingredient (based on their order in the ingredient list)
and picks 1 possible set of percentages by placing itself in the middle of the range for the first ingredient, and then going down to the other ingredients.

You can run this model in your development machine by following those instructions:
[Product Opener dev - Quick start guide](https://github.com/openfoodfacts/openfoodfacts-server/blob/main/docs/dev/how-to-quick-start-guide.md)

Once Product Opener runs in your dev environment, you can use the product_opener_localhost model in the metrics framework.

## Recipe estimator model

[Recipe Estimator](https://github.com/openfoodfacts/recipe-estimator) is a new model that uses linear solving to find the most likely quantity of each ingredient based on how close the sum of the nutrients of each ingredient matches the nutritional facts table listed on the product.

Once Recipe Estimator runs in your dev environment, you can use the recipe_estimator_localhost model in the metrics framework.

## PEFAP estimator model

[PEFAP estimator](https://framagit.org/GustaveCoste/off-product-environmental-impact) is a based-on Monte-Carlo algorithm tool that estimates the environmental impact of a given product, based on its ingredients

To execute this model, you need :

1) To install the PEFAP package in the root of this deposit :

2) To execute the following command :

```bash
python scripts/run_model_on_input_test_sets.py "you\path\to\python.exe;models/pefap_estimator_localhost.py" test-sets/results/pefap_estimator test-sets/input/pick_a_test
```

(don't forget to install de required python packages !!)

# Usage

## Installation

## Python environment

This is using Python3.

Create a virtualenv.
```
python -m venv venv 
```

Enter virtualenv (Windows).
```
venv/Scripts/activate
```
or (Linux)
```
source venv/bin/activate
```

Install requirements.
```
pip install -r requirements.txt
```

## Create or add to a test set the products corresponding to a search query

This script is used to create a new test set by querying the Open Food Facts production (or local development) database for products matching a specific query.

```bash
./scripts/add_products_from_search_query_to_test_set.py 'http://fr.openfoodfacts.localhost/misc/en:all-ingredients-with-specified-percent/owner/org-les-mousquetaires.json?no_cache=1&page_size=100' test-sets/input/fr-les-mousquetaires-all-specified 
```

## Clean a test set

Remove fields that are not needed.

```bash
./scripts/clean_input_test_sets.py test-sets/input/fr-1000-some-specified-popular
```

## Update the ingredients parsing of a test set

This script reruns the ingredients analysis to recreate the "ingredients" structure from the textual list of ingredients (ingredients_text).

```bash
./scripts/parse_ingredients_for_input_test_sets.py test-sets/input/fr-1000-some-specified-popular
```

## Run a model on a test set

This script runs a specific model on a specific test set, and estimates the ingredients for all the products in the test set.

```bash
./scripts/run_model_on_input_test_sets.py recipe_estimator_localhost recipe_estimator_main_20241107 fr-1000-some-specified-popular

```

## Compute metrics for a test set

To compare estimated percent values to specified percent values:

```bash
./scripts/compute_metrics_for_model_on_test_sets.py test-sets/results/product_opener test-sets/input/fr-les-mousquetaires-all-specified
```

Sample output:

```
Results summary for test set fr-1000-some-specified-popular:
Total difference: 23707.128
Number of products: 1000
Average difference: 23.71
All ciqual test set total difference: 1577.6545
All ciqual test set number of products: 128
All ciqual test set average difference: 12.33
Percent estimate with ciqual_food_code: 50.2
Percent estimate with ciqual_proxy_food_code: 35.6
Percent estimate with ciqual or ciqual_proxy_food_code: 85.9
```

The key metrics are:
- Average difference: the average sum of quantity differences for all ingredients of the product.
- All ciqual test set average difference: the average difference restricted to a subset of products for which we have been able to match all ingredients to the CIQUAL nutritional database.

## Show side-by-side product comparison for all models

Run

```
./scripts/compute_product_metrics_for_all_models.py
```
This will generate the `test-sets/results/products_stats.csv` file which has a column for each result set and shows the total percentage variance for each product.

