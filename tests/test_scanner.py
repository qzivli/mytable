from pprint import pprint

import pytest

from mytable.ast.expression import Number
from mytable.scanner import *


def test_scan_empty_input():
    text = ""
    assert Scanner(text=text).scan() == []


def test_scan_string():
    text = r"'foo'"
    tokens = Scanner(text=text).scan()
    pprint(tokens)


def test_scan_identifier_valid():
    text = r"foo_bar_1_baz"
    tokens = Scanner(text=text).scan()
    pprint(tokens)


def test_scan_identifier_invalid_initial():
    text = r"2_items"
    tokens = Scanner(text=text).scan()
    pprint(tokens)


def test_scan_identifier_invalid_subsequent():
    text = r"foo$bar"
    with pytest.raises(ScannerException) as exc_info:
        tokens = Scanner(text=text).scan()
        pprint(tokens)


def test_scan_multiline_string():
    text = r"""
'  foo
   bar
baz   '
"""
    tokens = Scanner(text=text).scan()
    pprint(tokens)


def test_scan_number():
    text = r"42"
    tokens = Scanner(text=text).scan()
    assert tokens[0] == Number(value=42)


def test_scan_negative_number():
    text = r" -  42   "
    tokens = Scanner(text=text).scan()
    assert tokens[0] == Number(value=-42)


def test_scan_file():
    tokens = Scanner(filename="files/example_input.sql").scan()
    pprint(tokens)
