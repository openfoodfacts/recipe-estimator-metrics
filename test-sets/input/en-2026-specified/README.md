# en-2026-specified

Recent products sold in English speaking countries with an ingredients list in English

Generated on 2026-11-05 from `candidates-20261005.jsonl.gz` with:

```
./scripts/build_test_set.py --preset en-2026-specified --candidates candidates/candidates-20261005.jsonl.gz
```

## Selection criteria

- ingredients_lc: ['en']
- countries: ['en:united-kingdom', 'en:ireland', 'en:united-states', 'en:canada', 'en:australia', 'en:new-zealand']
- modified_after: 2025-01-01
- max_products: 1500
- per_category_max: 15
- min_specified_percent_n: 1
- max_unknown_ingredients_ratio: 0.2

## Selection statistics

- candidates: 325994
- rejected: modified_before: 11067
- rejected: incomplete_nutrition: 13001
- rejected: ingredients_lc: 252917
- rejected: countries: 22891
- rejected: not_enough_specified_percents: 3289
- rejected: too_many_unknown_ingredients: 5592
- rejected: single_ingredient: 714
- matching the criteria: 16523
- after limiting products per category: 10274
- rejected: inconsistent specified percents: 146
- saved: 1500
- inconsistent: minimum sum of percents: 141
- inconsistent: is greater than previous: 47

## Products

- number of products: 1500
- ingredients languages: {'en': 1500}
- number of ingredients with specified percent (5 = 5 or more): {1: 596, 2: 368, 3: 241, 4: 142, 5: 153}

### Category groups

- meals: 223
- sauces: 119
- biscuits and cakes: 85
- spreads: 76
- breads: 72
- beverages: 67
- breakfast cereals: 63
- yogurts and dairy desserts: 54
- fishes and seafood: 48
- soups: 47
- processed meats: 43
- plant-based milks: 32
- crisps: 29
- fats: 25
- dried fruits and vegetables: 23
- chocolates: 21
- cheeses: 18
- jams: 11

### Most frequent categories

- en:reheatable-vegetable-soups: 3
- en:groceries: 2
- en:meat-analogues: 2
- xx:tofu: 2
- en:frozen-potato-fries: 2
- en:nuts: 2
- en:margherita-pizzas: 2
- en:wholemeal-sliced-breads: 2
- en:dips: 2
- en:bolognese-sauces: 2
- en:mixed-nuts: 2
- en:yogurt-drinks: 2
- en:spice-blends: 2
- en:reheatable-soups: 2
- en:cereal-bar-with-almonds-or-hazelnuts: 2
- en:oatcakes: 2
- en:raviolis: 2
- en:indian-style-sauces: 2
- en:sweet-chili-sauces: 2
- en:salad-dressings: 2
- en:sourdough-breads: 2
- en:plant-based-creams-for-cooking: 2
- en:chocolate-covered-biscuits: 2
- en:mixed-nuts-and-dried-fruits: 2
- en:ciabattas: 2
- en:instant-chocolate-powders: 2
- en:frozen-breaded-fish: 2
- en:prawn-crackers: 2
- en:vegetarian-hamburgers: 2
- en:mixed-dried-fruits: 2
