import json
import os

import pandas as pd

from data import INGREDIENTS_DATA_FILEPATH
from ingredients_characterization.nutrition.ciqual import data_ciqual_OFF

from ingredients_characterization.vars import ING_OFF_WITH_CIQUAL_FILEPATH, CIQUAL_OFF_LINKING_TABLE_FILEPATH, \
    CIQUAL_DATA_FILEPATH

with open(ING_OFF_WITH_CIQUAL_FILEPATH, 'r', encoding='utf8') as file:
    ing = json.load(file)

with open(CIQUAL_DATA_FILEPATH, 'r', encoding='utf8') as file:
    ciqual_data = json.load(file)
CODES_CIQUAL_IN_OFF_REPLACED_BY_OTHER_CODE = {'26132': '26210', '7430': '7432', '13082': '13024'}

links = pd.read_csv(CIQUAL_OFF_LINKING_TABLE_FILEPATH)
graph = data_ciqual_OFF.main()
ingredient_unique = links['OFF_ID'].unique()
result = []
for ingredient_u in  ingredient_unique:
    ingredient = {"OFF_ID": ingredient_u}
    ingredient_off = ingredient['OFF_ID'].lower()

    CIQUAL_INDEX_FR = links[links['OFF_ID'] == ingredient_u]['CIQUAL_INDEX_FR']
    ingredient['CIQUAL_INDEX_GUSTAVE'] = []
    ingredient['CIQUAL_INDEX_GUSTAVE_CODE'] =[f"{x}" for x in links[links['OFF_ID'] == ingredient_u]['CIQUAL_ID'].values]
    for ciqual_code in ingredient['CIQUAL_INDEX_GUSTAVE_CODE']:
        if ciqual_data.get(str(ciqual_code), 'nan') != 'nan':
            ingredient['CIQUAL_INDEX_GUSTAVE'].append(ciqual_data[str(ciqual_code)].get('alim_nom_fr'))
    if len(ingredient['CIQUAL_INDEX_GUSTAVE']) == 1:
        ingredient['CIQUAL_INDEX_GUSTAVE'] = ingredient['CIQUAL_INDEX_GUSTAVE'][0]

    ingredient['CIQUAL_FOOD_CODE_OFF'] = {}
    ingredient['CIQUAL_FOOD_CODE_OFF']['OFF mapping direct code'] = ""
    if ingredient_off in graph.keys() :
        if ingredient_off in ing :
            ciqual = ing[ingredient_off].get("ciqual_food_code")
            if ciqual != None :
                ingredient['CIQUAL_FOOD_CODE_OFF']['OFF mapping direct code'] = ciqual['en']
                if ciqual_data.get(str(ciqual['en']), 'nan') != 'nan':
                    ingredient['CIQUAL_FOOD_CODE_OFF']['OFF mapping direct'] = ciqual_data[str(ciqual['en'])].get('alim_nom_fr')
                else :
                    ingredient['CIQUAL_FOOD_CODE_OFF']['OFF mapping direct'] = ciqual_data[CODES_CIQUAL_IN_OFF_REPLACED_BY_OTHER_CODE[str(ciqual['en'])]].get('alim_nom_fr')

        ingredient['CIQUAL_FOOD_CODE_OFF']['OFF mapping graph'] = [x for x in graph[ingredient_off]['ciqual_food_code'] if x not in [ingredient['CIQUAL_FOOD_CODE_OFF'].get('OFF mapping direct code',[])]]
        CIQUAL_FOOD_CODE_OFF_WITH_GRAPH = ingredient['CIQUAL_FOOD_CODE_OFF']['OFF mapping graph']
        ingredient['CIQUAL_FOOD_CODE_OFF']['OFF mapping graph id'] = []
        for ciqual_food_code in ingredient['CIQUAL_FOOD_CODE_OFF']['OFF mapping graph']:
            if ciqual_data.get(str(ciqual_food_code), 'nan') != 'nan' :
                ingredient['CIQUAL_FOOD_CODE_OFF']['OFF mapping graph id'].append(
                    ciqual_data[ciqual_food_code].get('alim_nom_fr'))
        if len(ingredient['CIQUAL_FOOD_CODE_OFF']['OFF mapping graph id']) == 1:
            ingredient['CIQUAL_FOOD_CODE_OFF']['OFF mapping graph id'] = ingredient['CIQUAL_FOOD_CODE_OFF']['OFF mapping graph id'][0]
    result.append(ingredient)
