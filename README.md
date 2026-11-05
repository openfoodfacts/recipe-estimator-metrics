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
  * `number_of_specified_ingredients`
  * `difference_per_specified_ingredient` (float): total_difference / number_of_specified_ingredients
  * `total_quantity_difference` (float): sum of abs(quantity_estimate - real percent), using percent_estimate when the model does not return a quantity_estimate
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
* skipped_products and skipped_products_problems (see below)
* average_difference_per_specified_ingredient: products with many specified percents weigh as much as products with few
* average_quantity_difference: for products that lost water (e.g. dried meats, crisps), the label percent can be the quantity of ingredient used for 100g of finished product (EU regulation 1169/2011 Annex VIII), which corresponds to quantity_estimate and not to percent_estimate
* category_groups: the same averages for groups of categories (cheeses, processed meats, crisps etc., see scripts/category_groups.py)
and some more data

## Specified quantities

Some labels specify the quantity of an ingredient used for 100 g of finished product, which can be more than 100 g
for products that lost water (e.g. "Viande de porc (140g pour 100g de produit)", "Préparé avec 76g de fruits pour 100g de produit fini").
Those specified quantities are compared to the quantity_estimate of the models (quantity before water loss), separately from the specified percents.

scripts/specified_quantities.py gets them from the quantity_g field of ingredients (only when the ingredients text contains the quantity followed by "per 100 g")
and from the specific_ingredients field (mentions after the ingredients list), and matches them to the ingredients of the list,
with the ingredients taxonomy (a specified quantity of "fruits" corresponds to all the fruits of the list) or with the ingredients text.

The ingredients taxonomy is read from taxonomies/ingredients.json (not committed), which can be copied from a local Product Opener:

```bash
mkdir -p taxonomies
docker cp po_off-backend-1:/mnt/podata/build-cache/taxonomies/ingredients.[hash].json taxonomies/ingredients.json
```

Specified quantities are hidden from the models (moved to quantity_g_hidden and specific_ingredients_hidden fields) when running them.

We report:
* in `ingredients_metrics` of each product: `specified_quantities` (with the specified quantity, the quantity_estimate of the matched ingredients and the difference, and the specified percent if the same ingredient also has one), `total_specified_quantity_difference`
* for the test set: `number_of_products_with_specified_quantities`, `number_of_specified_quantities`, `number_of_unmatched_specified_quantities`, `number_of_specified_quantities_with_specified_percent`, `average_specified_quantity_difference` (per specified quantity)

Products with specified quantities but no specified percent are not counted in the percent metrics.

To list the specified quantities of a test set:

```bash
./scripts/specified_quantities.py test-sets/input/water-loss-processed-meat
```

## Skipped products

Products whose specified percents are inconsistent are skipped, as they are most likely data errors or parsing errors
(e.g. "Cacao : 53% minimum" at the end of a chocolate ingredients list is parsed as an ingredient with 53%).
The check is done on the input product by scripts/specified_percent_check.py, so that all models are evaluated on the same products:
- specified percents must be greater than 0
- ingredients are listed by decreasing weight, so the ingredients before an ingredient with p% weigh at least p% each, and the sum of those minimums must not exceed 100% (ingredients under 2% can be listed in any order)
- sub ingredients percents can be relative to the parent or absolute

Test sets of products that lost water can accept sums over 100% with `"allow_sum_over_100": true` in their `test_set_config.conf` file (JSON).

To list the inconsistent products of a test set:

```bash
./scripts/specified_percent_check.py test-sets/input/fr-1000-some-specified-popular
```

Note: we used to skip products with `ingredients_percent_analysis == -1` in the resulting product, but this field depends on the model
(Product Opener recomputes it, other models copy the one of the input), and Product Opener flags some valid products.


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

## Build a test set from an Open Food Facts JSONL export

First, extract products with specified percents from the JSONL export (one pass on the full export, takes about 10 minutes):

```bash
./scripts/extract_candidates_from_jsonl.py ~/recipe-estimator/ingredients_distributions/openfoodfacts-products-20261005.jsonl.gz candidates/candidates-20261005.jsonl.gz
```

Then build test sets from the candidates. Presets define the selection criteria (language, countries, date of last modification, categories etc.):

```bash
./scripts/build_test_set.py --list-presets
./scripts/build_test_set.py --preset fr-2026-specified --candidates candidates/candidates-20261005.jsonl.gz --dry-run
./scripts/build_test_set.py --preset fr-2026-specified --candidates candidates/candidates-20261005.jsonl.gz
```

The script needs a local Product Opener to re-parse the ingredients, so that the percent fields are the values on the label
(the percent fields in the export are set by the percent estimation, and can be rescaled).
Products with incomplete nutrition facts and products with inconsistent specified percents are excluded,
and products are spread across categories (the most scanned products of each category first).
A README.md with the selection criteria and statistics is generated in the test set directory.

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

