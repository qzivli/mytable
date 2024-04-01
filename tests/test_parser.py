from pprint import pprint

from mytable.ast.key import *
from mytable.ast.table import *
from mytable.ast.types import *
from mytable.parser import parse_sql_file, Parser
from mytable.scanner import Scanner


def test_parse_data_type():
    text = r"INT"
    tokens = Scanner(text=text).scan()
    ast = Parser(tokens=tokens).parse_data_type()
    print(ast)
    assert ast == SqlType(name="int")


def test_parse_data_type_maximum():
    text = r"VARCHAR(36)"
    tokens = Scanner(text=text).scan()
    print(tokens)
    ast = Parser(tokens=tokens).parse_data_type()
    print(ast.dump())
    assert ast == SqlType(name="VARCHAR", maximum=36)


def test_parse_data_type_decimals():
    text = r"DECIMAL(10, 2)"
    tokens = Scanner(text=text).scan()
    ast = Parser(tokens=tokens).parse_data_type()
    assert ast == SqlType(name="DECIMAL", maximum=10, decimals=2)


def test_parse_java_list():
    text = r"List<TravelRoute>"
    tokens = Scanner(text=text).scan()
    ast = Parser(tokens=tokens).parse_java_type()
    pprint(ast)
    assert ast == JavaList(element_type=JavaAtom(name='TravelRoute'))


def test_parse_java_map():
    text = r"Map<String, Object>"
    tokens = Scanner(text=text).scan()
    ast = Parser(tokens=tokens).parse_java_type()
    pprint(ast)
    assert ast == JavaMap(key_type="String", value_type=JavaAtom(name="Object"))


def test_parse_composite_key():
    text = r"PRIMARY KEY (account_type, account_code)"
    tokens = Scanner(text=text).scan()
    ast = Parser(tokens=tokens).parse_primary_key()
    assert ast == PrimaryKey(key_parts=[KeyPart(col_name="account_type"), KeyPart(col_name="account_code")])


def test_parse_foreign_key():
    text = r"FOREIGN KEY (ref_num, ref_type) REFERENCES accounts (`id`)"
    tokens = Scanner(text=text).scan()
    ast = Parser(tokens=tokens).parse_foreign_key()
    pprint(ast.dump())


def test_parse_sql_file():
    sql = parse_sql_file(filename="files/example_input.sql")
    pprint(sql)


def test_parse_column():
    text = r"`id` int AUTO_INCREMENT NOT NULL COMMENT 'primary key',"
    tokens = Scanner(text=text).scan()
    ast = Parser(tokens=tokens).parse_column_definition()
    pprint(ast)
    assert Parser(tokens=tokens).parse_column_definition() == Column(
        col_name='id',
        data_type=SqlType(name='int', maximum=None, decimals=None),
        nullable=False,
        default=None,
        visible=True,
        auto_increment=True,
        unique=False,
        primary=False,
        enum_choices=None,
        assoc_tbl_name=None,
        assoc_col_name=None
    )
