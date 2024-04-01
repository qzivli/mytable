import io

import pytest

from mytable.parser import parse_sql, parse_sql_file
from mytable.transpiler import transpile_sql, transpile_sql_file


def test_memory_file():
    memory_file = io.StringIO()

    data = memory_file.getvalue()
    print(data)


def test_java_atom_type_ref():
    text = r"""
    CREATE TABLE Item (
      `id` INT AUTO_INCREMENT NOT NULL,
      `name` VARCHAR(36),
       PRIMARY KEY (`id`)
    );
    CREATE TABLE A (
      `id` INT AUTO_INCREMENT NOT NULL,
      `item` Item,
      PRIMARY KEY (`id`)
    );
    """

    expected = r"""
    CREATE TABLE IF NOT EXISTS `Item`
    (
        `id` INT AUTO_INCREMENT NOT NULL,
        `name` VARCHAR(36) NULL,
        `etl_date` datetime NULL,
        PRIMARY KEY (id)
    );
    CREATE TABLE IF NOT EXISTS `A`
    (
        `id` INT AUTO_INCREMENT NOT NULL,
        `item_id` int NULL,
        `etl_date` datetime NULL,
        PRIMARY KEY (id),
        FOREIGN KEY item (item_id) REFERENCES Item (id) ON DELETE CASCADE
    );
    """
    s = transpile_sql(text)
    print(s)
    assert parse_sql(s) == parse_sql(expected)

    # with pytest.raises(Exception) as exc_info:
    #     transpile_sql(text)
    #
    # print(exc_info)


def test_java_atom_type_missing():
    text = r"""
    CREATE TABLE A (
      `id` int AUTO_INCREMENT NOT NULL,
      `item` Item,
      PRIMARY KEY (`id`)
    );
    """
    transpile_sql(text)
    # with pytest.raises(Exception) as exc_info:
    #     transpile_sql(text)
    #
    # print(exc_info)


def test_list_element_missing():
    text = r"""
    CREATE TABLE A (
      `id` int AUTO_INCREMENT NOT NULL,
      `items` List<Item>,
      PRIMARY KEY (`id`)
    );
    """
    with pytest.raises(Exception) as exc_info:
        transpile_sql(text)

    print(exc_info)


def test_map_value_missing():
    text = r"""
    CREATE TABLE A (
      `id` int AUTO_INCREMENT NOT NULL,
      `items` Map<String, Item>,
      PRIMARY KEY (`id`)
    );
    """
    s = transpile_sql(text)
    print(s)
    # with pytest.raises(Exception) as exc_info:
    #     transpile_sql(text)
    #
    # print(exc_info)


def test_transpile_file():
    input_file = "files/example_input.sql"
    output_file = "files/transpiled.sql"
    transpile_sql_file(input_file, output_file)


def test_transpile_one_to_many():
    text = open("files/one_to_many.sql").read()
    assert parse_sql(transpile_sql(text)) == parse_sql_file("files/one_to_many_output.sql")


def test_transpile_many_to_many():
    text = open("files/many_to_many.sql").read()
    print(transpile_sql(text))
