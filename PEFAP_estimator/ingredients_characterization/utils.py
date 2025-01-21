"""
the explanation of all the algorithm is written in documentation
"""

def recursive_dfs(graph, node, parents_or_children="children", fcen_or_ciqual ='ciqual', visited=None, codes_ciqual=None):
    """algorithm of Breadth First Search"""
    if visited is None:
        visited = []
    if codes_ciqual is None:
        codes_ciqual = []
    if node not in visited:
        visited.append(node)
    ciqual_food_code = graph[node].get(f'{fcen_or_ciqual}_food_code')
    if ciqual_food_code and ciqual_food_code != [[]]:
        if list(ciqual_food_code) == ciqual_food_code:
            for one_ciqual_code in ciqual_food_code:
                codes_ciqual.append(one_ciqual_code)
        else:
            codes_ciqual.append(ciqual_food_code)
        unvisited = []
    else:
        unvisited = [n for n in graph[node][parents_or_children] if n not in visited and n in graph.keys()]
    for node in unvisited:
        recursive_dfs(graph, node, parents_or_children, fcen_or_ciqual, visited, codes_ciqual)
    if codes_ciqual == [[]] : return  graph, visited, []
    return graph, visited, list(set(codes_ciqual))

def one_generation(parents_or_children, ingredient, all_ing):
    """

    Args:
        parents_or_children: we are looking for the direct parents or direct children of an ingredient
        ingredient: the ingredient
        all_ing: graph of all ingredients

    Returns: list of all parents (or children) direct of the ingredient

    """
    ing = ingredient[0]
    list_generation = all_ing[ing].get(parents_or_children)
    list_one_generation = []
    if list_generation:
        for generation in list_generation:
            list_one_generation.append(generation)
    return list(set(list_one_generation))


def recursive_to_complete_codes_parents_or_children(graph, parents_or_children = "children", fcen_or_ciqual ='ciqual' ) :
    """
    using recursive_dfs, we complete the graph with the mapping. If parents_or_children="children",
    we take into account only children, else we use the parents
    """
    if fcen_or_ciqual == 'ciqual' : ORIGIN = 'parents_children_proxy'
    else : ORIGIN = 'manual_entry'
    nb_with_children_or_parents_without_code = len(graph)
    nb_with_children_or_parents_without_code_before = len(graph)+1
    while nb_with_children_or_parents_without_code < nb_with_children_or_parents_without_code_before:
        graph_sorted = sorted(graph.items(), key=lambda kv: len(kv[1][parents_or_children]))
        for node, node_item in graph_sorted:
            graph, visited, codes = recursive_dfs(graph, node, parents_or_children,fcen_or_ciqual)
            if codes != [] and not (graph[node]['mapping_direct']):
                graph[node][f"{fcen_or_ciqual}_food_code"] = codes
                graph[node]['mapping_direct'] = ORIGIN

        nb_with_children_or_parents_without_code_before = nb_with_children_or_parents_without_code
        nb_with_children_or_parents_without_code = len([x for x in graph.items() if
                                                          len(x[1].get(f"{fcen_or_ciqual}_food_code",[])) == 0 and len(
                                                              x[1]["parents"]) > 0 and len(x[1]["children"]) > 0])
    return graph



def recursive_to_complete_codes_parents_AND_children(graph, fcen_or_ciqual ='ciqual' ) :
    """
    using recursive_dfs, we complete the graph with the mapping. we look the parents and after the children
    """
    if fcen_or_ciqual == 'ciqual':
        ORIGIN = 'parents_children_proxy'
    else:
        ORIGIN = 'manual_entry'
    nb_with_children_or_parents_without_code = len(graph)
    nb_with_children_or_parents_without_code_before = len(graph)+1
    while nb_with_children_or_parents_without_code < nb_with_children_or_parents_without_code_before:
        graph_sorted = sorted(graph.items(), key=lambda kv: len(kv[1]['children']))
        for node, node_item in graph_sorted:
            graph, visited, codes = recursive_dfs(graph, node, "children", fcen_or_ciqual)
            if codes != [] and not (graph[node]['mapping_direct']):
                graph[node][f"{fcen_or_ciqual}_food_code"] = codes
                graph[node]['mapping_direct'] = ORIGIN

        graph_sorted = sorted(graph.items(), key=lambda kv: len(kv[1]['parents']))
        for node, node_item in graph_sorted:
            graph, visited, codes = recursive_dfs(graph, node, "parents", fcen_or_ciqual)
            if codes != [] and not (graph[node]['mapping_direct']):
                graph[node][f"{fcen_or_ciqual}_food_code"] = codes
                graph[node]['mapping_direct'] = ORIGIN

        nb_with_children_or_parents_without_code_before = nb_with_children_or_parents_without_code
        nb_with_children_or_parents_without_code = len([x for x in graph.items() if
                                                        len(x[1].get(f"{fcen_or_ciqual}_food_code",[])) == 0 and len(
                                                            x[1]["parents"]) > 0 and len(x[1]["children"]) > 0])
    return graph

def recursive_to_complete_codes_parents_children(graph,fcen_or_ciqual ='ciqual' ) :
    """
    Args:
        graph: OFF_id and informations about mapping (codes ciqual or fcen)
        fcen_or_ciqual: what codes are we using ?
    Returns:
        graph with new mappings

    """
    graph_step1 = recursive_to_complete_codes_parents_or_children(graph, "children", fcen_or_ciqual )
    graph_step2 = recursive_to_complete_codes_parents_or_children(graph_step1, "parents", fcen_or_ciqual )
    graph_step3 = recursive_to_complete_codes_parents_AND_children(graph_step2, fcen_or_ciqual)
    return graph_step3