df = pd.DataFrame(result)
df.to_csv('ingredient_in_linkind_table_without_ciqual_OFF.csv', index=False)

nb_mapper_avec_gustave = 0
nb_mapper_avec_OFF_graph = 0
nb_mapper_deux_fois = 0
nb_mapper_deux_fois_G_inOFF = 0
nb_mapper_deux_fois_identiques = 0
mapper_OFF_Gustave = 0
ing_mappes_OFF_direct_G_diff = []
ing_mappes_OFF_parents_enf_G_in = []
ing_mappes_G = []
ing_mappes_OFF_direct_G_same = []
ing_mappes_OFF = []
for ingredient in graph.keys() :
    mapper_avec_G = False
    mapper_avec_OFF = False
    if ingredient in ingredient_unique :
        nb_mapper_avec_gustave = nb_mapper_avec_gustave+1
        mapper_avec_G = True
        ing_mappes_G.append(ingredient)
    if len(graph[ingredient]['ciqual_food_code']) != 0 :
        nb_mapper_avec_OFF_graph = nb_mapper_avec_OFF_graph+1
        mapper_avec_OFF = True
    if (graph[ingredient].get('mapping_direct')) == True:
        ing_mappes_OFF.append(ingredient)
    if mapper_avec_G and mapper_avec_OFF :
        nb_mapper_deux_fois = nb_mapper_deux_fois +1
        if df[df['OFF_ID']==ingredient]['CIQUAL_FOOD_CODE_OFF'].values[0]['OFF mapping direct code'] == df[df['OFF_ID']==ingredient]['CIQUAL_INDEX_GUSTAVE_CODE'].values[0][0]:
            nb_mapper_deux_fois_identiques = nb_mapper_deux_fois_identiques+1
            ing_mappes_OFF_direct_G_same.append(ingredient)
        elif df[df['OFF_ID']==ingredient]['CIQUAL_FOOD_CODE_OFF'].values[0]['OFF mapping direct code'] != "":
            ing_mappes_OFF_direct_G_diff.append(ingredient)
        for ciqual_code in df[df['OFF_ID']==ingredient]['CIQUAL_INDEX_GUSTAVE_CODE'].values :
            if ciqual_code[0] in graph[ingredient]['ciqual_food_code'] :
                nb_mapper_deux_fois_G_inOFF = nb_mapper_deux_fois_G_inOFF+1
                if df[df['OFF_ID']==ingredient]['CIQUAL_FOOD_CODE_OFF'].values[0]['OFF mapping direct code'] != df[df['OFF_ID']==ingredient]['CIQUAL_INDEX_GUSTAVE_CODE'].values[0][0]:
                    ing_mappes_OFF_parents_enf_G_in.append(ingredient)
                pass
    if mapper_avec_G and ingredient in ing.keys() :
        if ing[ingredient].get('ciqual_food_code') :
            mapper_OFF_Gustave = mapper_OFF_Gustave +1
len(graph)

result_mappes_OFF_direct_G_diff = []
result_mappes_OFF_parents_enf_G_in = []
result_mappes_G = []
result_mappes_OFF_direct = []
for ingredient in ing_mappes_OFF_direct_G_diff:
    dic_ing = {}
    dic_ing["ingredient"] = ingredient
    dic_ing["mapping G code"] = df[df['OFF_ID']==ingredient]['CIQUAL_INDEX_GUSTAVE_CODE'].values[0]
    dic_ing["mapping G"] = df[df['OFF_ID'] == ingredient]['CIQUAL_INDEX_GUSTAVE'].values[0]
    dic_ing["mapping OFF direct code"] = df[df['OFF_ID']==ingredient]['CIQUAL_FOOD_CODE_OFF'].values[0]['OFF mapping direct code']
    dic_ing["mapping OFF direct"] = df[df['OFF_ID'] == ingredient]['CIQUAL_FOOD_CODE_OFF'].values[0].get('OFF mapping direct')
    result_mappes_OFF_direct_G_diff.append(dic_ing)

