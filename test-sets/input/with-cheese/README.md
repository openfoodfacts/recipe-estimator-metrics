# with-cheese

Cheeses, and products with a specified percent of cheese

Generated on 2026-11-05 from `candidates-20261005.jsonl.gz` with:

```
./scripts/build_test_set.py --preset with-cheese --candidates candidates/candidates-20261005.jsonl.gz
```

## Selection criteria

- ingredients_lc: ['fr', 'en']
- modified_after: 2023-01-01
- categories: ['en:cheeses']
- specified_ingredient_regex: cheese|emmental|mozzarella|parmigiano|parmesan|cheddar|comte|gouda|raclette|roquefort|feta|ricotta|mascarpone|gruyere|reblochon|camembert|brie|edam|grana-padano|pecorino|tomme|beaufort|cantal|munster|fromage
- max_products: 500
- per_category_max: 25
- min_specified_percent_n: 1
- max_unknown_ingredients_ratio: 0.2
- allow_sum_over_100: True

## Selection statistics

- candidates: 325994
- rejected: modified_before: 8090
- rejected: product_type: 173171
- rejected: ingredients_lc: 133495
- rejected: incomplete_nutrition: 1108
- rejected: too_many_unknown_ingredients: 1572
- rejected: not_enough_specified_percents: 829
- rejected: single_ingredient: 20
- matching the criteria: 7709
- after limiting products per category: 5264
- rejected: inconsistent specified percents: 36
- saved: 500
- inconsistent: is greater than previous: 36
- inconsistent: percent <= 0: 1

## Products

- number of products: 500
- ingredients languages: {'fr': 420, 'en': 80}
- number of ingredients with specified percent (5 = 5 or more): {1: 71, 2: 90, 3: 71, 4: 71, 5: 197}

### Category groups

- meals: 193
- cheeses: 132
- spreads: 43
- yogurts and dairy desserts: 41
- sauces: 25
- biscuits and cakes: 10
- fishes and seafood: 10
- crisps: 9
- processed meats: 8
- soups: 7
- breads: 5
- fats: 3
- beverages: 3
- dried fruits and vegetables: 2

### Most frequent categories

- en:processed-cheeses: 2
- en:margherita-pizzas: 2
- en:raviolis: 2
- en:cheddar-cheese: 2
- en:frozen-pizzas: 1
- en:groceries: 1
- en:vegetarian-patties: 1
- en:crackers-appetizers: 1
- en:cheese-spreads: 1
- none: 1
- en:green-pestos: 1
- en:pizzas: 1
- en:flavoured-uncured-soft-cheese-spreadable-with-around-30-40-fat: 1
- en:cream-cheeses: 1
- en:plant-based-meals: 1
- en:pasteurized-cheeses: 1
- en:microwave-meals: 1
- en:industrial-cheese: 1
- en:regina-pizza: 1
- en:beef-cottage-pies: 1
- en:vegetable-pizza: 1
- en:frozen-ready-made-meals: 1
- en:Vegetables - Prepared/Processed (Frozen): 1
- en:red-pestos: 1
- en:Groceries: 1
- fr:fromages-blancs-aromatises: 1
- fr:fromages-blancs-natures: 1
- en:feta-blocs: 1
- en:flammekueche: 1
- en:three-cheese-pizza: 1
