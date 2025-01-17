"""
having a table and a graph with all mappings using algorithm parents/children (cf documentation)
"""

import copy
import json
import os

import pandas as pd
import bs4
import requests

from data import INGREDIENTS_DATA_FILEPATH, ingredients_data
from ingredients_characterization.utils import *
from ingredients_characterization.vars import  CIQUAL_OFF_LINKING_TABLE_FILEPATH, \
    CIQUAL_DATA_FILEPATH, FCEN_DATA_FILEPATH, FCEN_OFF_LINKING_TABLE_FILEPATH, MANUAL_SOURCES_NUTRITION_DATA_FILEPATH, \
    OFF_DUPLICATES_FILEPATH, AGRIBALYSE_DATA_FILEPATH

# with open(ING_OFF_WITH_CIQUAL_FILEPATH, 'r', encoding='utf8') as file:
#     ing = json.load(file)


with open(CIQUAL_DATA_FILEPATH, 'r', encoding='utf8') as file:
    ciqual_data = json.load(file)
ciqual_data_inverse = {x[1]['alim_nom_eng'] : x[1] for x in ciqual_data.items()}
CODES_CIQUAL_IN_OFF_REPLACED_BY_OTHER_CODE = {'26132': '26210', '7430': '7432', '13082': '13024'}

with open(FCEN_DATA_FILEPATH, 'r', encoding='utf8') as file:
    fcen_data = json.load(file)
USING_FCEN = True

with open(AGRIBALYSE_DATA_FILEPATH, 'r', encoding='utf8') as file:
    agribalyse_impacts = json.load(file)
agribalyse_impacts = {x['ciqual_AGB']: x for x in agribalyse_impacts}
#agribalyse_impacts_inverse = {x[1]['LCI_name'] : x[1] for x in agribalyse_impacts.items()}

url = "https://static.openfoodfacts.org/data/taxonomies/ingredients.json"
reponse = requests.get(url)
ing = (json.loads(reponse.text))
ing.pop("")

