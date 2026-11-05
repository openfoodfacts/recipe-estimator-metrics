# water-loss-dried

Dried fruits and vegetables and products declaring quantities used per 100 g of finished product

Generated on 2026-11-05 from `candidates-20261005.jsonl.gz` with:

```
./scripts/build_test_set.py --preset water-loss-dried --candidates candidates/candidates-20261005.jsonl.gz --overwrite
```

## Selection criteria

- ingredients_lc: ['fr', 'en']
- modified_after: 2023-01-01
- categories: ['en:dried-fruits', 'en:dried-vegetables', 'en:dried-meats']
- text_regex: \d+(?:[,.]\d+)? ?g (?:de |d'|of )?[^,.;:()]{0,40}(?:pour|per|for) 100 ?g|préparée? avec \d|élaborée? avec \d|prepared with \d|made with \d
- max_products: 500
- per_category_max: 40
- min_specified_percent_n: 1
- max_unknown_ingredients_ratio: 0.2
- allow_sum_over_100: True
- include_specified_quantities: True

## Selection statistics

- candidates: 350315
- rejected: modified_before: 8308
- rejected: product_type: 194311
- rejected: ingredients_lc: 142719
- rejected: too_many_unknown_ingredients: 980
- rejected: single_ingredient: 119
- rejected: not_enough_specified_percents: 605
- rejected: incomplete_nutrition: 618
- matching the criteria: 2655
- after limiting products per category: 2240
- rejected: inconsistent specified percents: 11
- saved: 500
- inconsistent: is greater than previous: 11

## Products

- number of products: 500
- ingredients languages: {'fr': 382, 'en': 118}
- number of ingredients with specified percent (5 = 5 or more): {0: 263, 1: 117, 2: 38, 3: 23, 4: 16, 5: 43}
- products with specified quantities for 100 g of product: 342

### Category groups

- processed meats: 143
- spreads: 140
- dried fruits and vegetables: 112
- jams: 91
- meals: 23
- sauces: 14
- breads: 5
- fishes and seafood: 2
- breakfast cereals: 2
- biscuits and cakes: 1

### Most frequent categories

- en:mixed-dried-fruits: 5
- en:dried-fruits: 3
- en:mixed-nuts-and-dried-fruits: 3
- en:strawberry-jams: 2
- en:apricot-jams: 2
- en:raspberry-jams: 2
- en:bilberry-jams: 2
- en:chestnut-spreads: 2
- en:dried-tomato-in-oil: 2
- en:dried-tomatoes: 2
- en:chorizo: 2
- en:mixed-berry-jams: 2
- fr:saucisses-seches: 2
- en:rillettes-from-mans: 2
- fr:Tartinades: 2
- en:figs-jams: 2
- en:low-sugar-fruit-jam: 2
- fr:Confitures gelees ou marmelades: 2
- en:cherry-jams: 2
- en:dried-cranberries: 2
- en:shelf-stable-jams: 2
- en:dry-sausage-pure-pork: 2
- en:clementine-jams: 2
- en:dry-sausages: 2
- en:dried-bananas: 2
- en:orange-jams: 2
- en:dried-apricots: 2
- none: 2
- en:raisins: 2
- en:dried-mangoes: 2
