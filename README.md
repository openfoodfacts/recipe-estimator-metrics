# recipe-estimator-metrics

Metrics framework for recipe estimation (estimating percentage of each ingredient)


# Test sets

The test-sets/input directory contains test sets with products that have some or all of the ingredients percent values specified.

To evaluate a model accuracy, we remove some or all specified percent values, run the model to estimate the missing percent values, and then compare the estimated percent values with the specified percent values.

The test-sets/results directory contains the results of some models and some test sets.

# Models

The models directory contains executable files for each model we want to evaluate.

The executable file for each model expects the JSON of one product in STDIN, and outputs the resulting product (with added percent_estimate field for some or all ingredients) to STDOUT. In most cases, the executable file is just a wrapper for an API or local service.

# Scripts

## Create or add to a test set the products corresponding to a search query

./scripts/add_products_from_search_query_to_test_set.py 'http://fr.openfoodfacts.localhost/misc/en:all-ingredients-with-specified-percent/owner/org-les-mousquetaires.json?no_cache=1&page_size=100' test-sets/input/fr-les-mousquetaires-all-specified 

## Clean a test set

Remove fields that are not needed.

./scripts/clean_input_test_sets.py test-sets/input/fr-les-mousquetaires-all-specified

## Run a model on a test set

./scripts/run_model_on_input_test_sets.py models/product_opener_localhost.py test-sets/results/product_opener test-sets/input/fr-les-mousquetaires-all-specified

## Compute metrics for a test set

To compare estimated percent values to specified percent values:

./scripts/compute_metrics_for_model_on_test_sets.py test-sets/results/product_opener test-sets/input/fr-les-mousquetaires-all-specified

Sample output:

Test set fr-les-mousquetaires-all-specified
number of products: 100
total difference:983.3156699221914
average difference: 9.833156699221915
