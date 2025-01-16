# this scripts takes the results from a one or more test runs and creates a database to help visualize the results

import argparse
import contextlib
import glob
import itertools
import json
import os

import duckdb


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        prog='create_db.py',
        description='Create a db for test reults exploration'
    )
    parser.add_argument("db_path", help="Path of the db file")
    parser.add_argument("results_path", nargs="*", help="Path to the results directory")
    result = parser.parse_args(args)
    return result


def test_name(results_path):
    return results_path.split('/')[-1]


def model_name(results_path):
    return results_path.split('/')[-2]


@contextlib.contextmanager
def test_db(db_path):
    with duckdb.connect(db_path) as conn:
        yield conn


def create_db(db_path):
    with test_db(db_path) as conn:
        conn.execute("""
            CREATE TABLE models(
                id INTEGER PRIMARY KEY,
                name VARCHAR,
            );
            CREATE SEQUENCE seq_models_id START 1;
            CREATE TABLE tests(
                id INTEGER PRIMARY KEY,
                name VARCHAR,
            );
            CREATE SEQUENCE seq_tests_id START 1;
            CREATE TABLE results(
                id INTEGER PRIMARY KEY,
                test_id INTEGER,
                model_id INTEGER,
                code VARCHAR,
                num_ingredients INTEGER,
                num_ingredients_total INTEGER,
                num_ciqual INTEGER,
                total_specified_input_percent FLOAT,
                total_difference FLOAT,
                relative_difference FLOAT,
                UNIQUE (test_id, model_id, code),
                FOREIGN KEY(test_id) REFERENCES tests(id),
                FOREIGN KEY(model_id) REFERENCES models(id)
            );
            CREATE SEQUENCE seq_results_id START 1;
            CREATE TABLE ingredients(
                id INTEGER PRIMARY KEY,
                result_id INTEGER,
                name VARCHAR,
                position DECIMAL,
                is_sub BOOLEAN,
                difference FLOAT,
                has_sub_ingredients BOOLEAN,
                percent_estimate FLOAT,
                percent_hidden FLOAT,
                percent_max FLOAT,
                percent_min FLOAT,
                rank INTEGER,
                text VARCHAR,
                FOREIGN KEY(result_id) REFERENCES results(id),
                UNIQUE (result_id, name, position)
            );
            CREATE SEQUENCE seq_ingredients_id START 1;
            CREATE TABLE categories(
                id INTEGER PRIMARY KEY,
                result_id INTEGER,
                name VARCHAR,
                FOREIGN KEY(result_id) REFERENCES results(id),
                UNIQUE (result_id, name)
            );
            CREATE SEQUENCE seq_categories_id START 1;
        """)


def num_ingredients_total(ingredients):
    if not ingredients:
        return 0
    return len(ingredients) + sum(
        num_ingredients_total(ingredient.get("ingredients")) for ingredient in ingredients
    )

def num_ciqual(ingredients):
    if not ingredients:
        return 0
    return sum(
        1 if ingredient.get("ciqual_food_code") else 0
        for ingredient in ingredients
        if not ingredient.get("ingredients")
    ) + sum(
        num_ciqual(ingredient.get("ingredients")) for ingredient in ingredients
    )


def populate_ingredients_statement(ingredient, result_id, position, is_sub=False):
    yield (
        """
        INSERT INTO ingredients
        (id, result_id, name, position, is_sub, difference, has_sub_ingredients, percent_estimate, percent_hidden, percent_max, percent_min, rank, text)
        VALUES (nextval('seq_ingredients_id'), getvariable('test_id'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ingredient["name"],
            position,
            is_sub,
            ingredient["difference"],
            bool(ingredient.get("ingredients")),
            ingredient["percent_estimate"],
            ingredient["percent_hidden"],
            ingredient["percent_max"],
            ingredient["percent_min"],
            ingredient["rank"],
            ingredient["text"],
        )
    )
    if ingredient.get("ingredients"):
        for sub_ingredient in ingredient["ingredients"]:
            yield from populate_ingredients_statement(sub_ingredient, result_id, is_sub=True)


def populate_statements(results_path):
    yield (
        "INSERT OR IGNORE INTO models VALUES (nextval('seq_models_id'), ?)",
        (model_name(results_path),),
    )
    yield (
        "SET VARIABLE model_id = (SELECT id FROM models WHERE name = ?)",
        (model_name(results_path),),
    )
    # create the test
    yield (
        "INSERT INTO tests VALUES (nextval('seq_tests_id'), ?)",
        (test_name(results_path),),
    )
    yield (
        "SET VARIABLE test_id = (SELECT id FROM tests WHERE name = ?)",
        (test_name(results_path),),
    )
    for json_path in glob.glob(f"{results_path}/*.json"):
        with open(json_path) as f:
            if json_path.endswith("results_summary.json"):
                continue
            code = json_path.split("/")[-1].split(".")[0]
            result = json.load(f)
            yield from result_statements(code, result)


def result_statements(code, result):
    metrics = result["ingredients_metrics"]
    yield (
        """
        INSERT INTO results
        (id, test_id, model_id, code, num_ingredients, num_ingredients_total, num_ciqual, total_specified_input_percent, total_difference, relative_difference)
        VALUES (nextval('seq_results_id'), getvariable('test_id'),getvariable('model_id'), ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            code,
            len(result["ingredients"]),
            num_ingredients_total(result["ingredients"]),
            num_ciqual(result["ingredients"]),
            metrics.get("total_specified_input_percent"),
            metrics.get("total_difference"),
            metrics.get("relative_difference"),
        )
    )
    yield (
        """
        SET VARIABLE result_id = (
            SELECT id FROM results WHERE  getvariable('test_id') AND code = ?)
        """,
        (code,),
    )
    for ingredient in result["ingredients"]:
        pass  # FIXME
    for category in result["categories_tags"]:
        yield (
            """
            INSERT INTO categories
            (id, result_id, name)
            VALUES (nextval('seq_categories_id'), getvariable('result_id'), ?)
            """,
            (category,),
        )


def batched(iter, n):
    while True:
        batch = list(itertools.islice(iter, n))
        if not batch:
            break
        yield batch


def populate_db(db_path, statements):
    with test_db(db_path) as conn:
        for statement in statements:
            conn.execute(*statement)


def process_path(db_path, results_path):
    if glob.glob(f"{results_path}/*.json"):
        populate_db(db_path, populate_statements(results_path))
    else:
        # recurse
        for sub_path in glob.glob("results_path/*"):
            if os.path.isdir(sub_path):
                process_path(db_path, sub_path)

if __name__ == "__main__":
    args = parse_args()
    create_db(args.db_path)
    for results_path in args.results_path:
        process_path(args.db_path, results_path)
