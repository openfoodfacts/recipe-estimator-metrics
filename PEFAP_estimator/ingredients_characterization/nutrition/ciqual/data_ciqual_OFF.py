"""
With the mapping already done by OFF, we only know of 571 direct mappings. We want to give a ciqual code for other
ingredients, thanks their parents or children, which have a mapping. We are going to use the recursive algorithm in
order to visit all children (or parents) of an ingredient.
"""
import json

from ingredients_characterization.vars import CIQUAL_DATA_FILEPATH, ING_OFF_WITH_CIQUAL_FILEPATH, \
    AGRIBALYSE_DATA_FILEPATH


def all_children(list_all_children, list_children_to_do, all_ing):
    ing = list_children_to_do[0]
    list_children_to_do.remove(ing)
    if all_ing.get(ing):
        list_children = all_ing[ing].get("children")
        if list_children:
            for child in list_children:
                list_all_children.append(child)
                list_children_to_do.append(child)
                a = 0
    if len(list_children_to_do) > 0:
        all_children(list_all_children, list_children_to_do, all_ing)

    return list(set(list_all_children))


def all_parents(list_all_parents, list_parents_to_do, all_ing):
    ing = list_parents_to_do[0]
    list_parents = all_ing[ing].get("parents")
    list_parents_to_do.remove(ing)
    if list_parents:
        for parent in list_parents:
            list_all_parents.append(parent)
            list_parents_to_do.append(parent)
    if len(list_parents_to_do) > 0:
        all_parents(list_all_parents, list_parents_to_do, all_ing)
    return list(set(list_all_parents))


def one_generation(parents_or_children, ingredient, all_ing):
    ing = ingredient[0]
    list_generation = all_ing[ing].get(parents_or_children)
    list_one_generation = []
    if list_generation:
        for generation in list_generation:
            list_one_generation.append(generation)
    return list(set(list_one_generation))


def recursive_dfs(graph, node, parents_or_children="children", visited=None, codes_ciqual=None):
    if visited is None:
        visited = []
    if codes_ciqual is None:
        codes_ciqual = []
    if node not in visited:
        visited.append(node)
    ciqual_food_code = graph[node]['ciqual_food_code']
    if ciqual_food_code:
        if list(ciqual_food_code) == ciqual_food_code:
            for one_ciqual_code in ciqual_food_code:
                codes_ciqual.append(one_ciqual_code)
        else:
            codes_ciqual.append(ciqual_food_code)
        # graph[node]['ciqual_food_code'].append(ciqual_food_code)
        unvisited = []
    else:
        unvisited = [n for n in graph[node][parents_or_children] if n not in visited and n in graph.keys()]
    for node in unvisited:
        recursive_dfs(graph, node, parents_or_children, visited, codes_ciqual)
    return graph, visited, list(set(codes_ciqual))


