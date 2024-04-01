from abc import ABC, abstractmethod
from typing import List
from typing import Optional

from mytable.ast.data import mysql_reserved_words

__all__ = [
    "MyTableException",
    "sql_dialect", "format_dict",
    "is_sql_reserved_word",
    "Position", "DUMMY_POSITION", "copy_position",
    "Node", "SqlFile", "SkippedStatement", "Delimiter",
]


class MyTableException(Exception):
    pass


sql_dialect = "mysql"

sql_reserved_words = mysql_reserved_words


def format_dict(d: dict) -> str:
    lines = []
    for k, v in d.items():
        lines.append(f"{k} = {v}")

    return "\n  ".join(lines)


def is_sql_reserved_word(word: str):
    return word in sql_reserved_words


class Position(object):
    def __init__(
            self,
            start: int = 0,
            end: int = 0,
            start_line: int = 0,
            start_col: int = 0,
            end_line: int = 0,
            end_col: int = 0
    ):
        self.start = start
        self.end = end
        self.start_line = start_line
        self.start_col = start_col
        self.end_line = end_line
        self.end_col = end_col

    def __str__(self):
        return "{},{}-{},{}".format(self.start_line, self.start_col, self.end_line, self.end_col)

    def dump(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "start_line": self.start_line,
            "start_col": self.start_col,
            "end_line": self.end_line,
            "end_col": self.end_col,
        }


DUMMY_POSITION = Position()


def copy_position(*nodes):
    assert len(nodes) >= 2
    s = nodes[0]
    t = nodes[-1]
    return Position(
        start=s.position.start,
        end=t.position.end,
        start_line=s.position.start_line,
        start_col=s.position.start_col,
        end_line=t.position.end_line,
        end_col=t.position.end_col
    )


class Node(ABC):
    def __init__(
            self,
            *,
            name: Optional[str] = None,
            file: Optional[str] = None,
            position: Position = DUMMY_POSITION
    ):
        self.name = name
        self.file = file
        self.position = position

        self.value = None
        self.parent: Optional[Node] = None

    def __str__(self):
        return f"<{self.__class__.__name__} {self.name!r} at {self.position}>"

    def __repr__(self):
        return self.__str__()

    @abstractmethod
    def dump(self) -> dict:
        return {}

    def __len__(self):
        return self.position.end - self.position.start

    def __eq__(self, other):
        if isinstance(other, Node):
            return self.file == other.file \
                and self.position.start == other.position.start \
                and self.position.end == other.position.end
        else:
            return False

    def __hash__(self):
        return hash(f"{self.file}:{self.position.start}:{self.position.end}")

    def set_parent_node(self, parent):
        self.parent = parent

    def get_ast_root(self):
        if self.parent is None:
            return self
        else:
            return self.parent.get_ast_root()

    def add_children(self, *nodes):
        for node in nodes:
            if node is not None:
                node.set_parent_node(self)

    @abstractmethod
    def unparse(self) -> str:
        pass

    @abstractmethod
    def render(self) -> Optional[str]:
        return self.unparse()


class SqlFile(Node):
    def __init__(
            self,
            nodes: List[Node],
            *,
            file: Optional[str] = None,
            position: Position = DUMMY_POSITION
    ):
        super().__init__(file=file, position=position)
        self.nodes = nodes

        self.ref_chain = {}

    def __eq__(self, other):
        if isinstance(other, SqlFile):
            for i, n in enumerate(self.nodes):
                if n != other.nodes[i]:
                    return False
            return True
        else:
            return False

    def dump(self) -> dict:
        return {
            "class": self.__class__.__name__,
            "nodes": [node.dump() for node in self.nodes],
            "position": self.position.dump()
        }

    def unparse(self):
        lines = [
            node.unparse()
            for node in self.nodes
            if node is not None
        ]
        return "\n\n".join(lines)

    def render(self) -> Optional[str]:
        lines = [
            node.render()
            for node in self.nodes
            if node is not None
        ]
        return "\n\n".join(lines)


class SkippedStatement(Node):
    def __init__(
            self,
            *,
            file: Optional[str] = None,
            position: Position = DUMMY_POSITION
    ):
        super().__init__(file=file, position=position)

    def dump(self):
        return {
            "class": self.__file__,
            "value": self.value,
            "file": self.file,
            "position": self.position.dump()
        }

    def unparse(self):
        return ""

    def render(self) -> Optional[str]:
        return self.unparse()


class Delimiter(Node):
    def __init__(
            self,
            value: str,
            *,
            file: Optional[str] = None,
            position: Position = DUMMY_POSITION
    ):
        super().__init__(file=file, position=position)
        self.value = value

    def __str__(self):
        return f"<{self.__class__.__name__} {self.value!r} at {self.position}>"

    def dump(self):
        return {
            "class": self.__file__,
            "value": self.value,
            "file": self.file,
            "position": self.position.dump()
        }

    def unparse(self):
        return self.value

    def render(self) -> Optional[str]:
        return self.unparse()
