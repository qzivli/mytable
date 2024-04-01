import logging
from enum import Enum
from typing import List, Optional

from mytable.ast.base import *
from mytable.ast.base import DUMMY_POSITION

__all__ = [
    "KeyPart", "PrimaryKey", "Index", "ForeignKey", "UniqueKey",
    "ReferenceOption",
]

logger = logging.getLogger(__name__)

alchemy_reserved_names = {"metadata", }

default_table_options = {
    "ENGINE": "InnoDB",
    "CHARSET": "utf8mb4",
}


class KeyPart(Node):
    """
    key_part: {col_name [(length)] | (expr)} [ASC | DESC]
    """

    def __init__(
            self,
            col_name: str,
            length: Optional[int] = None,
            expr: Optional[str] = None,
            file: Optional[str] = None,
            *,
            position: Position = DUMMY_POSITION
    ):
        super().__init__(file=file, position=position)
        self.col_name = col_name
        self.length = length
        self.expr = expr

    def dump(self):
        return {
            "class": self.__class__.__name__,
            "col_name": self.col_name,
            "length": self.length,
            "expr": self.expr,
            "position": self.position.dump()
        }

    def unparse(self) -> str:
        sql = self.col_name
        if self.length:
            sql += f" ({self.length})"
        return sql

    def render(self) -> Optional[str]:
        return self.unparse()

    def to_alchemy(self):
        pass

    def to_pydantic(self):
        return ""


class PrimaryKey(Node):
    """
    Syntax:

      [CONSTRAINT [symbol]] PRIMARY KEY
          [index_type] (key_part,...)
          [index_option] ...
    """

    def __init__(
            self,
            *,
            symbol: Optional[str] = None,
            index_type: Optional[str] = None,
            key_parts: List[KeyPart],
            index_option=None,
            file: Optional[str] = None,
            position: Position = DUMMY_POSITION,
    ):
        super().__init__(file=file, position=position)
        self.symbol = symbol
        self.index_type = index_type
        self.key_parts = key_parts
        self.index_option = index_option

        self.add_children(*key_parts)

    def dump(self):
        return {
            "class": self.__class__.__name__,
            "symbol": self.symbol,
            "index_type": self.index_type,
            "key_parts": self.key_parts,
            "index_option": self.index_option,
            "position": self.position.dump()
        }

    def unparse(self):
        key_parts = ", ".join([p.unparse() for p in self.key_parts])
        if self.symbol:
            return f"    CONSTRAINT {self.symbol} PRIMARY KEY ({key_parts})"
        else:
            return f"    PRIMARY KEY ({key_parts})"

    def render(self) -> Optional[str]:
        return self.unparse()

    def to_alchemy(self):
        return ""

    def to_pydantic(self):
        # TODO
        # FIXME
        return ""


class Index(Node):
    def __init__(
            self,
            col_name: str,
            unique: bool,
            file: Optional[str] = None,
            *,
            position: Position
    ):
        super().__init__(file=file, position=position)
        self.col_name = col_name
        self.unique = unique
        # HACK
        self.name = ""

    def dump(self):
        return {
            "class": self.__class__.__name__,
            "col_name": self.col_name,
            "file": self.file,
            "position": self.position.dump()
        }

    def unparse(self):
        s = f"INDEX (`{self.col_name}`)"
        if self.unique:
            return "    UNIQUE " + s
        else:
            return "    " + s

    def render(self) -> Optional[str]:
        return self.unparse()

    def to_alchemy(self):
        # raise Exception("should not direct render an index")
        return ""

    def to_pydantic(self):
        return ""


class UniqueKey(Node):
    """
    Syntax:
        [CONSTRAINT [symbol]] UNIQUE [INDEX | KEY]
            [index_name] [index_type] (key_part,...)
            [index_option] ...

        key_part: {col_name [(length)] | (expr)} [ASC | DESC]
    """

    def __init__(
            self,
            *,
            symbol: Optional[str] = None,
            key_parts: List[KeyPart],
            index_name: Optional[str] = None,
            index_type: Optional[str] = None,
            index_option=None,
            unique: bool = True,
            file: Optional[str] = None,
            position: Position = DUMMY_POSITION
    ):
        super().__init__(file=file, position=position)
        self.symbol = symbol
        self.key_parts = key_parts
        self.index_name = index_name
        self.index_type = index_type
        self.index_option = index_option
        self.unique = unique

    def dump(self):
        return {
            "class": self.__class__.__name__,
            "symbol": self.symbol,
            "key_parts": self.key_parts,
            "index_name": self.index_name,
            "index_type": self.index_type,
            "index_option": self.index_option,
            "file": self.file,
            "position": self.position.dump()
        }

    def unparse(self) -> str:
        sql = f"    CONSTRAINT"
        if self.symbol:
            sql += f" {self.symbol}"
        sql += " UNIQUE KEY"
        # TODO: handle index_name and index_type
        key_parts = ",".join([p.unparse() for p in self.key_parts])
        sql += f" ({key_parts})"
        return sql

    def render(self) -> Optional[str]:
        if self.symbol:
            sql = f"    CONSTRAINT"
            if self.symbol:
                sql += f" {self.symbol}"
        else:
            sql = ""

        sql += " UNIQUE KEY"
        # TODO: handle index_name and index_type
        key_parts = ",".join([p.unparse() for p in self.key_parts])
        sql += f" ({key_parts})"
        return sql

    def key_name(self):
        if len(self.key_parts) != 1:
            raise Exception(f"unhandled: length of key parts is not 1: {self}")
        else:
            return self.key_parts[0].col_name