def main():
    with open(ING_OFF_WITH_CIQUAL_FILEPATH, 'r', encoding='utf8') as file:
        ing = json.load(file)

    with open(CIQUAL_DATA_FILEPATH, 'r', encoding='utf8') as file:
        ciqual_data = json.load(file)

    with open(AGRIBALYSE_DATA_FILEPATH, 'r', encoding='utf8') as file:
        agribalyse_impacts = json.load(file)
    agribalyse_impacts = {x['ciqual_code']: x for x in agribalyse_impacts}

    graph = {x: {"parents": one_generation("parents", [x], ing), "children": one_generation("children", [x], ing),
                 "ciqual_food_code": ing[x].get("ciqual_food_code", {"en": []})['en'],
                 "mapping_direct": True if ing[x].get("ciqual_food_code", {"en": []})['en'] != [] else False} for x in
             ing}
    ingredients_in_graph = list(graph.keys())
    for ingredient in ingredients_in_graph:
        parents = graph[ingredient].get('parent', [])
        children = graph[ingredient].get('children', [])
        for parent in parents:
            if parent not in ingredients_in_graph:
                if parent not in graph.keys():
                    graph[parent] = {"parents": one_generation("parents", [parent], ing),
                                     "children": one_generation("children", [parent], ing),
                                     "ciqual_food_code": ing[parent].get("ciqual_food_code", {"en": []})['en']}
                else:
                    graph[parent]["children"].append(ingredient)
        for child in children:
            if child not in ingredients_in_graph:
                if child not in graph.keys():
                    if child in ingredients_in_graph:
                        graph[child] = {"parents": one_generation("parents", [child], ing),
                                        "children": one_generation("children", [child], ing),
                                        "ciqual_food_code": ing[child].get("ciqual_food_code", {"en": []})['en']}
                    else:
                        graph[child] = {"parents": [ingredient], "children": [],
                                        "ciqual_food_code": []}
                else:
                    graph[child]['parents'].append(ingredient)

    # for the water
    graph['en:water']['ciqual_food_code'] = '18066'
    graph['en:water']['mapping_direct'] = True

    # graph = {}
    # graph["1"] = {"parents": [], "children": ["2", "3"], "ciqual_food_code": []}
    # graph["2"] = {"parents": ["1"], "children": ["4","5"], "ciqual_food_code": ["B"]}
    # graph["3"] = {"parents": ["1"], "children": ["5","6","7"], "ciqual_food_code": []}
    # graph["4"] = {"parents": ["2"], "children": ["8","9"], "ciqual_food_code": []}
    # graph["5"] = {"parents": ["2","3"], "children": [], "ciqual_food_code": []}
    # graph["6"] = {"parents": ["3"], "children": ["10"], "ciqual_food_code": []}
    # graph["7"] = {"parents": ["3"], "children": [], "ciqual_food_code": ["C"]}
    # graph["8"] = {"parents": ["4"], "children": [], "ciqual_food_code": ["D"]}
    # graph["9"] = {"parents": ["4"], "children": ["11","12"], "ciqual_food_code": []}
    # graph["10"] = {"parents": ["6"], "children": [], "ciqual_food_code": ["E"]}
    # graph["11"] = {"parents": ["9"], "children": [], "ciqual_food_code": ["F"]}
    # graph["12"] = {"parents": ["9"], "children": [], "ciqual_food_code": ["G"]}

    nb_with_children_or_parents_without_ciqual = len(graph)
    nb_with_children_or_parents_without_ciqual_before = len(graph) + 1
    while nb_with_children_or_parents_without_ciqual < nb_with_children_or_parents_without_ciqual_before:
        graph_sorted = sorted(graph.items(), key=lambda kv: len(kv[1]['children']))
        for node, node_item in graph_sorted:
            graph, visited, codes_ciqual = recursive_dfs(graph, node, "children")
            graph[node]["ciqual_food_code"] = codes_ciqual

        nb_with_children_or_parents_without_ciqual_before = nb_with_children_or_parents_without_ciqual
        nb_with_children_or_parents_without_ciqual = len([x for x in graph.items() if
                                                          len(x[1]["ciqual_food_code"]) == 0 and len(
                                                              x[1]["parents"]) > 0 and len(x[1]["children"]) > 0])

    nb_with_children_or_parents_without_ciqual = len(graph)
    nb_with_children_or_parents_without_ciqual_before = len(graph) + 1
    while nb_with_children_or_parents_without_ciqual < nb_with_children_or_parents_without_ciqual_before:
        graph_sorted = sorted(graph.items(), key=lambda kv: len(kv[1]['parents']))
        for node, node_item in graph_sorted:
            graph, visited, codes_ciqual = recursive_dfs(graph, node, "parents")
            graph[node]["ciqual_food_code"] = codes_ciqual
        nb_with_children_or_parents_without_ciqual_before = nb_with_children_or_parents_without_ciqual
        nb_with_children_or_parents_without_ciqual = len([x for x in graph.items() if
                                                          len(x[1]["ciqual_food_code"]) == 0 and len(
                                                              x[1]["parents"]) > 0 and len(x[1]["children"]) > 0])

    nb_with_children_or_parents_without_ciqual = len(graph)
    nb_with_children_or_parents_without_ciqual_before = len(graph) + 1
    while nb_with_children_or_parents_without_ciqual < nb_with_children_or_parents_without_ciqual_before:
        graph_sorted = sorted(graph.items(), key=lambda kv: len(kv[1]['children']))
        for node, node_item in graph_sorted:
            graph, visited, codes_ciqual = recursive_dfs(graph, node, "children")
            graph[node]["ciqual_food_code"] = codes_ciqual

        graph_sorted = sorted(graph.items(), key=lambda kv: len(kv[1]['parents']))
        for node, node_item in graph_sorted:
            graph, visited, codes_ciqual = recursive_dfs(graph, node, "parents")
            graph[node]["ciqual_food_code"] = codes_ciqual
        nb_with_children_or_parents_without_ciqual_before = nb_with_children_or_parents_without_ciqual
        nb_with_children_or_parents_without_ciqual = len([x for x in graph.items() if
                                                          len(x[1]["ciqual_food_code"]) == 0 and len(
                                                              x[1]["parents"]) > 0 and len(x[1]["children"]) > 0])
    return graph


if __name__ == '__main__':
    main()