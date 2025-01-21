import json

import pandas as pd

INGREDIENTS_DATA_FILEPATH = 'C:/Users/justine.catel/PycharmProjects/off-product-environmental-impact/data/off_ingredients_taxonomy.json'

with open(INGREDIENTS_DATA_FILEPATH, 'r', encoding = 'utf-8') as file:
    ingredients_data = json.load(file)
ingredients = {'name' : [x for x in ingredients_data]}
ingredients = pd.DataFrame(ingredients)

ingredients.to_csv('list_of_all_ingredients.csv', index=False)