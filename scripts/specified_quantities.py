#!/usr/bin/python3
"""
Get the quantities of ingredients used for 100 g of finished product that are specified on the label,
and match them to the ingredients of the ingredients list.

e.g. "Viande de porc (140g pour 100g de produit)", "Préparé avec 76g de fruits pour 100g de produit fini",
"145g de viande de porc utilisée pour 100g de produit fini"

Those quantities are different from specified percents: for products that lost water (e.g. dried meats, jams),
more than 100 g of ingredients can be used to make 100 g of product. They correspond to the quantity_estimate
of the models (quantity before water loss), and not to the percent_estimate.

Product Opener stores them in 2 places:
- quantity_g of an ingredient of the ingredients list: "Viande de Porc (140g pour 100g de produit)".
  quantity_g can also be a quantity without "per 100 g" (e.g. "farine de riz 52,8g"), which we do not use,
  so we check that the ingredients text contains the quantity followed by "per 100 g".
- specific_ingredients: mentions after the ingredients list ("Préparé avec 76g de fruits pour 100g de produit fini").
  A specific ingredient can correspond to several ingredients of the list (e.g. fruits: pineapple and tangor),
  which we find with the ingredients taxonomy (taxonomies/ingredients.json, copied from Product Opener),
  or by matching the text of the ingredients.

Used by:
- compute_metrics.py to compare specified quantities to the quantity_estimate of the models

Usage (prints the specified quantities found for each product of the test sets):

./scripts/specified_quantities.py test-sets/input/water-loss-processed-meat
"""

import json
import os
import re
import sys
import unicodedata

taxonomy_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "taxonomies", "ingredients.json")
_parents = None
_ids_by_name = None


def load_taxonomy():
    # Load the parents of each ingredient and an index of names from the taxonomy, if available
    global _parents, _ids_by_name
    if _parents is None:
        _parents = {}
        _ids_by_name = {}
        if os.path.exists(taxonomy_path):
            with open(taxonomy_path, "r") as f:
                taxonomy = json.load(f)
            for ingredient_id, entry in taxonomy.items():
                _parents[ingredient_id] = entry.get("parents", [])
                for name in (entry.get("name") or {}).values():
                    _ids_by_name.setdefault(singular(normalize(name)), ingredient_id)
        else:
            print(f"Warning: {taxonomy_path} not found, specific ingredients will only be matched by text", file=sys.stderr)


def get_parents():
    load_taxonomy()
    return _parents


def get_id_by_name(name):
    load_taxonomy()
    return _ids_by_name.get(singular(normalize(name)))


def is_a(ingredient_id, parent_id):
    """Return True if ingredient_id is parent_id or one of its descendants in the taxonomy"""
    parents = get_parents()
    seen = set()
    to_visit = [ingredient_id]
    while to_visit:
        current_id = to_visit.pop()
        if current_id == parent_id:
            return True
        if current_id in seen:
            continue
        seen.add(current_id)
        to_visit.extend(parents.get(current_id, []))
    return False


def normalize(text):
    # lowercase, without accents, with only letters and spaces
    text = unicodedata.normalize("NFD", (text or "").lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z]+", " ", text).split())


def singular(text):
    # crude singular for French and English names: "fruits" -> "fruit"
    return " ".join(word[:-1] if len(word) > 3 and word.endswith("s") else word for word in text.split())


def clean_specific_ingredient_name(name):
    # "fruits pour 100g de sirop" -> "fruits", "viande de porc mis en oeuvre" -> "viande de porc"
    name = re.split(r"\(|\d|\b(?:pour|per|for|mise? en \S{0,2}uvre|utilis[ée]+s?|used|ont été|a été|have been|has been)\b", name, flags=re.IGNORECASE)[0]
    # "raw turkey" -> "turkey", "viande crue" -> "viande"
    name = re.sub(r"\b(?:raw|fresh|crue?s?|fra[iî]che?s?)\b", " ", name, flags=re.IGNORECASE)
    return " ".join(name.split()).strip(" -:,.")