class ReferenceOption(str, Enum):
    RESTRICT = "RESTRICT"
    CASCADE = "CASCADE"
    SET_NULL = "SET NULL"
    NO_ACTION = "NO ACTION"
    SET_DEFAULT = "SET DEFAULT"


class ForeignKey(Node):
    """
    Syntax:

    [CONSTRAINT [symbol]] FOREIGN KEY
        [index_name] (col_name, ...)
        REFERENCES tbl_name (col_name,...)
        [ON DELETE reference_option]
        [ON UPDATE reference_option]

    reference_option:
        RESTRICT | CASCADE | SET NULL | NO ACTION | SET DEFAULT

    """

    def __init__(
            self,
            col_names: List[str],
            ref_tbl_name: str,
            ref_col_names: List[str],
            symbol: Optional[str] = None,
            index_name: Optional[str] = None,
            match: Optional[str] = None,
            on_delete: Optional[ReferenceOption] = None,
            on_update: Optional[ReferenceOption] = None,
            back_populates: Optional[str] = None,
            *,
            file: Optional[str] = None,
            position: Position = DUMMY_POSITION,
    ):
        super().__init__(file=file, position=position)
        self.col_names = col_names
        self.ref_tbl_name = ref_tbl_name
        self.ref_col_names = ref_col_names
        self.symbol = symbol
        self.index_name = index_name

        # HACK
        self.name = ""

        self.match = match
        self.on_delete = on_delete
        self.on_update = on_update

        # Added for SQLAlchemy
        self.back_populates = back_populates

    def dump(self):
        return {
            "class": self.__class__.__name__,
            "ref_tbl_name": self.ref_tbl_name,
            "ref_col_names": self.ref_col_names,
            "symbol": self.symbol,
            "index_name": self.index_name,
            "match": self.match,
            "on_delete": self.on_delete,
            "on_update": self.on_update,
            "back_populates": self.back_populates,
            "file": self.file,
            "position": self.position.dump()
        }

    def unparse(self):
        if self.symbol:
            s = f"    CONSTRAINT {self.symbol} FOREIGN KEY"
        else:
            s = "    FOREIGN KEY"

        if self.index_name:
            s += f" {self.index_name}"

        joined_col_names = ", ".join(self.col_names)
        s += f" ({joined_col_names})"

        joined_ref_col_names = ", ".join(self.ref_col_names)
        s += f" REFERENCES {self.ref_tbl_name} ({joined_ref_col_names})"

        if self.match:
            s += f" MATCH {self.match}"

        if self.on_delete:
            s += f" ON DELETE {self.on_delete.value}"

        if self.on_update:
            s += f" ON UPDATE {self.on_update.value}"

        return s

    def render(self) -> Optional[str]:
        return self.unparse()

    def to_alchemy(self):
        """
        e.g.,

        class User(Base):
            __tablename__ = "users"

            id = Column(Integer, primary_key=True, index=True)
            ...
            items = relationship("Item", back_populates="owner")

        class Item(Base):
            __tablename__ = "items"

            id = Column(Integer, primary_key=True, index=True)
            ...
            owner_id = Column(Integer, ForeignKey("users.id"))

            owner = relationship("User", back_populates="items")

        :return:
        """
        # back_populates = self.belonged_table.tbl_name.split("_")[1]

        # owner = relationship("User", back_populates="items")

        rel_name = self.get_relation_name()
        return f'    {rel_name} = relationship("{self.ref_tbl_name}", back_populates="{self.index_name}")'

    def get_relation_name(self):
        if len(self.col_names):
            rel_name = self.col_names[0].rstrip("_id") + "_rel"
            return rel_name
        else:
            raise Exception(f"multi relationship names unhandled: {self.col_names}")