df_mappes_OFF_direct_G_diff = pd.DataFrame(result_mappes_OFF_direct_G_diff)
df_mappes_OFF_direct_G_diff.to_csv('result_mappes_OFF_direct_G_diff.csv', index=False)
result_mappes_OFF = []
for ingredient in ing_mappes_OFF:
    dic_ing = {}
    dic_ing["ingredient"] = ingredient
    ciqual = graph[ingredient]['ciqual_food_code']
    dic_ing["mapping OFF direct code"] = ciqual
    if ciqual_data.get((ciqual)[0], 'nan') != 'nan':
        dic_ing['OFF mapping direct'] = ciqual_data[ciqual[0]].get('alim_nom_fr')
    result_mappes_OFF.append(dic_ing)

df_mappes_OFF_direct = pd.DataFrame(result_mappes_OFF)
df_mappes_OFF_direct.to_csv('result_mappes_OFF.csv', index=False)

for ingredient in ing_mappes_OFF_parents_enf_G_in:
    dic_ing = {}
    dic_ing["ingredient"] = ingredient
    dic_ing["mapping G code"] = df[df['OFF_ID']==ingredient]['CIQUAL_INDEX_GUSTAVE_CODE'].values[0]
    dic_ing["mapping G"] = df[df['OFF_ID'] == ingredient]['CIQUAL_INDEX_GUSTAVE'].values[0]
    dic_ing["mapping OFF parents/enfants code"] = df[df['OFF_ID'] == ingredient]['CIQUAL_FOOD_CODE_OFF'].values[0][
        'OFF mapping graph']
    dic_ing["mapping OFF parents/enfants"] = df[df['OFF_ID'] == ingredient]['CIQUAL_FOOD_CODE_OFF'].values[0].get(
        'OFF mapping graph id')
    if 'OFF mapping direct code' in df[df['OFF_ID']==ingredient]['CIQUAL_FOOD_CODE_OFF'].values[0] :
        dic_ing["mapping OFF direct code"] = df[df['OFF_ID']==ingredient]['CIQUAL_FOOD_CODE_OFF'].values[0]['OFF mapping direct code']
        dic_ing["mapping OFF direct"] = df[df['OFF_ID'] == ingredient]['CIQUAL_FOOD_CODE_OFF'].values[0].get('OFF mapping direct')

    result_mappes_OFF_parents_enf_G_in.append(dic_ing)

df_mappes_OFF_parents_enf_G_in = pd.DataFrame(result_mappes_OFF_parents_enf_G_in)
df_mappes_OFF_parents_enf_G_in.to_csv('result_mappes_OFF_parents_enf_G_in.csv', index=False)

for ingredient in ing_mappes_G:
    if ingredient not in ing_mappes_OFF_parents_enf_G_in and ingredient not in ing_mappes_OFF_direct_G_diff and ingredient not in ing_mappes_OFF_direct_G_same:
        dic_ing = {}
        dic_ing["ingredient"] = ingredient
        dic_ing["mapping G code"] = df[df['OFF_ID'] == ingredient]['CIQUAL_INDEX_GUSTAVE_CODE'].values[0]
        dic_ing["mapping G"] = df[df['OFF_ID'] == ingredient]['CIQUAL_INDEX_GUSTAVE'].values[0]
        dic_ing["mapping OFF parents/enfants code"] = df[df['OFF_ID'] == ingredient]['CIQUAL_FOOD_CODE_OFF'].values[0][
            'OFF mapping graph']
        dic_ing["mapping OFF parents/enfants"] = df[df['OFF_ID'] == ingredient]['CIQUAL_FOOD_CODE_OFF'].values[0].get(
            'OFF mapping graph id')
        if 'OFF mapping direct code' in df[df['OFF_ID'] == ingredient]['CIQUAL_FOOD_CODE_OFF'].values[0]:
            dic_ing["mapping OFF direct code"] = df[df['OFF_ID'] == ingredient]['CIQUAL_FOOD_CODE_OFF'].values[0][
                'OFF mapping direct code']
            dic_ing["mapping OFF direct"] = df[df['OFF_ID'] == ingredient]['CIQUAL_FOOD_CODE_OFF'].values[0].get(
                'OFF mapping direct')

        result_mappes_G.append(dic_ing)

df_mappes_G = pd.DataFrame(result_mappes_G)
df_mappes_G.to_csv('result_mappes_G.csv', index=False)
a=0