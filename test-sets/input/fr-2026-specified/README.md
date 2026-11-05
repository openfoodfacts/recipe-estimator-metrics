# fr-2026-specified

Recent products sold in France with an ingredients list in French

Generated on 2026-11-05 from `candidates-20261005.jsonl.gz` with:

```
./scripts/build_test_set.py --preset fr-2026-specified --candidates candidates/candidates-20261005.jsonl.gz
```

## Selection criteria

- ingredients_lc: ['fr']
- countries: ['en:france']
- modified_after: 2025-01-01
- max_products: 1500
- per_category_max: 15
- min_specified_percent_n: 1
- max_unknown_ingredients_ratio: 0.2

## Selection statistics

- candidates: 325994
- rejected: ingredients_lc: 206572
- rejected: single_ingredient: 3063
- rejected: too_many_unknown_ingredients: 16971
- rejected: not_enough_specified_percents: 5176
- rejected: incomplete_nutrition: 18769
- rejected: countries: 17235
- rejected: modified_before: 446
- matching the criteria: 57762
- after limiting products per category: 26911
- rejected: inconsistent specified percents: 132
- saved: 1500
- inconsistent: minimum sum of percents: 122
- inconsistent: is greater than previous: 54
- inconsistent: percent <= 0: 1

## Products

- number of products: 1500
- ingredients languages: {'fr': 1500}
- number of ingredients with specified percent (5 = 5 or more): {1: 455, 2: 361, 3: 235, 4: 145, 5: 304}

### Category groups

- meals: 297
- spreads: 125
- yogurts and dairy desserts: 111
- fishes and seafood: 108
- breads: 90
- processed meats: 79
- beverages: 73
- biscuits and cakes: 60
- sauces: 53
- plant-based milks: 47
- cheeses: 40
- breakfast cereals: 39
- crisps: 30
- fats: 24
- jams: 23
- soups: 21
- dried fruits and vegetables: 16
- chocolates: 1

### Most frequent categories

- en:groceries: 1
- none: 1
- en:extruded-crispbreads: 1
- en:wholemeal-sliced-breads: 1
- en:tinned-mackerels: 1
- en:potato-crisps-in-sunflower-oil: 1
- en:Groceries: 1
- en:sliced-breads: 1
- en:mueslis-with-fruits: 1
- en:plant-based-meals: 1
- en:toasted-bread-rolls: 1
- en:Vegetables - Prepared/Processed (Shelf Stable): 1
- en:whole-milk-yogurts: 1
- en:strawberry-jams: 1
- en:sweetened-beverages: 1
- en:biscuits: 1
- en:apple-compotes: 1
- en:wholemeal-breads: 1
- en:ratatouille: 1
- en:microwave-meals: 1
- en:fruit-skyrs: 1
- en:vanilla-yogurt: 1
- en:breadsticks: 1
- en:hummus: 1
- en:skyrs: 1
- en:prepared-lentils: 1
- en:frozen-pizzas: 1
- en:pear-applesauces: 1
- en:sardines-in-olive-oil: 1
- en:crunchy-mueslis-with-fruits: 1
