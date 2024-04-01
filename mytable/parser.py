import enum
import logging
from copy import copy
from typing import Any, Callable
from typing import List, Optional, Union

from mytable.ast.base import Node, is_sql_reserved_word, Delimiter, SkippedStatement, SqlFile, Position, copy_position, MyTableException
from mytable.ast.database import CreateDatabase
from mytable.ast.expression import Identifier, String
from mytable.ast.key import KeyPart, PrimaryKey, ForeignKey, UniqueKey, Index
from mytable.ast.table import Column, CreateTable
from mytable.ast.transactional import StartTransaction, Commit, Transaction
from mytable.ast.types import SqlType, JavaType, is_java_atom, JavaAtom, JavaList, JavaMap, is_sql_type
from mytable.scanner import Scanner

logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s: %(message)s')  # noqa

LOG_NAME = "parser"
logger = logging.getLogger(LOG_NAME)

logger.setLevel(logging.INFO)


class ParserException(MyTableException):
    pass


allow_primary_key_missing = False


def identity(x: Any) -> Any:
    return x


default_name_converter = identity


def to_alchemy_type(data_type):
    pass


class Context(str, enum.Enum):
    CREATE_TABLE = "CREATE TABLE"


class Parser(object):
    def __init__(
            self,
            tokens: List[Node],
            debug_mode: bool = False,
            convert_name: Callable = default_name_converter
    ):
        self.tokens = tokens
        self.offset = 0
        self.debug_mode = debug_mode
        self.convert_name = convert_name

        # storing parsed tables
        self.tables = {}

    def debug(self, x):
        logger.debug(repr(x))

    def get(self, i: int) -> Optional[Node]:
        if i >= len(self.tokens):
            return None
        else:
            node = self.tokens[i]
            self.debug(node)
            return node

    def peek(self, n=1) -> Union[Node, List[Node]]:
        if n == 1:
            return self.get(self.offset)
        else:
            exprs = []
            for i in range(n):
                exprs.append(self.get(self.offset + i))
            return exprs

    def forward(self) -> Node:
        e = self.get(self.offset)
        self.offset += 1
        logger.debug(f"got expr: {e}")
        return e

    def abort(self, *args):
        # msg = f"{args} at {self.line}: {self.col}"
        msg = args
        raise ParserException(msg)

    def parse_transaction(self):
        s = self.expect_specified_symbol("START")
        t = self.expect_specified_symbol("TRANSACTION")
        semicolon = self.expect_delimiter(";")
        start_transaction = StartTransaction(
            file=s.file,
            position=copy_position(s, t, semicolon)
        )

        nodes = []

        while True:
            node = self.peek()
            if node is None:
                self.abort("unexpected None while parse transaction")
            elif identifier_equal(node, "COMMIT"):
                commit = Commit(file=node.file, position=copy(node.position))
                self.forward()
                self.expect_delimiter(";")
                transaction = Transaction(
                    start_transaction=start_transaction,
                    nodes=nodes,
                    commit=commit,
                    position=copy_position(start_transaction, commit)
                )
                transaction.add_children(*nodes)
                return transaction
            else:
                # self.abort("unhandled condition while parse transaction", node)
                nodes.append(self.parse_one())

    def parse_create(self) -> Union[CreateDatabase, CreateTable]:
        """
        CREATE DATABASE... or CREATE TABLE...
        """
        initials = self.peek(2)
        assert identifier_equal(initials[0], "CREATE")
        if identifier_equal(initials[1], "DATABASE"):
            return self.parse_create_database()
        elif identifier_equal(initials[1], "TABLE"):
            return self.parse_create_table()
        else:
            self.abort("unhandled condition", initials[1])

    def parse_create_database(self) -> CreateDatabase:
        info = []
        name = self.forward()
        while True:
            node = self.forward()
            if node is None:
                self.abort("unexpected None while parse CREATE DATABASE")
            elif delimiter_equal(node, ";"):
                return CreateDatabase(name.value, info)
            else:
                info.append(node)

    def parse_create_table(self) -> CreateTable:
        """
        CREATE [TEMPORARY] TABLE [IF NOT EXISTS] tbl_name
            (create_definition,...)
            [table_options]
            [partition_options]
        """
        self.expect_specified_symbols("CREATE TABLE")
        maybe_tbl_name = self.forward()
        if identifier_equal(maybe_tbl_name, "IF"):
            self.expect_specified_symbols("NOT EXISTS")
            if_not_exists = True
            tbl_name = self.forward()
        else:
            if_not_exists = False
            tbl_name = maybe_tbl_name

        _, definitions, _, options, _ = (
            self.expect_delimiter("("),
            self.parse_create_definitions(),
            self.expect_delimiter(")"),
            self.parse_table_options(),
            self.expect_delimiter(";")
        )

        columns = definitions["columns"]
        columns_dict = {x.col_name: x for x in columns}

        primary_key = definitions["primary_key"]
        if (primary_key is None) and (not allow_primary_key_missing):
            raise ParserException(f"tbl_name={tbl_name}, primary key missing")

        indexes = definitions["indexes"]
        keys = definitions["keys"]
        foreign_keys = definitions["foreign_keys"]
        common_code = definitions["common_code"]

        create_table = CreateTable(
            tbl_name=tbl_name.value,
            if_not_exists=if_not_exists,
            columns=columns_dict,
            primary_key=primary_key,
            indexes=indexes,
            keys=keys,
            foreign_keys=foreign_keys,
            common_code=common_code,
            table_options=options,
            partition_options={},
        )

        # HACK:
        if create_table.common_code is not None:
            create_table.common_code.parent = create_table

        create_table.tweak()
        return create_table

    def expect_specified_symbol(self, s: str):
        node = self.peek()
        if identifier_equal(node, s):
            self.forward()
            return node
        else:
            self.abort(f"expect symbol '{s}', but got {repr(node)}")

    def expect_specified_symbols(self, words: str):
        # words = "RESTRICT | CASCADE | SET NULL | NO ACTION | SET DEFAULT"
        def split_bar(s):
            return [x.strip() for x in s.strip().split("|")]

        def split_space(s):
            return [x.strip() for x in s.strip().split()]

        def split(s):
            return [split_space(x) for x in split_bar(s)]

        lol = split(words)
        # d = groupby(xs, len)

        expected_words = None

        symbols = []

        node = self.peek()

        for ls in lol:
            if identifier_equal(node, ls[0]):
                expected_words = ls
                self.forward()
                symbols.append(node)

        if expected_words is None:
            self.abort(f"expected: {words}, got: {node}")

        for word in expected_words[1:]:
            n = self.expect_specified_symbol(word)
            symbols.append(n)

        return symbols

    def expect_unquoted_symbol(self):
        node = self.peek()
        if isinstance(node, Identifier):
            self.forward()
            return node
        else:
            self.abort(f"expect a unquoted symbol, but got {repr(node)}")

    def expect_symbol(self):
        node = self.peek()
        if isinstance(node, Identifier):
            self.forward()
            return node
        else:
            self.abort(f"expect a symbol, but got {repr(node)}")

    def expect_delimiter(self, p: str):
        node = self.peek()
        if delimiter_equal(node, p):
            self.forward()
            return node
        else:
            self.abort(f"expect delimiter '{p}', but got {repr(node)}")

    def expect_enclosed(self) -> Union[Node, List[Node]]:
        self.expect_delimiter("(")
        x = self.forward()
        n = self.peek()
        if delimiter_equal(n, ","):
            xs = [x]
            while True:
                n = self.peek()
                if delimiter_equal(n, ")"):
                    self.forward()
                    return xs
                elif delimiter_equal(n, ","):
                    self.forward()
                    n = self.expect_symbol()
                    xs.append(n)
                else:
                    self.abort(f"unexpect token while parsing enclosed elements: {n}")
        else:
            self.expect_delimiter(")")

        return x

    def parse_key_part(self) -> KeyPart:
        """key_part: {col_name [(length)] | (expr)} [ASC | DESC]"""
        col_name = self.expect_symbol()
        # TODO: handle (expr)
        node = self.peek()
        if delimiter_equal(node, "("):
            length = self.expect_enclosed()
        else:
            length = None
        return KeyPart(col_name=col_name.value, length=length)

    def parse_key_parts(self) -> List[KeyPart]:
        """(key_part,...)"""
        self.expect_delimiter("(")
        key_parts = []
        while True:
            node = self.peek()
            if node is None:
                self.abort("unexpect eof while parsing key_parts")
            if delimiter_equal(node, ")"):
                self.forward()
                break
            if delimiter_equal(node, ","):
                self.forward()
            key_part = self.parse_key_part()
            key_parts.append(key_part)

        return key_parts

    def parse_primary_key(self, symbol=None):
        """
        Syntax:

          [CONSTRAINT [symbol]] PRIMARY KEY
              [index_type] (key_part,...)
              [index_option] ...

          index_type: USING {BTREE | HASH}

        """
        self.expect_specified_symbol("PRIMARY")
        self.expect_specified_symbol("KEY")

        node = self.peek()
        if identifier_equal(node, "USING"):
            index_type = self.expect_symbol().value
        else:
            index_type = None

        key_parts = self.parse_key_parts()

        return PrimaryKey(symbol=symbol,
                          index_type=index_type,
                          key_parts=key_parts)

    def parse_index(self, symbol=None, unique=False):
        self.expect_specified_symbol("INDEX")
        self.expect_delimiter("(")
        i = self.forward()
        self.expect_delimiter(")")

        n = self.peek()
        if delimiter_equal(n, ","):
            self.forward()

        return Index(col_name=i.value, unique=unique)

    def parse_key(self, symbol: Optional[Identifier] = None, unique=True):
        """
        Syntax:

          [CONSTRAINT [symbol]] UNIQUE [INDEX | KEY]
            [index_name] [index_type] (key_part,...)
            [index_option] ...
        """
        # self.expect_specified_symbol("UNIQUE")
        self.expect_specified_symbols("KEY | INDEX")
        if symbol is None:
            s = None
        else:
            s = symbol.value

        key_parts = self.parse_key_parts()

        key = UniqueKey(symbol=s, key_parts=key_parts, unique=unique)
        return key

    def parse_unique(self, symbol) -> UniqueKey:
        self.expect_specified_symbol("UNIQUE")
        node = self.peek()
        if identifier_equal(node, "INDEX") or identifier_equal(node, "KEY"):
            return self.parse_key(symbol=symbol, unique=True)
        else:
            self.abort(f"expect INDEX or KEY after UNIQUE, but got: {node}")

    def parse_foreign_key(self):
        """
        Syntax:

          [CONSTRAINT [symbol]] FOREIGN KEY
            [index_name] (col_name,...)
            reference_definition

        reference_definition:
          REFERENCES tbl_name (key_part,...)
            [MATCH FULL | MATCH PARTIAL | MATCH SIMPLE]
            [ON DELETE reference_option]
            [ON UPDATE reference_option]
        :return:
        """
        self.expect_specified_symbol("FOREIGN")
        self.expect_specified_symbol("KEY")

        n = self.peek()
        if isinstance(n, Identifier):
            self.forward()
            index_name = n.value
        else:
            index_name = None

        col_names = self.expect_enclosed()
        if not isinstance(col_names, list):
            col_names = [col_names]

        self.expect_specified_symbol("REFERENCES")

        ref_tbl_name = self.forward()
        ref_col_names = self.expect_enclosed()
        if not isinstance(ref_col_names, list):
            ref_col_names = [ref_col_names]

        n = self.peek()
        if identifier_equal(n, "MATCH"):
            self.forward()
            match = self.expect_symbol().value
        else:
            match = None

        on_delete = None
        on_update = None
        for i in range(2):
            n = self.peek()
            if identifier_equal(n, "ON"):
                self.forward()
                n = self.expect_symbol()
                if identifier_equal(n, "DELETE"):
                    ref_option = self.expect_specified_symbols("RESTRICT | CASCADE | SET NULL | NO ACTION | SET DEFAULT")
                    on_delete = " ".join([n.value for n in ref_option])
                elif identifier_equal(n, "UPDATE"):
                    ref_option = self.expect_specified_symbols("RESTRICT | CASCADE | SET NULL | NO ACTION | SET DEFAULT")
                    on_update = " ".join([n.value for n in ref_option])
                else:
                    self.abort(f"unexpected token while parsing ON: {n}")

        n = self.peek()
        if delimiter_equal(n, ","):
            self.forward()

        return ForeignKey(col_names=[n.value for n in col_names],
                          ref_tbl_name=ref_tbl_name.value,
                          ref_col_names=[n.value for n in ref_col_names],
                          index_name=index_name,
                          match=match,
                          on_delete=on_delete,
                          on_update=on_update)

    def parse_constraint(self):
        """
        e.g., # CONSTRAINT __unique_code UNIQUE KEY (`payerPaymentType`)

        FIXME: currently only support CONSTRAINT UNIQUE KEY

          [CONSTRAINT [symbol]] PRIMARY KEY
            [index_type] (key_part,...)
            [index_option] ...

        | [CONSTRAINT [symbol]] UNIQUE [INDEX | KEY]
            [index_name] [index_type] (key_part,...)
            [index_option] ...

        | [CONSTRAINT [symbol]] FOREIGN KEY
            [index_name] (col_name,...)


        :return:
        """
        self.expect_specified_symbol("CONSTRAINT")
        n = self.peek()
        saved_symbol = None
        if isinstance(n, Identifier):
            if is_sql_reserved_word(n.value):
                raise ParserException("unhandled condition")
            else:
                self.forward()
                saved_symbol = n
        else:
            self.abort(f"expect a symbol after CONSTRAINT, but got: {n}")

        n = self.peek()
        if identifier_equal(n, "PRIMARY"):
            return self.parse_primary_key()
        elif identifier_equal(n, "UNIQUE"):
            return self.parse_unique(symbol=saved_symbol)
        elif identifier_equal(n, "FOREIGN"):
            return self.parse_foreign_key()
        else:
            self.abort(f"unexpect keyword after CONSTRAINT: {n}")

    def parse_unique_code(self):
        pass

    def parse_common_code(self):
        """non-standard syntax
        """
        self.expect_specified_symbol("__common_code")
        key_parts = self.parse_key_parts()
        key = UniqueKey(symbol=None, key_parts=key_parts, unique=True)
        return key

    def parse_create_definitions(self) -> dict:
        """
        Syntax:

            create_definition: {
                col_name column_definition
              | {INDEX | KEY} [index_name] [index_type] (key_part,...)
                  [index_option] ...
              | {FULLTEXT | SPATIAL} [INDEX | KEY] [index_name] (key_part,...)
                  [index_option] ...
              | [CONSTRAINT [symbol]] PRIMARY KEY
                  [index_type] (key_part,...)
                  [index_option] ...
              | [CONSTRAINT [symbol]] UNIQUE [INDEX | KEY]
                  [index_name] [index_type] (key_part,...)
                  [index_option] ...
              | [CONSTRAINT [symbol]] FOREIGN KEY
                  [index_name] (col_name,...)
                  reference_definition
              | check_constraint_definition
            }

        :return:
        """
        definitions = {
            "columns": [],
            "primary_key": None,
            "indexes": [],
            "keys": [],
            "foreign_keys": [],
            "common_code": None,
        }
        while True:
            node = self.peek()
            if node is None:
                self.abort("unexpected None while parse create definitions")

            elif delimiter_equal(node, ","):
                self.forward()

            elif delimiter_equal(node, ")"):
                return definitions

            elif identifier_equal(node, "PRIMARY"):
                logger.info(f"Seen 'PRIMARY' at ")
                definitions["primary_key"] = self.parse_primary_key()

            elif identifier_equal(node, "FOREIGN"):
                definitions["foreign_keys"].append(self.parse_foreign_key())

            elif identifier_equal(node, "INDEX"):
                definitions["indexes"].append(self.parse_index())

            elif identifier_equal(node, "UNIQUE"):
                definitions["keys"].append(self.parse_unique(symbol=None))
                # exprs.append(self.parse_key(unique=True))

            elif identifier_equal(node, "CONSTRAINT"):
                expr = self.parse_constraint()
                if isinstance(expr, PrimaryKey):
                    definitions["primary_key"] = expr
                elif isinstance(expr, UniqueKey):
                    definitions["keys"].append(expr)
                elif isinstance(expr, ForeignKey):
                    definitions["foreign_keys"].append(expr)
                else:
                    self.abort("BUG: should not happen")

            elif identifier_equal(node, "__common_code"):
                definitions["common_code"] = self.parse_common_code()

            elif isinstance(node, Identifier):
                definitions["columns"].append(self.parse_column_definition())

            else:
                self.abort("unhandled condition while parse create definitions", node)

    def parse_column_definition(self):
        col_name = self.forward()
        # data_type follows col_name immediately
        data_type = self.parse_data_type()

        column = Column(col_name=col_name.value,
                        data_type=data_type,
                        nullable=True,
                        default=None,
                        auto_increment=False,
                        unique=False)

        seen_not = False

        while True:
            node = self.peek()
            if node is None:
                self.abort("unexpected eof while parse column definition")
            elif delimiter_equal(node, ")"):
                return column
            elif delimiter_equal(node, ","):  # or is_keyword(node):
                self.forward()
                return column
            elif identifier_equal(node, "NOT"):
                self.forward()
                seen_not = True
            elif identifier_equal(node, "NULL"):
                self.forward()
                column.nullable = not seen_not
                seen_not = not seen_not
            elif identifier_equal(node, "DEFAULT"):
                self.forward()
                default = self.forward()
                column.default = default
            elif identifier_equal(node, "AUTO_INCREMENT"):
                self.forward()
                column.auto_increment = True
            elif identifier_equal(node, "UNIQUE"):
                self.forward()
                column.unique = True
            elif identifier_equal(node, "enum_choices"):
                self.forward()
                s = self.forward()
                if isinstance(s, String):
                    column.enum_choices = s.value
                else:
                    self.abort("enum_choices must be a string", node)
            elif identifier_equal(node, "COMMENT"):
                self.forward()
                s = self.forward()
                if isinstance(s, String):
                    column.comment = s.value
                else:
                    self.abort("comment must be a string", node)
            elif identifier_equal(node, "__assoc"):
                self.forward()
                s = self.expect_unquoted_symbol()
                assoc_tbl_name, assoc_col_name = s.value.split(".")
                column.assoc_tbl_name = assoc_tbl_name
                column.assoc_col_name = assoc_col_name
            elif identifier_equal(node, "__lift"):
                self.forward()
                column.lift = True
            else:
                self.abort("unhandled condition while parse col definition", node)

    def parse_data_type(self):
        # simple_sql_type = self.forward()
        while True:
            node = self.peek()
            if node is None:
                self.abort("unexpected None while parse data type")
            elif is_sql_type(node):
                return self.parse_sql_type()
            else:
                return self.parse_java_type()

    def parse_sql_type(self):
        name = self.forward()
        n = self.peek()
        if delimiter_equal(n, "("):
            self.forward()
            maximum = self.forward().value
            n = self.peek()
            if delimiter_equal(n, ","):
                self.forward()
                decimals = self.forward().value
            else:
                decimals = None
            self.expect_delimiter(")")
        else:
            maximum = None
            decimals = None

        return SqlType(name.value, maximum, decimals)

    def parse_java_type(self):
        data_type = None
        while True:
            node = self.peek()
            if node is None:
                self.abort("unexpected None while parse Java type")
            elif identifier_equal(node, "List"):
                return self.parse_java_list()
            elif identifier_equal(node, "Map"):
                return self.parse_java_map()
            elif is_java_atom(node):
                self.debug(f"{node} is java atom")
                self.forward()
                return JavaAtom(node.value)
            else:
                self.abort("unhandled condition while parse java type", node)

    def parse_java_list(self):
        self.expect_specified_symbol("List")
        self.expect_delimiter("<")
        e = self.parse_java_type()
        self.expect_delimiter(">")
        if e.name == "String":
            return SqlType("JSON", None)
        else:
            t = JavaList(e)
            return t

    def parse_java_map(self):
        self.expect_specified_symbol("Map")
        self.expect_delimiter("<")
        k = self.parse_java_type()
        self.expect_delimiter(",")
        v = self.parse_java_type()
        self.expect_delimiter(">")
        t = JavaMap(k.name, v)
        return t

    def parse_table_options(self):
        options = {}
        k = None
        seen_equal_sign = False

        while True:
            node = self.peek()
            if node is None:
                self.abort("unexpected None while parse table options")
            elif delimiter_equal(node, ";"):
                # self.forward()
                return options
            elif delimiter_equal(node, "="):
                self.forward()
                seen_equal_sign = True
            elif delimiter_equal(node, ","):
                self.forward()
            elif isinstance(node, Identifier) or isinstance(node, String):
                self.forward()
                if seen_equal_sign:
                    if k is None:
                        self.abort("option key is None while parse table options", node)
                    else:
                        seen_equal_sign = False
                        options[k] = node
                        k = None
                else:
                    if k is None:
                        k = node
                    else:
                        self.abort("table option format should be key=value", node)
            else:
                self.abort("unhandled condition while parse table options", node)

    def parse_table_option(self):
        pass

    def parse_table_sequence(self):
        exprs = []
        while True:
            node = self.peek()
            if node is None:
                self.abort("unexpected None while parse table sequence")
            elif delimiter_equal(node, ")"):
                self.forward()
                return exprs
            else:
                self.forward()
                exprs.append(self.parse_create_definitions())

    def parse_extra_info(self):
        pass

    def parse(self, context=None):
        pass

    def parse_exprs(self):
        exprs = []

    def parse_one(self):
        node = self.peek()
        if node is None:
            return None
        elif isinstance(node, Identifier):
            if node.quoted:
                return node
            if node.value.upper() == "START":
                return self.parse_transaction()
            elif node.value.upper() == "DROP":
                return self.skip_statement()
            elif identifier_equal(node, "USE"):
                return self.skip_statement()
            elif node.value.upper() == "CREATE":
                # self.forward()
                e = self.parse_create()
                return e
            else:
                self.abort("unhandled condition", node)
        elif isinstance(node, Delimiter):
            # 直接返回，让parse句子的函数来处理
            return node
        else:
            self.abort("unhandled condition", node)

    # HACK
    def skip_statement(self):
        while True:
            node = self.forward()
            if node is None:
                self.abort("unexpected None while skipping a statement")
            elif delimiter_equal(node, ";"):
                return SkippedStatement()

    def parse_all(self):
        nodes = []
        while True:
            node = self.peek()
            if node is None:
                top_node = SqlFile(nodes)
                top_node.add_children(*nodes)
                return top_node
            elif isinstance(node, Identifier):
                if node.value.upper() == "START":
                    nodes.append(self.parse_transaction())
                elif node.value.upper() == "DROP":
                    skipped = self.skip_statement()
                    continue
                elif identifier_equal(node, "USE"):
                    skipped = self.skip_statement()
                    continue
                elif identifier_equal(node, "CREATE"):
                    e = self.parse_create()
                    nodes.append(e)
                else:
                    self.abort("unhandled condition", node)
            else:
                self.abort("unhandled condition", node)


