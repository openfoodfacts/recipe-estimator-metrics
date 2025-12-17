#!/usr/bin/python3
"""
compare_metrics.py [path_to_result_set_A] [path_to_result_set_B]

This script compares two result sets for the same test set, product by product.
It ignores products not present in both result sets.
It outputs the number of products where one set is better than the other (based on total_difference, lower is better).
It also outputs top categories where one set is better, and a CSV file with aggregated stats by category.
"""

import sys
import os
import json
import csv

def main():
    if len(sys.argv) != 3:
        print("Usage: python compare_metrics.py <path_to_result_set_A> <path_to_result_set_B>")
        sys.exit(1)

    path_a = sys.argv[1]
    path_b = sys.argv[2]

    # Extract test_set_name from path_a (assuming same for both)
    test_set_name = os.path.basename(path_a)
    input_path = f"test-sets/input/{test_set_name}"

    # Get list of product files in both (excluding CSV and JSON summary files)
    exclude_files = {'products_stats.csv', 'products_ingredients_stats.csv', 'ingredients_stats.csv', 'results_summary.json'}
    products_a = set(f for f in os.listdir(path_a) if f not in exclude_files and f.endswith('.json'))
    products_b = set(f for f in os.listdir(path_b) if f not in exclude_files and f.endswith('.json'))
    common_products = products_a & products_b

    # Counters
    count_a_better = 0
    count_b_better = 0
    count_equal = 0

    # Category stats: category -> dict
    category_stats = {}

    # Product comparisons list
    product_comparisons = []

    for product_file in sorted(common_products):
        # Load input product to get categories
        input_file = os.path.join(input_path, product_file)
        try:
            with open(input_file, 'r') as f:
                input_data = json.load(f)
        except FileNotFoundError:
            continue  # Skip if input not found

        categories = input_data.get('categories_tags', [])
        if not categories:
            categories = ['unknown']

        # Load result A
        result_a_file = os.path.join(path_a, product_file)
        try:
            with open(result_a_file, 'r') as f:
                result_a = json.load(f)
        except:
            continue
        diff_a = result_a.get('ingredients_metrics', {}).get('total_difference', float('inf'))

        # Load result B
        result_b_file = os.path.join(path_b, product_file)
        try:
            with open(result_b_file, 'r') as f:
                result_b = json.load(f)
        except:
            continue
        diff_b = result_b.get('ingredients_metrics', {}).get('total_difference', float('inf'))

        # Determine which is better (lower difference is better)
        if diff_a < diff_b:
            count_a_better += 1
            better = 'a'
        elif diff_b < diff_a:
            count_b_better += 1
            better = 'b'
        else:
            count_equal += 1
            better = 'equal'

        # Update category stats for each category
        for cat_tag in categories:
            category = cat_tag.replace('en:', '').replace('-', ' ').title()
            if category not in category_stats:
                category_stats[category] = {
                    'num_products': 0,
                    'a_better': 0,
                    'b_better': 0,
                    'equal': 0,
                    'total_diff_a': 0.0,
                    'total_diff_b': 0.0
                }
            cat = category_stats[category]
            cat['num_products'] += 1
            if better == 'a':
                cat['a_better'] += 1
            elif better == 'b':
                cat['b_better'] += 1
            else:
                cat['equal'] += 1
            cat['total_diff_a'] += diff_a if diff_a != float('inf') else 0
            cat['total_diff_b'] += diff_b if diff_b != float('inf') else 0

        # Add to product comparisons
        product_comparisons.append({
            'code': product_file[:-5],
            'product_name': input_data.get('product_name', ''),
            'difference_A': diff_a if diff_a != float('inf') else None,
            'difference_B': diff_b if diff_b != float('inf') else None,
            'difference_A_minus_B': (diff_a - diff_b) if diff_a != float('inf') and diff_b != float('inf') else None,
            'better': better
        })

    # Output summary
    print(f"Total products compared: {len(common_products)}")
    print(f"Set A better: {count_a_better}")
    print(f"Set B better: {count_b_better}")
    print(f"Equal: {count_equal}")

    # Top categories where A is better (by number of products)
    sorted_cats_a_num = sorted(
        [(cat, stats) for cat, stats in category_stats.items() if stats['num_products'] > 0],
        key=lambda x: x[1]['a_better'],
        reverse=True
    )
    print("\nTop categories where Set A is better (by number of products):")
    for cat, stats in sorted_cats_a_num[:10]:
        pct = (stats['a_better'] / stats['num_products']) * 100
        print(f"{cat}: {stats['a_better']} products ({pct:.1f}%)")

    # Top categories where A is better (by % of products)
    sorted_cats_a_pct = sorted(
        [(cat, stats) for cat, stats in category_stats.items() if stats['num_products'] > 0],
        key=lambda x: x[1]['a_better'] / x[1]['num_products'],
        reverse=True
    )
    print("\nTop categories where Set A is better (by % of products):")
    for cat, stats in sorted_cats_a_pct[:10]:
        pct = (stats['a_better'] / stats['num_products']) * 100
        print(f"{cat}: {stats['a_better']}/{stats['num_products']} ({pct:.1f}%)")

    # Top categories where B is better (by number of products)
    sorted_cats_b_num = sorted(
        [(cat, stats) for cat, stats in category_stats.items() if stats['num_products'] > 0],
        key=lambda x: x[1]['b_better'],
        reverse=True
    )
    print("\nTop categories where Set B is better (by number of products):")
    for cat, stats in sorted_cats_b_num[:10]:
        pct = (stats['b_better'] / stats['num_products']) * 100
        print(f"{cat}: {stats['b_better']} products ({pct:.1f}%)")

    # Top categories where B is better (by % of products)
    sorted_cats_b_pct = sorted(
        [(cat, stats) for cat, stats in category_stats.items() if stats['num_products'] > 0],
        key=lambda x: x[1]['b_better'] / x[1]['num_products'],
        reverse=True
    )
    print("\nTop categories where Set B is better (by % of products):")
    for cat, stats in sorted_cats_b_pct[:10]:
        pct = (stats['b_better'] / stats['num_products']) * 100
        print(f"{cat}: {stats['b_better']}/{stats['num_products']} ({pct:.1f}%)")

    # Write CSV
    csv_filename = 'category_comparison.csv'
    with open(csv_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'category', 'number_of_products', 'number_better_in_A', 'percent_better_in_A',
            'number_better_in_B', 'percent_better_in_B', 'total_difference_A', 'total_difference_B', 'total_difference_A_minus_B'
        ])
        for cat, stats in sorted(category_stats.items()):
            if stats['num_products'] == 0:
                continue
            pct_a = (stats['a_better'] / stats['num_products']) * 100
            pct_b = (stats['b_better'] / stats['num_products']) * 100
            writer.writerow([
                cat, stats['num_products'], stats['a_better'], f"{pct_a:.1f}%",
                stats['b_better'], f"{pct_b:.1f}%", round(stats['total_diff_a'], 3), round(stats['total_diff_b'], 3), round(stats['total_diff_a'] - stats['total_diff_b'], 3)
            ])
    print(f"\nCSV file written: {csv_filename}")

    # Write product comparison CSV
    product_csv_filename = 'product_comparison.csv'
    with open(product_csv_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['code', 'product_name', 'difference_A', 'difference_B', 'difference_A_minus_B', 'better'])
        for comp in product_comparisons:
            writer.writerow([
                comp['code'], comp['product_name'], comp['difference_A'], comp['difference_B'], comp['difference_A_minus_B'], comp['better']
            ])
    print(f"Product comparison CSV file written: {product_csv_filename}")

if __name__ == "__main__":
    main()