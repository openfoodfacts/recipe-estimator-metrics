# water-loss-crisps

Crisps, which lose water when fried

Generated on 2026-11-05 from `candidates-20261005.jsonl.gz` with:

```
./scripts/build_test_set.py --preset water-loss-crisps --candidates candidates/candidates-20261005.jsonl.gz --overwrite
```

## Selection criteria

- ingredients_lc: ['fr', 'en']
- modified_after: 2023-01-01
- categories: ['en:crisps', 'en:potato-crisps']
- max_products: 500
- per_category_max: 60
- min_specified_percent_n: 1
- max_unknown_ingredients_ratio: 0.2
- allow_sum_over_100: True
- include_specified_quantities: True

## Selection statistics

- candidates: 350315
- rejected: modified_before: 8308
- rejected: product_type: 196408
- rejected: ingredients_lc: 142719
- rejected: incomplete_nutrition: 258
- rejected: not_enough_specified_percents: 235
- rejected: too_many_unknown_ingredients: 500
- rejected: single_ingredient: 9
- matching the criteria: 1878
- after limiting products per category: 982
- rejected: inconsistent specified percents: 2
- saved: 500
- inconsistent: is greater than previous: 2

## Products

- number of products: 500
- ingredients languages: {'fr': 317, 'en': 183}
- number of ingredients with specified percent (5 = 5 or more): {1: 201, 2: 175, 3: 80, 4: 28, 5: 16}
- products with specified quantities for 100 g of product: 1

### Category groups

- crisps: 500
- breads: 12
- meals: 5
- sauces: 4
- cheeses: 3
- spreads: 2
- biscuits and cakes: 2
- fishes and seafood: 2
- dried fruits and vegetables: 2
- breakfast cereals: 1
- processed meats: 1

### Most frequent categories

- en:prawn-crackers: 10
- en:potato-crisps-in-sunflower-oil: 8
- en:corn-chips: 8
- en:crisps: 8
- en:potato-crisps: 8
- en:lentil-crisps: 8
- en:farmer-s-crisps: 8
- en:stacked-extruded-potato-crisps: 8
- en:flavoured-potato-crisps: 8
- en:barbecue-crisps: 8
- fr:Chips classiques et ondulees: 8
- en:old-fashioned-style-potato-crisps: 8
- en:crackers-appetizers: 8
- fr:Tortillas: 8
- en:wavy-potato-crisps: 8
- en:snacks-salés: 8
- en:chickpea-crisps: 8
- en:quinoa-crisps: 8
- en:puffed-salty-snacks: 8
- en:salty-snacks-made-from-potato: 8
- en:paprika-crisps: 8
- en:puffed-salty-snacks-made-from-maize: 8
- en:truffle-crisps: 8
- en:crisps-made-from-reconstituted-potato: 8
- en:salt-and-vinegar-crisps: 8
- en:potato-crisps-in-olive-oil: 8
- fr:EPICERIE: 8
- en:puffed-salty-snacks-made-from-potato-and-soy: 7
- en:roasted-chicken-crisps: 7
- en:sweet-potato-crisps: 7
