# water-loss-processed-meat

Processed meats (hams, sausages, dried meats), which can lose water during processing

Generated on 2026-11-05 from `candidates-20261005.jsonl.gz` with:

```
./scripts/build_test_set.py --preset water-loss-processed-meat --candidates candidates/candidates-20261005.jsonl.gz --overwrite
```

## Selection criteria

- ingredients_lc: ['fr', 'en']
- modified_after: 2023-01-01
- categories: ['en:prepared-meats', 'en:hams', 'en:sausages', 'en:dried-meats']
- max_products: 500
- per_category_max: 60
- min_specified_percent_n: 1
- max_unknown_ingredients_ratio: 0.2
- allow_sum_over_100: True
- include_specified_quantities: True

## Selection statistics

- candidates: 350315
- rejected: modified_before: 8308
- rejected: product_type: 191971
- rejected: ingredients_lc: 142719
- rejected: too_many_unknown_ingredients: 930
- rejected: incomplete_nutrition: 567
- rejected: not_enough_specified_percents: 864
- rejected: single_ingredient: 7
- matching the criteria: 4949
- after limiting products per category: 4092
- rejected: inconsistent specified percents: 4
- saved: 500
- inconsistent: is greater than previous: 4

## Products

- number of products: 500
- ingredients languages: {'fr': 418, 'en': 82}
- number of ingredients with specified percent (5 = 5 or more): {0: 91, 1: 223, 2: 96, 3: 52, 4: 19, 5: 19}
- products with specified quantities for 100 g of product: 114

### Category groups

- processed meats: 500
- spreads: 61
- meals: 34
- fishes and seafood: 21
- sauces: 2
- fats: 1
- cheeses: 1

### Most frequent categories

- en:dry-sausages-with-hazelnuts: 2
- en:dry-sausages-with-walnuts: 2
- en:italian-hams: 2
- en:saxe-fillet: 2
- en:white-hams: 1
- en:rillettes-from-mans: 1
- en:chorizo: 1
- en:industrial-knacks: 1
- en:sausages: 1
- en:cooked-turkey-breast-slices: 1
- en:pork-sausages: 1
- en:preparations-made-from-fish-meat: 1
- en:sauteed-black-pudding: 1
- en:cooked-chicken-breast-slices: 1
- en:smoked-sausages: 1
- fr:charcuteries-a-cuire: 1
- fr:saucisses-seches: 1
- en:pork-pates: 1
- en:chipolatas: 1
- en:dry-sausages: 1
- fr:saucissons-cuits: 1
- en:pate: 1
- en:dry-sausage-pure-pork: 1
- en:diced-ham: 1
- en:reconstituted-turkey-breast-slices: 1
- en:plain-lardons: 1
- en:prepared-meats-with-less-salt: 1
- en:toulouse-sausages: 1
- en:prepared-meats: 1
- en:country-style-pates: 1
