from abc import ABC
from typing import Optional

from mytable.ast.base import Node, Position, DUMMY_POSITION

__all__ = [
    "Expression",
    "String",
    "Identifier",
    "Number"
]


class Expression(Node, ABC):
    def __str__(self):
        return f"<{self.__class__.__name__} {self.value!r} at {self.position}>"


class Identifier(Expression):
    def __init__(
            self,
            value: str,
            *,
            quoted: bool = False,
            file: Optional[str] = None,
            position: Position = DUMMY_POSITION,
    ):
        super().__init__(file=file, position=position)
        self.value = value
        self.quoted = quoted

    def dump(self):
        return {
            "class": self.__class__.__name__,
            "value": self.value,
            "quoted": self.quoted,
            "file": self.file,
            "position": self.position.dump(),
        }

    def unparse(self):
        return self.value

    def render(self) -> Optional[str]:
        return self.unparse()


class String(Expression):
    def __init__(
            self,
            value: str,
            *,
            file: Optional[str] = None,
            position: Position = DUMMY_POSITION,
    ):
        super().__init__(file=file, position=position)
        self.value = value

    def dump(self):
        return {
            "class": self.__class__.__name__,
            "value": self.value,
            "file": self.file,
            "position": self.position.dump()
        }

    def unparse(self):
        return f"'{self.value}'"

    def render(self) -> Optional[str]:
        return self.unparse()


class Number(Expression):
    def __init__(
            self,
            value: int,
            *,
            file: Optional[str] = None,
            position: Position = DUMMY_POSITION,
    ):
        super().__init__(file=file, position=position)
        self.value = value

    def __eq__(self, other):
        return isinstance(other, Number) and self.value == other.value

    def dump(self):
        return {
            "class": self.__class__.__name__,
            "value": self.value,
            "file": self.file,
            "position": self.position.dump()
        }

    def unparse(self):
        return f"{self.value}"

    def render(self) -> Optional[str]:
        return self.unparse()