def main():
    graph = {x: {"parents": one_generation("parents", [x], ing), "children": one_generation("children", [x], ing),
                 "ciqual_food_code": [ing[x].get("ciqual_food_code", {"en": []})['en']] if ing[x].get(
                     "ciqual_food_code") else [],
                 "mapping_direct": "OFF_mapping" if ing[x].get("ciqual_food_code", {"en": []})['en'] != [] else False}
             for x in
             ing}

    # first step : having the 5400 ingredients + mapping direct in a graph
    # we add all the children which are not written
    ingredients_in_graph = list(graph.keys())
    for ingredient in ingredients_in_graph:
        children = graph[ingredient].get('children', [])
        for child in children:
            if child not in ingredients_in_graph:
                if child not in graph.keys():
                    graph[child] = {"parents": [ingredient], "children": [], "ciqual_food_code": [],
                                    "mapping_direct": False}
                else:
                    graph[child]['parents'].append(ingredient)

    # second step : for the ingredients which not having a direct mapping : add Gustave links
    links_ciqual = pd.read_csv(CIQUAL_OFF_LINKING_TABLE_FILEPATH)
    ingredient_unique_Gustave = links_ciqual['OFF_ID'].unique()
    for ingredient in ingredient_unique_Gustave:
        if ingredient in graph.keys():
            if not (graph[ingredient]['mapping_direct']):
                df_ingredient_link = links_ciqual[links_ciqual['OFF_ID'] == ingredient]
                ciqual_code_link = [str(x) for x in df_ingredient_link['CIQUAL_ID'].values]
                graph[ingredient]['ciqual_food_code'] = ciqual_code_link
                graph[ingredient]['mapping_direct'] = 'own_mapping'

    # third step : using recursive algorithm, find parents/children
    graph = recursive_to_complete_codes_parents_children(graph, 'ciqual')

    # fourth step : add Gustave duplicates
    duplicates = pd.read_csv(OFF_DUPLICATES_FILEPATH)
    duplicates.columns = ['OFF_ID', 'reference', 'proxy_type']
    ingredient_unique_Gustave_duplicates = duplicates['OFF_ID'].unique()
    for ingredient in ingredient_unique_Gustave_duplicates:
        if ingredient in graph.keys():
            duplicate = duplicates[duplicates['OFF_ID']==ingredient]
            proxy = copy.deepcopy(ingredients_data.get(duplicate.reference.values[0]))
            # add the nutrients duplicates
            if proxy and not(graph[ingredient]['mapping_direct']) and (duplicate.proxy_type.values[0] != 2) :
                if ('nutriments' in proxy) :
                    graph[ingredient]['mapping_direct'] = 'manual_proxy'
                    if ciqual_data_inverse.get(proxy['id']):
                        graph[ingredient]['ciqual_food_code'] = ciqual_data_inverse[proxy['id']]['alim_code']
                    else :
                        graph[ingredient]['ciqual_duplicate'] = proxy['id']
                elif duplicate.reference.values[0] in graph.keys():
                    if graph[duplicate.reference.values[0]]['ciqual_food_code']!= []:
                        graph[ingredient]['mapping_direct'] = 'manual_proxy'
                        graph[ingredient]['ciqual_food_code'] = graph[duplicate.reference.values[0]]['ciqual_food_code']
            #add the impact duplicates
            if proxy and (graph[ingredient]['mapping_direct']!="manual_proxy") and (duplicate.proxy_type.values[0] != 1) :
                if ('impacts' in proxy) :
                    graph[ingredient]['mapping_direct'] = 'manual_proxy'
                    if 'environmental_impact_data_sources' != []:
                        graph[ingredient]['impacts'] = proxy['id']
                        #graph[ingredient]['code_impacts'] = agribalyse_impacts_inverse[proxy['id']]

    # fifth step : for the ingredients which not having a mapping yet : add FCEN Gustave links
    # and use the algorithm parents/children
    if USING_FCEN:
        links_fcen = pd.read_csv(FCEN_OFF_LINKING_TABLE_FILEPATH)
        ingredient_unique_Gustave = links_fcen['OFF_ID'].unique()
        for ingredient in ingredient_unique_Gustave:
            if ingredient in graph.keys():
                if not (graph[ingredient]['mapping_direct']):
                    df_ingredient_link = links_fcen[links_fcen['OFF_ID'] == ingredient]
                    fcen_code_link = [str(x) for x in df_ingredient_link['FCEN_ID'].values]
                    graph[ingredient]['fcen_food_code'] = fcen_code_link
                    graph[ingredient]['mapping_direct'] = 'manual_entry'
        graph = recursive_to_complete_codes_parents_children(graph, 'fcen')

    # sixth step : add manual data
    manual_data = pd.read_csv(MANUAL_SOURCES_NUTRITION_DATA_FILEPATH)
    ingredient_unique_Gustave = manual_data['OFF_ID'].unique()
    for ingredient in ingredient_unique_Gustave:
        if ingredient in graph.keys():
            if not (graph[ingredient]['mapping_direct']):
                graph[ingredient]['mapping_direct'] = 'manual_entry'
                graph[ingredient]['COMMENT'] = manual_data[manual_data['OFF_ID']==ingredient].get('SOURCE').values[0]


    # creation of df
    result = []
    for ingredient, information in graph.items():
        res = {}
        res['OFF_ID'] = ingredient
        res['ORIGIN'] = information['mapping_direct']
        if res['ORIGIN']:
            if res['ORIGIN'] == 'manual_entry' :
                res['COMMENT'] = information.get('COMMENT')
                res['CODE_NUTRI'] = information.get('fcen_food_code','manual_entry')
                if res['CODE_NUTRI']!='manual_entry' :
                    res["NAME_NUTRI"] = []
                    res['COMMENT'] = 'fcen'
                    for fcen_code in res["CODE_NUTRI"]:
                        res['NAME_NUTRI'].append(fcen_data[fcen_code].get('FoodDescription'))

            elif res['ORIGIN'] == 'manual_proxy' :
                if graph[ingredient]['ciqual_food_code']!=[] :
                    res[f"NAME_NUTRI"] = []
                    res['CODE_IMPACT'] = []
                    res['NAME_IMPACT'] = []
                    for ciqual_code in information['ciqual_food_code']:
                        if ciqual_code in CODES_CIQUAL_IN_OFF_REPLACED_BY_OTHER_CODE:
                            ciqual_code = CODES_CIQUAL_IN_OFF_REPLACED_BY_OTHER_CODE[ciqual_code]
                        res[f"NAME_NUTRI"].append(ciqual_data[ciqual_code].get('alim_nom_eng'))
                        if agribalyse_impacts.get(ciqual_code) :
                            res['CODE_IMPACT'].append(ciqual_code)
                            if agribalyse_impacts[ciqual_code].get('LCI_name') :
                                res['NAME_IMPACT'].append(agribalyse_impacts[ciqual_code].get('LCI_name'))
                if graph[ingredient].get('impacts') :
                    res['NAME_IMPACT'] = graph[ingredient].get('impacts')
                    #res['CODE_IMPACT'] = graph[ingredient]['code_impacts']
                if  information.get('ciqual_duplicate'):
                    res["NAME_NUTRI"] = information['ciqual_duplicate']

            elif res['ORIGIN'] in ['OFF_mapping','own_mapping','parents_children_proxy'] :
                res['CODE_NUTRI'] = information['ciqual_food_code']
                res["NAME_NUTRI"] = []
                res['CODE_IMPACT'] = []
                res['NAME_IMPACT'] = []
                for ciqual_code in res["CODE_NUTRI"]:
                    if ciqual_code in CODES_CIQUAL_IN_OFF_REPLACED_BY_OTHER_CODE:
                        ciqual_code = CODES_CIQUAL_IN_OFF_REPLACED_BY_OTHER_CODE[ciqual_code]
                    res[f"NAME_NUTRI"].append(ciqual_data[ciqual_code].get('alim_nom_eng'))
                    if agribalyse_impacts.get(ciqual_code):
                        res['CODE_IMPACT'].append(ciqual_code)
                        if agribalyse_impacts[ciqual_code].get('LCI_name'):
                            res['NAME_IMPACT'].append(agribalyse_impacts[ciqual_code].get('LCI_name'))
            else:
                res['ATTENTION'] = 'ATTENTION'
        else :
            res['ORIGIN']='No_reference'
        result.append(res)

    df = pd.DataFrame(result)
    df.to_csv('Information_about_mapping.csv', index=False, sep = ';')

    return graph


if __name__ == '__main__':
    main()
