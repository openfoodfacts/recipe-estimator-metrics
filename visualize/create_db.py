# this scripts takes the results from a one or more test runs and creates a database to help visualize the results

import argparse
import collections
import contextlib
import glob
import itertools
import json
import os

import duckdb
import sqlite3
import pandas as pd


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
    return results_path.strip("/").split('/')[-1]


def model_name(results_path):
    return results_path.strip("/").split('/')[-2]


def is_sqlite(db_path):
    return db_path.endswith(".sqlite")

@contextlib.contextmanager
def test_db(db_path):
    if is_sqlite(db_path):
        with sqlite3.connect(db_path) as conn:
            yield conn
    else:
        with duckdb.connect(db_path) as conn:
            yield conn


def create_db(db_path):
    with test_db(db_path) as conn:
        sql = """
            CREATE TABLE models(
                id INTEGER PRIMARY KEY,
                name VARCHAR
            );
            CREATE TABLE tests(
                id INTEGER PRIMARY KEY,
                name VARCHAR
            );
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
            CREATE TABLE categories(
                id INTEGER PRIMARY KEY,
                result_id INTEGER,
                name VARCHAR,
                FOREIGN KEY(result_id) REFERENCES results(id),
                UNIQUE (result_id, name)
            );
        """
        for statement in sql.split(";"):
            conn.execute(statement)


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


def next_seq(sequences, name, key=None):
    """Try to get the right sequence number for a table row

    if key is not None, we might seek for a previous sequence number for this key

    It then sets current sequence for the table
    """
    if name not in sequences:
        sequences[name] = {"seq": 0, "keys": {}, "current": None}
    if key:
        is_new = False
        if key not in sequences[name]["keys"]:
            sequences[name]["seq"] += 1
            sequences[name]["keys"][key] = sequences[name]["seq"]
            is_new = True
        sequences[name]["current"] = sequences[name]["keys"][key]
        return sequences[name]["current"], is_new
    else:
        sequences[name]["seq"] += 1
        sequences[name]["current"] = sequences[name]["seq"]
        return sequences[name]["current"]


def current_seq(sequences, name):
    return sequences[name]["current"]


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


def populate_statements(results_path, sequences):
    model_id, is_new = next_seq(sequences, "models", model_name(results_path))
    if is_new:
        yield ("models", {
            "id": model_id,
            "name": model_name(results_path),
        })
    test_id, is_new = next_seq(sequences, "tests", test_name(results_path))
    if is_new:
        yield ("tests", {
            "id": test_id,
            "name": test_name(results_path),
        })
    for json_path in glob.glob(f"{results_path}/*.json"):
        with open(json_path) as f:
            if json_path.endswith("results_summary.json"):
                continue
            code = json_path.split("/")[-1].split(".")[0]
            result = json.load(f)
            yield from result_statements(sequences, code, result)


def result_statements(sequences, code, result):
    metrics = result["ingredients_metrics"]
    yield ("results", {
        "id": next_seq(sequences, "results"),
        "test_id": current_seq(sequences, "tests"),
        "model_id": current_seq(sequences, "models"),
        "code": code,
        "num_ingredients": len(result["ingredients"]),
        "num_ingredients_total": num_ingredients_total(result["ingredients"]),
        "num_ciqual": num_ciqual(result["ingredients"]),
        "total_specified_input_percent": metrics.get("total_specified_input_percent"),
        "total_difference": metrics.get("total_difference"),
        "relative_difference": metrics.get("relative_difference"),
    })
    for ingredient in result["ingredients"]:
        pass  # FIXME
    for category in result.get("categories_tags", []):
        yield ("categories", {"id": next_seq(sequences, "categories"), "result_id": current_seq(sequences, "results"), "name": category})


def batched(iter, n):
    while True:
        batch = list(itertools.islice(iter, n))
        if not batch:
            break
        yield batch


def populate_db(db_path, statements):
    ORDERS = {
        "models": 1,
        "tests": 2,
        "results": 3,
        "ingredients": 4,
        "categories": 5,
    }
    with test_db(db_path) as conn:
        # create dataframes
        datas = sorted(statements, key=lambda x: (ORDERS[x[0]], x[0], x[1].get("id")))
        for table, data in itertools.groupby(datas, lambda x: x[0]):
            data_df = pd.DataFrame([d[1] for d in data])
            if is_sqlite(db_path):
                # sqlite
                data_df.to_sql(name=table, con=conn, if_exists="append", index=False, method="multi")
            else:
                # duckdb
                conn.execute(f"INSERT INTO {table} SELECT * FROM data_df")


def process_path(db_path, results_path, sequences=None):
    if glob.glob(f"{results_path}/*.json"):
        populate_db(db_path, populate_statements(results_path, sequences))
    else:
        # recurse
        for sub_path in glob.glob("results_path/*"):
            if os.path.isdir(sub_path):
                process_path(db_path, sub_path, sequences)

if __name__ == "__main__":
    args = parse_args()
    create_db(args.db_path)
    # help having unique ids per models
    # if we want to update an existing db, we should get sequences from database
    sequences = {}
    for results_path in args.results_path:
        process_path(args.db_path, results_path, sequences)