def quantity_regex(quantity_g):
    # 47.5 -> 47[,.]5 so that we can match "47,5 g" and "47.5g"
    number = ("%g" % quantity_g).replace(".", "[,.]")
    return rf"(?<![\d,.]){number} ?g\b"


per_100g_regex = r"(?:pour|per|for|/) ?100 ?g"
prepared_with_regex = r"préparée? avec|élaborée? avec|prepared with|made with|utilisée? pour|used (?:for|per)"
# Mentions of nutrient contents, which are not quantities of ingredients
nutrient_content_regex = r"biologique|organic|en sucres|sucres totaux|sugars? content|total sugars?|teneur en sel|salt content|teneur en mati[eè]res? grasses?|fat content"


def walk_with_paths(ingredients, path=()):
    for i, ingredient in enumerate(ingredients or []):
        yield path + (i,), ingredient
        yield from walk_with_paths(ingredient.get("ingredients"), path + (i,))


def get_ingredient_by_path(ingredients, path):
    ingredient = None
    for i in path:
        if not ingredients or i >= len(ingredients):
            return None
        ingredient = ingredients[i]
        ingredients = ingredient.get("ingredients")
    return ingredient


def match_specific_ingredient(ingredients, specific_ingredient):
    """Return the paths of the top-most ingredients of the list that correspond to the specific ingredient"""
    specific_name = clean_specific_ingredient_name(specific_ingredient.get("ingredient") or specific_ingredient.get("id", "").split(":")[-1].replace("-", " "))
    specific_id = specific_ingredient.get("id")
    # Specific ingredients that are not in the taxonomy (e.g. "fr:fruits-pour-100g-de-sirop"): look for the cleaned name
    if specific_id not in get_parents():
        specific_id = get_id_by_name(specific_name)
    # 1. With the taxonomy: the ingredient is the specific ingredient or one of its descendants
    # The taxonomy has separate entries for animals and their meat (e.g. en:pork and en:pork-meat), we accept both
    specific_ids = [specific_id] if specific_id else []
    if specific_id and specific_id + "-meat" in get_parents():
        specific_ids.append(specific_id + "-meat")
    paths = []
    for path, ingredient in walk_with_paths(ingredients):
        if any(path[:len(matched_path)] == matched_path for matched_path in paths):
            continue
        if any(is_a(ingredient.get("id", ""), matched_id) for matched_id in specific_ids):
            paths.append(path)
    if paths:
        return paths
    # 2. With the text: the specific ingredient name contains the ingredient text
    # e.g. "viande de porc utilisee" contains "viande de porc"
    specific_name = normalize(specific_name)
    best_path = None
    best_length = 0
    for path, ingredient in walk_with_paths(ingredients):
        ingredient_text = normalize(ingredient.get("text"))
        if len(ingredient_text) >= 4 and re.search(r"\b" + re.escape(ingredient_text) + r"\b", specific_name):
            # Longest match, top-most ingredient for equal lengths
            if len(ingredient_text) > best_length:
                best_path = path
                best_length = len(ingredient_text)
    if best_path:
        return [best_path]
    # 3. With the text: the ingredient text contains the specific ingredient name
    # e.g. "viande de cuisses de poulet" contains "viande", "british beef brisket" contains "beef"
    paths = []
    if len(specific_name) >= 4:
        for path, ingredient in walk_with_paths(ingredients):
            if any(path[:len(matched_path)] == matched_path for matched_path in paths):
                continue
            if re.search(r"\b" + re.escape(specific_name) + r"\b", singular(normalize(ingredient.get("text")))) or re.search(r"\b" + re.escape(specific_name) + r"\b", normalize(ingredient.get("text"))):
                paths.append(path)
    return paths


