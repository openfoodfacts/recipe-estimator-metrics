#!/usr/bin/python3
"""
compute_metrics_for_model_on_test_sets [name of model results] [names of one or more input test sets]
 
This script will go through each product JSON file of the specified input test sets to:
- Compute accuracy metrics comparing the estimated "percent_estimate" field in the resulting product
to the "percent" field in the input product
- Store product level metrics in the resulting product
- Aggregate metrics by test set

Example:

./scripts/compute_metrics_for_model_on_test_sets.py product_opener fr-les-mousquetaires-all-specified
"""

import sys
import os

from compute_metrics import compute_metrics_for_test_set

results = [sys.argv[1]] if (len(sys.argv) > 1) else os.listdir('test-sets/results')
for result in results:
    results_path = 'test-sets/results/' + result
    if os.path.isdir(results_path):
        test_sets = sys.argv[2:] if (len(sys.argv) > 2) else os.listdir(results_path)
        # Go through each result test set directory
        for test_set_name in test_sets:
            if os.path.isdir(f"{results_path}/{test_set_name}"):
                # Compute average metrics for the test set
                compute_metrics_for_test_set(results_path, test_set_name)
