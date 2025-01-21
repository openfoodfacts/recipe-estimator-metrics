""" Script to link CIQUAL and FCEN nutritional data to OFF ingredients
using the previous codes of Gustave and the new mapping table (mapping created by OFF)
"""

import json
import math
from statistics import mean

import pandas as pd
from tqdm import tqdm

from ingredients_characterization.vars import CIQUAL_DATA_FILEPATH, ING_OFF_WITH_CIQUAL_FILEPATH, \
    AGRIBALYSE_DATA_FILEPATH, FCEN_DATA_FILEPATH
from data import INGREDIENTS_DATA_FILEPATH
from ingredients_characterization import having_a_table_with_OFF_direct_and_Gustave_links
from ingredients_characterization.nutrition.ciqual import data_ciqual_OFF
CODES_CIQUAL_IN_OFF_REPLACED_BY_OTHER_CODE = {'26132': '26210', '7430': '7432', '13082': '13024'}
# all codes ciqual in ING_OFF_WITH_CIQUAL which are not in the 2020 version of Ciqual

def main():

    with open(CIQUAL_DATA_FILEPATH, 'r', encoding='utf8') as file:
        ciqual_data = json.load(file)

    with open(AGRIBALYSE_DATA_FILEPATH, 'r', encoding='utf8') as file:
        agribalyse_impacts = json.load(file)
    agribalyse_impacts = {x['ciqual_code']: x for x in agribalyse_impacts}

    with open(FCEN_DATA_FILEPATH, 'r', encoding='utf8') as file:
        fcen_data = json.load(file)

    try:
        with open(INGREDIENTS_DATA_FILEPATH, 'r', encoding='utf8') as file:
            ingredients_data = json.load(file)
    except FileNotFoundError:
        ingredients_data = dict()

    graph = having_a_table_with_OFF_direct_and_Gustave_links.main()

    ############# CIQUAL
    # Looping on all ing to append ciqual data to off ingredients
    for ingredient_off, information_ingredient_off in tqdm(graph.items()):
        if ingredient_off in ingredients_data:
            ingredient = ingredients_data[ingredient_off]
        else:
            ingredient = {'id': ingredient_off}

        ingredient['nutritional_data_sources'] = []
        nutriments = dict()

        # Looping on ciqual products related to this off ingredient
        ciqual_ids = graph[ingredient_off]["ciqual_food_code"]
        for ciqual_food_code_off in ciqual_ids:
            if ciqual_food_code_off in CODES_CIQUAL_IN_OFF_REPLACED_BY_OTHER_CODE.keys():
                ciqual_ids.remove(ciqual_food_code_off)
                ciqual_ids.append(CODES_CIQUAL_IN_OFF_REPLACED_BY_OTHER_CODE[ciqual_food_code_off])
        if len(ciqual_ids) == 0:
            continue
        elif len(ciqual_ids) == 1:
            ciqual_product = ciqual_data[str(ciqual_ids[0])]
            ciqual_nutriments = ciqual_product['nutriments']

            ingredient['nutritional_data_sources'].append({'database': 'ciqual',
                                                           'entry': ciqual_product['alim_nom_eng'], 'mapping_direct' : graph[ingredient_off]["mapping_direct"]})

            # Getting minimum and maximum value for each nutriment
            # If they are not present, uses the confidence code to deduce it from the reference value
            # If there is no confidence code, use default error margin of 10%
            for nutriment_name in ciqual_nutriments:
                if (ciqual_nutriments[nutriment_name].get('value') is None) and \
                        (ciqual_nutriments[nutriment_name].get('min') is None):
                    continue

                value = ciqual_nutriments[nutriment_name].get('value')

                if 'min' in ciqual_nutriments[nutriment_name]:
                    min_value = ciqual_nutriments[nutriment_name]['min']
                else:
                    min_value = value

                if 'max' in ciqual_nutriments[nutriment_name]:
                    max_value = ciqual_nutriments[nutriment_name]['max']
                else:
                    max_value = value

                max_value = min(max_value, 100) if nutriment_name != 'energy-kcal' else max_value

                # If value is undefined, take the middle value
                if (value is None) and ((min_value is not None) and (max_value is not None)):
                    value = (min_value + max_value) / 2

                nutriments[nutriment_name] = {'value': value, 'min': min_value, 'max': max_value}
        else:
            # If there are more than one ciqual product linked to this off ingredient,
            # compile the data of every ciqual product
            values = dict()
            min_values = dict()
            max_values = dict()
            for ciqual_id in ciqual_ids:
                ciqual_product = ciqual_data[str(ciqual_id)]

                ingredient['nutritional_data_sources'].append({'database': 'ciqual',
                                                               'entry': ciqual_product['alim_nom_eng'], 'mapping_direct' : graph[ingredient_off]["mapping_direct"]})

                for nutriment_name, nutriment_data in ciqual_product['nutriments'].items():
                    if (nutriment_data.get('value') is None) and (nutriment_data.get('min') is None):
                        continue

                    if nutriment_name not in values:
                        values[nutriment_name] = []
                        min_values[nutriment_name] = []
                        max_values[nutriment_name] = []

                    value = nutriment_data.get('value')

                    if 'min' in nutriment_data:
                        min_value = nutriment_data['min']
                    else:
                        min_value = value

                    if 'max' in nutriment_data:
                        max_value = nutriment_data['max']
                    else:
                        max_value = value

                    # If value is undefined, take the middle value
                    if (value is None) and ((min_value is not None) and (max_value is not None)):
                        value = (min_value + max_value) / 2

                    values[nutriment_name].append(value)
                    min_values[nutriment_name].append(min_value)
                    max_values[nutriment_name].append(min(max_value, 100)
                                                      if nutriment_name != 'energy-kcal'
                                                      else max_value)

            for nutriment_name in values.keys():
                if values[nutriment_name]:
                    nutriments[nutriment_name] = {'value': mean(values[nutriment_name]),
                                                  'min': min(min_values[nutriment_name]),
                                                  'max': max(max_values[nutriment_name])}

        if len(nutriments) > 0:
            # Add the nutriments dict to the ingredient
            ingredient['nutriments'] = nutriments

            # Adding the ingredient to the main result
            ingredients_data[ingredient_off] = ingredient

        ingredients_data[ingredient_off]['environmental_impact_data_sources'] = []
        for ciqual_id in ciqual_ids :
            if agribalyse_impacts.get(ciqual_id) :
                ingredients_data[ingredient_off]['environmental_impact_data_sources'].append({'database': 'agribalyse',
                                                                               'entry': agribalyse_impacts[ciqual_id].get('LCI_name')})

        if len(ingredients_data[ingredient_off]['environmental_impact_data_sources']) == 0:
            del(ingredients_data[ingredient_off]['environmental_impact_data_sources'])

    ########## FCEN
    # Looping on all links to append fcen data to off ingredients
    for off_id in graph.keys():
        if not(graph[off_id]['mapping_direct']):
            continue
        if 'fcen' in graph[off_id]['mapping_direct'] :
            if off_id in ingredients_data:
                ingredient = ingredients_data[off_id]
            else:
                ingredient = {'id': off_id}

            ingredient['nutritional_data_sources'] = []
            nutriments = dict()

            # Looping on fcen products related to this off ingredient
            fcen_ids = graph[off_id]['fcen_food_code']
            if len(fcen_ids) == 0:
                continue
            elif len(fcen_ids) == 1:

                fcen_product = fcen_data[str(fcen_ids[0])]

                ingredient['nutritional_data_sources'].append({'database': 'fcen',
                                                               'entry': fcen_product['FoodDescription'],
                                                              'mapping_direct' : graph[off_id]['mapping_direct']})

                fcen_nutriments = fcen_product['nutriments']

                # Getting minimum and maximum value for each nutriment using the standard deviation
                # The distribution of the nutriment amount is supposed to be normal and the minimum and maximum values are
                # defined as:
                # min/max = reference_value -/+ 2 * std_error
                # If no standard error is given, a default 10% margin is used

                # Getting minimum and maximum value for each nutriment
                # If they are not present, uses the reference value
                for nutriment_name in fcen_nutriments:
                    value = fcen_nutriments[nutriment_name]['value']
                    stdev = fcen_nutriments[nutriment_name]['stdev']

                    if not math.isnan(stdev):
                        min_value = value - (2 * stdev)
                        max_value = value + (2 * stdev)
                    else:
                        min_value = value
                        max_value = value

                    max_value = min(max_value, 100)

                    nutriments[nutriment_name] = {'value': value,
                                                  'min': min_value,
                                                  'max': max_value}

            else:
                # If there are more than one fcen product linked to this off ingredient,
                # compile the data of every fcen product
                values = dict()
                min_values = dict()
                max_values = dict()
                for fcen_id in fcen_ids:
                    fcen_product = fcen_data[str(fcen_id)]

                    ingredient['nutritional_data_sources'].append({'database': 'fcen',
                                                                   'entry': fcen_product['FoodDescription'],
                                                                   'mapping_direct' : graph[off_id]['mapping_direct'] })

                    for nutriment_name, nutriment_data in fcen_product['nutriments'].items():
                        if nutriment_name not in values:
                            values[nutriment_name] = []
                            min_values[nutriment_name] = []
                            max_values[nutriment_name] = []

                        value = nutriment_data['value']
                        stdev = nutriment_data['stdev']

                        if not math.isnan(stdev):
                            min_value = value - (2 * stdev)
                            max_value = value + (2 * stdev)
                        else:
                            min_value = value
                            max_value = value

                        values[nutriment_name].append(value)
                        min_values[nutriment_name].append(min_value)
                        max_values[nutriment_name].append(min(max_value, 100)
                                                          if nutriment_name != 'energy-kcal'
                                                          else max_value)

                for nutriment_name in values.keys():
                    if values[nutriment_name]:
                        nutriments[nutriment_name] = {'value': mean(values[nutriment_name]),
                                                      'min': min(min_values[nutriment_name]),
                                                      'max': max(max_values[nutriment_name])}

            if len(nutriments) > 0:
                # Add the nutriments dict to the ingredient
                ingredient['nutriments'] = nutriments

                # Adding the ingredient to the main result
                ingredients_data[off_id] = ingredient

    with open(INGREDIENTS_DATA_FILEPATH, 'w', encoding='utf8') as file:
        json.dump(ingredients_data, file, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()