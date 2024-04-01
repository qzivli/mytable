from typing import Optional

from mytable.ast.base import Node, Position, DUMMY_POSITION

__all__ = ["CreateDatabase"]


class CreateDatabase(Node):
    def __init__(
            self,
            name: str,
            info: list,
            file: Optional[str] = None,
            *,
            position: Position = DUMMY_POSITION
    ):
        super().__init__(file=file, position=position)
        self.name = name

    def dump(self) -> dict:
        return {
            "class": self.__class__.__name__,
            "name": self.name,
            "file": self.file,
            "position": self.position.dump()
        }

    def unparse(self):
        return f"CREATE DATABASE `{self.name}`;"

    def render(self) -> Optional[str]:
        return self.unparse()
