import re
from abc import ABC
from typing import Optional
from typing import Union

from mytable.ast.base import *

__all__ = [
    "SQL_TYPES",
    "SqlType", "JavaType", "JavaAtom", "JavaList", "JavaMap",
    "is_sql_type", "is_java_type", "is_type",
    "is_java_atom",
    "complex_data_type",
]

from mytable.ast.expression import Identifier

SQL_TYPES = {
    "bit", "tinyint", "smallint", "int", "bigint", "long", "decimal", "numeric", "float", "real",
    "bool", "boolean",
    "date", "time", "datetime", "timestamp", "year",
    "char", "varchar", "text",
    "clob", "blob", "xml", "json"
}


def complex_data_type(use_json: bool):
    if sql_dialect.lower() == "mysql":
        if use_json:
            return "JSON"
        else:
            return "mediumtext"
    else:
        raise NotImplementedError(f"unsupported SQL dialect: {sql_dialect}")


class SqlType(Node):
    def __init__(
            self,
            name: str,
            maximum: Optional[int] = None,
            decimals: Optional[int] = None,
            file: Optional[str] = None,
            *,
            position: Position = DUMMY_POSITION
    ):
        super().__init__(file=file, position=position)
        self.name = name
        self.maximum = maximum
        self.decimals = decimals

    def __eq__(self, other):
        return (
                isinstance(other, SqlType) and
                self.name.upper() == other.name.upper() and
                self.maximum == other.maximum and
                self.decimals == other.decimals
        )

    def dump(self):
        return {
            "class": self.__class__.__name__,
            "name": self.name,
            "maximum": self.maximum,
            "decimals": self.decimals,
            "file": self.file,
            "position": self.position.dump()
        }

    def unparse(self):
        if self.maximum:
            if self.decimals:
                return f"{self.name}({self.maximum}, {self.decimals})"
            else:
                return f"{self.name}({self.maximum})"
        else:
            return self.name

    def render(self) -> Optional[str]:
        return self.unparse()


class JavaType(Node, ABC):
    name: Optional[str]

    def unparse(self):
        pass

    def render(self) -> Optional[str]:
        return self.unparse()


class JavaAtom(JavaType):
    def __init__(
            self,
            name: str,
            file: Optional[str] = None,
            *,
            position: Position = DUMMY_POSITION
    ):
        super().__init__(file=file, position=position)
        self.name = name

    def dump(self):
        return {
            "class": self.__file__,
            "name": self.name,
            "file": self.file,
            "position": self.position.dump()
        }

    def __eq__(self, other):
        return isinstance(other, JavaAtom) and self.name == other.name

    def __ne__(self, other):
        return not self.__eq__(other)

    def unparse(self):
        return self.name

    def render(self) -> Optional[str]:
        return "int"


class JavaList(JavaType):
    def __init__(
            self,
            element_type: Union[str, JavaType],
            file: Optional[str] = None,
            *,
            position: Position = DUMMY_POSITION
    ):
        super().__init__(file=file, position=position)
        self.element_type = element_type

        self.add_children(element_type)

    def dump(self):
        et = self.element_type
        return {
            "class": self.__name__,
            "element_type": et.dump() if isinstance(et, JavaType) else et,
            "file": self.file,
            "position": self.position.dump()
        }

    def __eq__(self, other):
        return isinstance(other, JavaList) and self.element_type == other.element_type

    def __ne__(self, other):
        return not self.__eq__(other)

    def unparse(self):
        if isinstance(self.element_type, JavaType):
            e = self.element_type.unparse()
        else:
            e = self.element_type

        return f"List<{e}>"

    def render(self) -> Optional[str]:
        # should not render
        return None


class JavaMap(JavaType):
    def __init__(
            self,
            key_type: str,
            value_type: Union[str, JavaType],
            file: Optional[str] = None,
            *,
            position: Position = DUMMY_POSITION
    ):
        super().__init__(file=file, position=position)
        self.key_type = key_type
        self.value_type = value_type

        self.add_children(value_type)

    def dump(self):
        return {
            "class": self.__file__,
            "key_type": self.key_type,
            "value_type": self.value_type,
            "file": self.file,
            "position": self.position.dump()
        }

    def __eq__(self, other):
        return (
                isinstance(other, JavaMap) and
                self.key_type == other.key_type and
                self.value_type == other.value_type
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def unparse(self):
        k = self.key_type
        if isinstance(self.value_type, JavaType):
            v = self.value_type.unparse()
        else:
            v = self.value_type

        return f"Map<{k}, {v}>"

    def render(self) -> Optional[str]:
        return self.unparse()


def sql_type_to_alchemy(sql_type: str) -> str:
    mapping = {
        "int": "Integer",
        "tinyint": "Integer",
        "long": "BigInteger",
        "decimal": "DECIMAL",
        "varchar": "String",

        "bool": "Boolean",
        "boolean": "Boolean",
        "json": "JSON",

    }
    return mapping.get(sql_type.lower())


def sql_type_to_pydantic(sql_type: str) -> str:
    mapping = {
        "int": "int",
        "tinyint": "bool",
        "long": "int",
        "float": "float",
        "double": "float",
        "decimal": "Decimal",
        "timestamp": "int",
        "datetime": "Union[datetime.datetime, int]",
        "varchar": "str",
        "text": "str",
        "bool": "bool",
        "boolean": "bool",
        # "json": "Union[list,dict]",
        "json": "Any",
    }
    return mapping.get(sql_type.lower())


def is_sql_type(node: Node):
    return isinstance(node, Identifier) and node.value.lower() in SQL_TYPES


def is_java_type(node: Node):
    return isinstance(node, Identifier) and not is_sql_type(node)


def is_java_atom(node: Node):
    return is_java_type(node) and is_java_class_name(node.value)


def is_java_class_name(name: str):
    parts = re.findall('[A-Z][a-z]*', name)
    return " ".join(parts).istitle()


def is_type(node: Node):
    return is_sql_type(node) or is_java_type(node)