def get_specified_quantities(product):
    """Return the list of specified quantities used for 100g of product:
    [{"id", "text", "quantity_g", "source", "paths"}], paths being the paths of the matched ingredients in the ingredients list
    (empty list if we could not match the quantity to ingredients)"""
    ingredients = product.get("ingredients") or []
    ingredients_text = product.get("ingredients_text") or ""
    specified_quantities = []

    # 1. Quantities of ingredients of the list, followed by "per 100 g" in the ingredients text
    for path, ingredient in walk_with_paths(ingredients):
        quantity_g = ingredient.get("quantity_g")
        if not isinstance(quantity_g, (int, float)) or quantity_g <= 0 or "percent" in ingredient:
            continue
        # Exclude parsing errors like "NUTRITION DECLARATION PER 100 g"
        if not ingredient.get("is_in_taxonomy"):
            continue
        if not re.search(quantity_regex(quantity_g) + r"[^,;)]{0,60}?" + per_100g_regex, ingredients_text, re.IGNORECASE):
            continue
        specified_quantities.append({
            "id": ingredient["id"],
            "text": ingredient.get("text"),
            "quantity_g": quantity_g,
            "source": "ingredients",
            "paths": [path],
        })

    # 2. Specific ingredients mentioned after the ingredients list
    seen = set((normalize(clean_specific_ingredient_name(quantity["text"] or "")), quantity["quantity_g"]) for quantity in specified_quantities)
    for specific_ingredient in product.get("specific_ingredients") or []:
        text = specific_ingredient.get("text") or ""
        if re.search(nutrient_content_regex, text, re.IGNORECASE):
            continue
        quantity_g = specific_ingredient.get("quantity_g")
        if not isinstance(quantity_g, (int, float)):
            # "Préparé avec 50% de fruits pour 100 g": the percent is a quantity per 100 g
            percent = specific_ingredient.get("percent")
            if isinstance(percent, (int, float)) and (re.search(per_100g_regex, text, re.IGNORECASE) or re.search(prepared_with_regex, text, re.IGNORECASE)):
                quantity_g = percent
        if not isinstance(quantity_g, (int, float)) or quantity_g <= 0:
            continue
        # The same mention can be listed twice with different ids (e.g. "fr:viande-de-porc" and "fr:viande de porc")
        key = (normalize(clean_specific_ingredient_name(specific_ingredient.get("ingredient") or specific_ingredient.get("id", ""))), quantity_g)
        if key in seen:
            continue
        seen.add(key)
        specified_quantities.append({
            "id": specific_ingredient.get("id"),
            "text": text,
            "quantity_g": quantity_g,
            "source": "specific_ingredients",
            "paths": match_specific_ingredient(ingredients, specific_ingredient),
        })

    return specified_quantities


def hide_specified_quantities(product):
    """Hide specified quantities from the models, as they are compared to the quantity_estimate of the models.
    Like percent fields that are moved to percent_hidden, we keep a copy in *_hidden fields."""
    for _, ingredient in walk_with_paths(product.get("ingredients")):
        for field in ["quantity", "quantity_g", "quantity_ml"]:
            if field in ingredient:
                ingredient[field + "_hidden"] = ingredient.pop(field)
    if "specific_ingredients" in product:
        product["specific_ingredients_hidden"] = product.pop("specific_ingredients")
    return product


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: specified_quantities.py [paths of one or more input test sets]")
        sys.exit(1)

    for test_set_path in sys.argv[1:]:
        products_n = 0
        products_with_quantities_n = 0
        quantities_n = 0
        unmatched_n = 0
        for file_name in sorted(os.listdir(test_set_path)):
            if not file_name.endswith(".json"):
                continue
            with open(os.path.join(test_set_path, file_name), "r") as f:
                product = json.load(f)
            products_n += 1
            specified_quantities = get_specified_quantities(product)
            if not specified_quantities:
                continue
            products_with_quantities_n += 1
            print(f"{product.get('code')}: {(product.get('ingredients_text') or '')[:150]}")
            for quantity in specified_quantities:
                quantities_n += 1
                matched = [get_ingredient_by_path(product["ingredients"], path).get("id") for path in quantity["paths"]]
                if not matched:
                    unmatched_n += 1
                print(f"    {quantity['quantity_g']} g {quantity['id']} ({quantity['source']}: {quantity['text']}) -> {matched or 'NOT MATCHED'}")
        print(f"\n{test_set_path}: {products_with_quantities_n} products with specified quantities out of {products_n}, {quantities_n} quantities, {unmatched_n} not matched")
