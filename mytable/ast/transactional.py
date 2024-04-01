from typing import Optional, List

from mytable.ast.base import Node, Position
from mytable.ast.statement import Statement


class StartTransaction(Statement):
    def __init__(self, file: Optional[str] = None, *, position: Position):
        super().__init__(file=file, position=position)

    def dump(self) -> dict:
        return {
            "class": self.__class__.__name__,
            "file": self.file,
            "position": self.position.dump()
        }

    def unparse(self):
        return "START TRANSACTION;"

    def render(self) -> Optional[str]:
        return self.unparse()

    def to_alchemy(self):
        return ""

    def to_pydantic(self):
        raise NotImplementedError


class Commit(Statement):
    def __init__(self, file: Optional[str] = None, *, position: Position):
        super().__init__(file=file, position=position)

    def dump(self) -> dict:
        return {
            "class": self.__class__.__name__,
            "file": self.file,
            "position": self.position.dump()
        }

    def unparse(self):
        return "COMMIT;"

    def render(self) -> Optional[str]:
        return self.unparse()

    def to_alchemy(self):
        return ""

    def to_pydantic(self):
        raise NotImplementedError


class Transaction(Statement):
    def __init__(
            self,
            start_transaction: StartTransaction,
            nodes: List[Node],
            commit: Commit,
            file: Optional[str] = None,
            *,
            position: Position
    ):
        super().__init__(file=file, position=position)
        self.start_transaction = start_transaction
        self.nodes = nodes
        self.commit = commit

    def dump(self) -> dict:
        return {
            "class": self.__class__.__name__,
            "start_transaction": self.start_transaction,
            "nodes": [node.dump() for node in self.nodes],
            "commit": self.commit,
            "file": self.file,
            "position": self.position.dump()
        }

    def unparse(self):
        s = self.start_transaction.unparse()
        s += "\n\n"
        lines = [e.unparse() for e in self.nodes if e]
        s += "\n\n".join(lines)
        s += "\n\n"
        s += self.commit.unparse()
        return s

    def render(self) -> Optional[str]:
        return self.unparse()

    def to_alchemy(self):
        result = []
        for expr in self.nodes:
            result.append(expr.to_alchemy())
        return result

    def to_pydantic(self):
        raise NotImplementedError