def equal(a: str, b: str) -> bool:
    return a.upper() == b.upper()


def identifier_equal(node: Node, s: str) -> bool:
    return isinstance(node, Identifier) and node.value.upper() == s.upper()


def delimiter_equal(node: Node, s: str) -> bool:
    return isinstance(node, Delimiter) and node.value == s


def is_keyword(node: Node):
    raise NotImplementedError()


def resolve_table(x):
    raise NotImplementedError()


def resolve_java_type(x):
    raise NotImplementedError()


def too_complex(typ: JavaType):
    if isinstance(typ, JavaAtom):
        return False
    elif isinstance(typ, JavaList):
        e = typ.element_type
        if isinstance(e, JavaAtom):
            return False
        else:
            return True
    elif isinstance(typ, JavaMap):
        # FIXME
        return True
    else:
        raise ParserException("not a java type", typ)


def make_table_name(parent_table_name: str, col_name: str):
    return f"{parent_table_name}_{col_name}"


def parse_sql_file(filename: str, debug_mode: bool = False) -> SqlFile:
    lexer = Scanner(filename=filename, debug_mode=debug_mode)
    tokens = lexer.scan()
    logger.debug(tokens)
    parser = Parser(tokens, debug_mode=debug_mode)
    tree = parser.parse_all()
    return tree


def parse_sql(text: str, debug_mode: bool = False):
    lexer = Scanner(text=text, debug_mode=debug_mode)
    tokens = lexer.scan()
    logger.debug(tokens)
    parser = Parser(tokens, debug_mode=debug_mode)
    tree = parser.parse_all()
    return tree
