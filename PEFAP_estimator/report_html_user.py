from reporting import ProductImpactReport

# Example of 2 products which are not in OFF (in Nextcloud you can see how write a product knowing nutrients and
# aliments)
Product_data = {"_id": 'NaN',
                "nutriments": {"proteins_100g": 0.5, "carbohydrates_100g": 39, "fiber_100g": 1.6, "salt_100g": 0},
                "ingredients": [{'id': 'en:strawberry', 'percent_min': 40}, {'id': 'en:sugar'}]}

Product_data = {"_id": 'NaN',
                "nutriments": {"proteins_100g": 0.4, "carbohydrates_100g": 58.6, "fiber_100g": 1.5, "salt_100g": 0.03},
                "ingredients": [{'id': 'en:sugar'}, {'id': 'en:fruits',
                                                     'ingredients': [{'id': 'en:strawberry', 'percent': 35},
                                                                     {'id': 'en:raspberry', 'percent': 15}]}]}

# # Have html of a OFF product (with the barcode)
# reporter = ProductImpactReport(barcode='20000776')  # change barcode
# reporter.to_html()
#
# # Have html of a product (without the barcode)
# reporter = ProductImpactReport(product=Product_data)
# reporter.to_html(filename='test_fruits.html')  # add name of the html

# Have html of a product (without the barcode) and knowing which we know the ciqual AGB
reporter = ProductImpactReport(product=Product_data, ciqual_AGB_similar='31024')
reporter.to_html(filename='test_fruits_with_ciqual_AGB.html')  # add name of the html

# Have html of a product (without the barcode) and knowing which OFF product looks like another product
reporter = ProductImpactReport(product=Product_data, barcode_similar='20000776')
reporter.to_html(filename='test_fruits_with_barcode.html')  # add name of the html
