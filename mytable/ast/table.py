import copy
from typing import List, Union, Optional, Dict
from typing import TypeVar

from mytable.ast.base import Node, Position, DUMMY_POSITION, MyTableException
from mytable.ast.expression import Identifier, String
from mytable.ast.key import KeyPart, UniqueKey, ForeignKey, ReferenceOption, PrimaryKey, Index
from mytable.ast.statement import Statement
from mytable.ast.types import JavaType, SqlType, JavaList, complex_data_type, JavaAtom, JavaMap
from mytable.config import config

__all__ = [
    "Column", "CreateTable", "Replacement",
    "make_assoc_table_name",
]

alchemy_reserved_names = {"metadata", }

default_table_options = {
    "ENGINE": "InnoDB",
    "CHARSET": "utf8mb4",
}

# CREATE TABLE IF NOT EXISTS
inject_if_not_exists = False


def default_on_delete():
    return None
    # return ReferenceOption.CASCADE


types_to_simplify = {
    # type name to fields mapping
    "AmountInput": ["amount"],
    "OpenApiAmountDataDto": ["amount"],
    "DateTimeInput": ["startTime", "endTime"],
    "CityInput": ["departureText", "destinationText"],
}


def make_assoc_table_name(one, other):
    """Foo, Bar --> Bar_Foo_assoc
    """
    return "_".join(sorted([one, other])) + "_assoc"


def get_column(table, col_name):
    """Get a column object by name

    :param table: A table object
    :param col_name: column name
    :return: An instance of Column, or None if not found.
    """
    for col in table.columns.values():
        if col.col_name == col_name:
            return col

    return None


def merge_options(o1: dict, o2: dict, key):
    for k1, v1 in o1.items():
        if isinstance(k1, Identifier) and k1.value == key:
            t = v1.value
            for k2, v2 in o2.items():
                if isinstance(k2, Identifier) and k2.value == key:
                    merged = t + "_" + v2.value
                    v1.value = merged
    return None


class Replacement(Node):
    """
    Replace a composite column with some simple columns.
    """

    def __init__(
            self,
            original_column: "Column",
            new_columns: dict,
            *,
            file: Optional[str] = None,
            position: Position = DUMMY_POSITION
    ):
        super().__init__(file=file, position=position)
        self.original_column = original_column
        self.new_columns = new_columns

    def dump(self) -> dict:
        return {
            "class": self.__class__.__name__,
            "original_column": self.original_column,
            "new_columns": self.new_columns,
            "file": self.file,
            "position": self.position.dump()
        }

    def unparse(self) -> str:
        pass

    def render(self) -> Optional[str]:
        ls = [col.render() for col in self.new_columns.values()]
        return ",\n".join(ls)


class Column(Node):
    """
    Syntax:
      column_definition: {
        data_type [NOT NULL | NULL] [DEFAULT {literal | (expr)} ]
          [VISIBLE | INVISIBLE]
          [AUTO_INCREMENT] [UNIQUE [KEY]] [[PRIMARY] KEY]
          [COMMENT 'string']
          [COLLATE collation_name]
          [COLUMN_FORMAT {FIXED | DYNAMIC | DEFAULT}]
          [ENGINE_ATTRIBUTE [=] 'string']
          [SECONDARY_ENGINE_ATTRIBUTE [=] 'string']
          [STORAGE {DISK | MEMORY}]
          [reference_definition]
          [check_constraint_definition]
      | data_type
          [COLLATE collation_name]
          [GENERATED ALWAYS] AS (expr)
          [VIRTUAL | STORED] [NOT NULL | NULL]
          [VISIBLE | INVISIBLE]
          [UNIQUE [KEY]] [[PRIMARY] KEY]
          [COMMENT 'string']
          [reference_definition]
          [check_constraint_definition]
      }
    """

    def __init__(
            self,
            *,
            col_name: str,
            data_type: Union[SqlType, JavaType],
            nullable: bool = True,
            default=None,
            visible: bool = True,
            auto_increment: bool = False,
            unique: bool = False,
            primary: bool = False,
            enum_choices: Optional[str] = None,
            comment: Optional[str] = None,
            belonged_table=None,
            assoc_tbl_name=None,
            assoc_col_name=None,
            lift: bool = False,
            file: Optional[str] = None,
            position: Position = DUMMY_POSITION
    ):
        super().__init__(file=file, position=position)
        self.col_name = col_name
        self.data_type = data_type
        self.nullable = nullable
        self.default = default
        self.visible = visible
        self.auto_increment = auto_increment
        self.unique = unique
        self.primary = primary
        self.enum_choices = enum_choices
        self.comment = comment
        self.belonged_table = belonged_table
        self.assoc_tbl_name = assoc_tbl_name
        self.assoc_col_name = assoc_col_name
        self.lift = lift

        self.add_children(data_type)

    def dump(self):
        if hasattr(self.parent, "tbl_name"):
            tbl_name = self.parent.tbl_name
        else:
            tbl_name = ""

        return {
            "class": self.__class__.__name__,
            "col_name": self.col_name,
            "parent": tbl_name,
            "data_type": self.data_type,
            "nullable": self.nullable,
            "default": self.default,
            "visible": self.visible,
            "auto_increment": self.auto_increment,
            "unique": self.unique,
            "primary": self.primary,
            "enum_choices": self.enum_choices,
            "comment": self.comment,
            "assoc_tbl_name": self.assoc_tbl_name,
            "assoc_col_name": self.assoc_col_name,
            "file": self.file,
            "position": self.position.dump()
        }

    def unparse(self) -> str:
        s = f"    `{self.col_name}`"
        s += f" {self.data_type.unparse()}"
        if self.auto_increment:
            s += " AUTO_INCREMENT"

        if self.nullable:
            s += " NULL"
        else:
            s += " NOT NULL"

        if self.default:
            s += f" DEFAULT {self.default.unparse()}"

        if self.unique:
            s += " UNIQUE"

        if self.comment:
            s += f" COMMENT '{self.comment}'"

        return s

    def render(self) -> Optional[str]:
        if isinstance(self.data_type, JavaAtom):
            s = f"    `{self.col_name}_id` int"

            if self.nullable:
                s += " NULL"
            else:
                s += " NOT NULL"

            if self.unique:
                s += " UNIQUE"

            if self.comment:
                s += f" COMMENT '{self.comment}'"

            return s

        elif isinstance(self.data_type, JavaList):
            return None

        else:
            s = f"    `{self.col_name}`"

            # HACK:
            if self.col_name == "customObject" or self.col_name == "detailTotalAmount":
                t = complex_data_type(use_json=config.use_json)
            else:
                t = self.data_type.render()

            s += f" {t}"

            if self.auto_increment:
                s += " AUTO_INCREMENT"

            if self.nullable:
                s += " NULL"
            else:
                s += " NOT NULL"

            if self.default:
                s += f" DEFAULT {self.default.render()}"

            if self.unique:
                s += " UNIQUE"

            if self.comment:
                s += f" COMMENT '{self.comment}'"

            return s

    def handle_composite_type(self, template_tables: dict, collector: dict):
        """

        :return:
        """
        pass

    def update_foreign_keys(self):
        pass

    def get_ck_col(self):
        if self.parent.common_code is not None:
            ck: UniqueKey = self.parent.common_code
            ck_name = ck.key_name()
            return ck.parent.columns.get(ck_name)
        else:
            return None

    def generate_table(self, template_tables: dict, collector: dict):
        """
        - [x] generate child table
        - [ ] inject relationship
        - [ ] update table.depends ?

        owner_id = Column(Integer, ForeignKey("users.id"))
        owner = relationship("User", back_populates="items")

        :return:  Optional[CreateTable]
        """
        if template_tables is None:
            raise MyTableException("generate_table depends on template_tables")

        if isinstance(self.data_type, JavaType):

            if isinstance(self.data_type, JavaAtom):
                if config.simplify_flag and self.data_type.name in types_to_simplify:
                    column_names = types_to_simplify.get(self.data_type.name)
                    if len(column_names) > 1:
                        raise MyTableException(f"unhandled condition: {column_names}")

                    template_table = template_tables.get(self.data_type.name)
                    if template_table is None:
                        raise MyTableException(f"cannot get template table for {self.parent.tbl_name}.{self.col_name}")
                    tpl_col = get_column(template_table, column_names[0])
                    self.data_type = tpl_col.data_type
                    self.comment = tpl_col.comment
                return None

            elif isinstance(self.data_type, JavaList):
                # Generate sub-tables for column of type List<T>
                child_table_name = f"{self.parent.tbl_name}_{self.col_name}"
                template_table: Optional[CreateTable] = template_tables.get(self.data_type.element_type.name)
                if template_table is None:
                    raise MyTableException(f"cannot get template table {self.data_type.element_type.name!r}")

                comment = f"Generated from template table {template_table.tbl_name!r}, for {self.parent.tbl_name}.{self.col_name}"

                col_name = f"{self.parent.tbl_name}_id"

                fk_col_id = Column(
                    col_name=col_name,
                    data_type=SqlType(name="int", maximum=None),
                    comment=f"外键，指向{self.parent.tbl_name}（{self.parent.comment}）"
                )
                columns = template_table.columns.copy()
                columns[fk_col_id.col_name] = fk_col_id

                ref_tbl_name = self.parent.tbl_name
                # hard coded
                ref_col_name = "id"
                fk_constraint_id = ForeignKey(
                    index_name=self.col_name,
                    col_names=[col_name],
                    ref_tbl_name=ref_tbl_name,
                    ref_col_names=[ref_col_name],
                    on_delete=default_on_delete()
                )

                foreign_keys = template_table.foreign_keys + [fk_constraint_id]

                if self.parent.unique_code is not None:
                    col_name = f"{self.parent.tbl_name}_{self.parent.unique_code.key_name()}"
                    ref_tbl_name = self.parent.tbl_name
                    # hard coded
                    ref_col_name = self.parent.unique_code.key_name()
                    fk_constraint_code = ForeignKey(
                        index_name=self.parent.unique_code.index_name,
                        col_names=[col_name],
                        ref_tbl_name=ref_tbl_name,
                        ref_col_names=[ref_col_name],
                        on_delete=ReferenceOption.CASCADE
                    )
                    foreign_keys.append(fk_constraint_code)

                    parent_code_col = self.parent.columns.get(self.parent.unique_code.key_name())

                    fk_col_code = Column(col_name=col_name,
                                         data_type=parent_code_col.data_type,
                                         comment=f"外键，指向{self.parent.tbl_name}（{self.parent.comment}）")
                    columns[fk_col_code.col_name] = fk_col_code

                indexes = template_table.indexes

                print(f"self.parent.common_code {self.parent.common_code}")
                if self.parent.common_code is not None:
                    print(self.parent.common_code)
                    ck = self.parent.common_code
                    parent_ck_col = self.get_ck_col()
                    print(f"parent_ck_col: {parent_ck_col}")
                    ck_name = parent_ck_col.col_name
                    ck_col = Column(
                        col_name=ck_name,
                        data_type=parent_ck_col.data_type,
                        comment=parent_ck_col.comment,
                    )
                    columns[ck_name] = ck_col

                options = copy.deepcopy(template_table.table_options)

                if hasattr(self.parent, "options"):
                    merge_options(options, self.parent.options, "COMMENT")

                # generate a child table, and let it reference to this table
                child_table = CreateTable(
                    tbl_name=child_table_name,
                    columns=columns,
                    primary_key=template_table.primary_key,
                    indexes=indexes,
                    keys=template_table.keys,
                    foreign_keys=foreign_keys,
                    common_code=self.parent.common_code,
                    table_options=options,
                    partition_options=None,
                    comment=comment
                )
                child_table.set_parent_node(self.parent.parent)
                child_table.tweak()
                child_table.update_foreign_keys()
                child_table.update_refs()

                collector[child_table_name] = child_table

                for fk_col_id in child_table.columns.values():
                    if isinstance(fk_col_id, Replacement):
                        continue

                    if isinstance(fk_col_id.data_type, JavaList):
                        fk_col_id.generate_table(template_tables=template_tables, collector=collector)

                return child_table

            elif isinstance(self.data_type, JavaMap):
                pass
            else:
                return None
                # raise NotImplementedError("can not handle complex data yet")

        elif self.assoc_col_name is not None:
            assoc_table_name = make_assoc_table_name(one=self.parent.tbl_name, other=self.assoc_tbl_name)
            this_tbl = self.parent
            other_tbl = template_tables.get(self.assoc_tbl_name)
            other_col = get_column(other_tbl, self.assoc_col_name)

            if assoc_table_name in collector:
                assoc_table = collector[assoc_table_name]
                key = f"{self.assoc_tbl_name}_{self.assoc_col_name}"
                assoc_table.columns[key] = Column(col_name=key, data_type=other_col.data_type)
            else:
                assoc_table = _generate_assoc_table(assoc_table_name, this_tbl, other_tbl, this_col=self, other_col=other_col)
                assoc_table.parent = self.parent.parent
                collector[assoc_table_name] = assoc_table
        else:
            return None

    def update_assoc_table(self, template_tables: dict, collector: dict, collector2: dict):
        if self.assoc_col_name is not None:
            assoc_table_name = make_assoc_table_name(one=self.parent.tbl_name, other=self.assoc_tbl_name)
            this_tbl = self.parent
            other_tbl = template_tables.get(self.assoc_tbl_name)
            other_col = get_column(other_tbl, self.assoc_col_name)

            if assoc_table_name in collector:
                assoc_table = collector[assoc_table_name]
                key = f"{self.assoc_tbl_name}_{self.assoc_col_name}"
                assoc_table.columns[key] = Column(col_name=key, data_type=other_col.data_type)
                collector2[assoc_table_name] = assoc_table


def _generate_assoc_table(
        tbl_name: str,
        this_tbl,
        other_tbl,
        this_col,
        other_col
):
    options = {
        Identifier("COMMENT"): String(f"association table for {this_tbl!r} and {other_tbl!r}")
    }
    table = CreateTable(
        tbl_name=tbl_name,
        columns={},  # to be set
        primary_key=default_primary_key,
        foreign_keys=[],
        common_code=None,
        indexes=[],
        keys=[],
        table_options=options,
        partition_options=None,
        comment="many-to-many assoc table"
    )

    id_col = default_id_column
    id_col.parent = table

    left_key = f"{this_col.assoc_tbl_name}_{this_col.assoc_col_name}"
    gen_col = Column(
        col_name=left_key,
        data_type=other_col.data_type
    )
    gen_col.parent = table

    # right_key = f"{other_col.assoc_tbl_name}_{other_col.assoc_col_name}"
    # right_col = Column(col_name=right_key, data_type=this_col.data_type)
    # right_col.parent = table

    table.columns = {
        "id": id_col,
        left_key: gen_col,
        # right_key: right_col,
        # other_col.col_name: gen_other_col,
    }

    return table


default_id_column = Column(
    col_name="id",
    data_type=SqlType(name="int", maximum=None),
    nullable=False,
    auto_increment=True,
    unique=True,
    comment="generated primary key column"
)

default_primary_key = PrimaryKey(
    symbol=None,
    index_type=None,
    key_parts=[KeyPart(col_name='id', length=None, expr=None)],
    index_option=None
)


def make_parent_id_column(col_name: str):
    return Column(
        col_name=col_name,
        data_type=SqlType(name="int", maximum=None),
        nullable=False,
        unique=True
    )


default_parent_id_column = make_parent_id_column("parent_id")

CreateDefinition = TypeVar("CreateDefinition", bound=Union[Column, PrimaryKey, Index, UniqueKey, ForeignKey])


class Relationship(object):
    def __init__(self, name: str, child_type: str, name_in_child: str):
        self.name = name
        self.child_type = child_type
        self.name_in_child = name_in_child


def make_col_name(orig_name, val_field_name):
    """
    e.g., consumeTime, startTime -> consume_startTime ??

    :param orig_name:
    :param val_field_name:
    :return:
    """
    new_col_name = f"{orig_name}_{val_field_name}"
    return new_col_name


class CreateTable(Statement):
    """
    Syntax:

      CREATE [TEMPORARY] TABLE [IF NOT EXISTS] tbl_name
        (create_definition,...)
        [table_options]
        [partition_options]
    """

    def __init__(
            self,
            tbl_name: str,
            *,
            temporary: bool = False,
            if_not_exists: bool = False,
            columns: Dict[str, Union[Column, Replacement]],
            primary_key: Optional[PrimaryKey],
            indexes: List[Index],
            keys: List[UniqueKey],
            foreign_keys: List[ForeignKey],
            common_code: Optional[UniqueKey],
            table_options: dict,
            partition_options: dict,
            comment: str = "",
            file: Optional[str] = None,
            position: Position = DUMMY_POSITION
    ):
        super().__init__(file=file, position=position)
        self.tbl_name = tbl_name
        self.temporary = temporary
        self.if_not_exists = if_not_exists
        # (create_definition,...)
        self.columns = columns
        if not config.allow_primary_key_missing:
            assert primary_key is not None
        self.primary_key = primary_key
        self.indexes = indexes
        self.keys = keys
        self.foreign_keys = foreign_keys
        self.common_code = common_code
        # [table_options]
        self.table_options = table_options
        # [partition_options]
        self.partition_options = partition_options
        self.comment = comment

        self.add_children(*columns.values())
        self.add_children(primary_key)
        self.add_children(*indexes)
        self.add_children(*keys)
        self.add_children(*foreign_keys)

        self.unique_code = None
        "unique code for exchange data between different systems"

        self.update_unique_code()

        self.injected = False

        # update refs when JavaAtom found
        self.refs = set()

        # update children when JavaList found
        self.children = set()

        # if all columns are simple sql type
        self.is_simple: bool = False
        self.children_generated: bool = False

        self.relationships: List[Relationship] = []

        self.tweaked = False

        # 兼容之前调用self.definitions的代码
        self.definitions = []
        for c in self.columns.values():
            self.definitions.append(c)

        if self.primary_key:
            self.definitions.append(self.primary_key)

        for i in self.indexes:
            self.definitions.append(i)

        for k in self.keys:
            self.definitions.append(k)

        for fk in self.foreign_keys:
            self.definitions.append(fk)

        if self.common_code:
            self.definitions.append(self.common_code)

    def update_unique_code(self):
        for key in self.keys:
            if key.symbol == "__unique_code":
                self.unique_code = key

    def dump(self):
        return {
            "class": self.__class__.__name__,
            "tbl_name": self.tbl_name,
            "columns": {key: value.dump() for key, value in self.columns.items()},
            "primary_key": self.primary_key.dump(),
            "indexes": [index.dump() for index in self.indexes],
            "keys": [key.dump() for key in self.keys],
            "foreign_keys": [fk.dump() for fk in self.foreign_keys],
            "table_options": [option.dump() for option in self.table_options],
            "partition_options": [option.dump() for option in self.partition_options],
            "refs": self.refs,
            "children": self.children,
        }

    def unparse(self):
        pass

    def _format_options(self):
        lines = []
        seen_charset = False
        seen_collate = False
        for k, v in self.table_options.items():
            if isinstance(v, String):
                lines.append(f"{k.value} = '{v.value}'")
            else:
                lines.append(f"{k.value} = {v.value}")

            if k.value.upper() == "CHARSET":
                seen_charset = True

            if k.value.upper() == "COLLATE":
                seen_collate = True

        if not seen_charset:
            lines.append("CHARSET = utf8mb4")

        if not seen_collate:
            lines.append(f"COLLATE = {config.default_collate}")

        return "\n  ".join(lines)

    def render(self) -> Optional[str]:
        s = f"-- {self.comment}\n"
        s += "CREATE TABLE"
        if self.if_not_exists or inject_if_not_exists:
            s += " IF NOT EXISTS"
        s += f" `{self.tbl_name}`\n"

        s += "(\n"

        lines = []

        for col in self.columns.values():
            sql = col.render()
            if sql:
                lines.append(sql)

        if self.primary_key is None:
            msg = f"table {self.tbl_name} do not have a primary key"
            if config.allow_primary_key_missing:
                print("warning", msg)
            else:
                raise MyTableException(msg)
        else:
            pk = self.primary_key.render()
            assert pk
            lines.append(pk)

        for idx in self.indexes:
            sql = idx.render()
            if sql:
                lines.append(sql)

        for key in self.keys:
            sql = key.render()
            if sql:
                lines.append(sql)

        for fk in self.foreign_keys:
            sql = fk.render()
            if sql:
                lines.append(sql)

        s += ",\n".join(lines)

        if self.common_code is not None:
            # HACK:
            s += f",\n    INDEX (`{self.common_code.key_name()}`)"
            s += f"\n    #@@ __common_code (`{self.common_code.key_name()}`)"

        s += "\n)"
        # s += self.options.unparse()
        # FIXME: options should be a subtype of Node
        if self.table_options:
            s += " "
            s += self._format_options()
        s += ";\n\n\n"

        return s

    def find_foreign_key(self, index_name):
        for fk in self.foreign_keys:
            if fk.index_name == index_name:
                return fk

        return None

    def update_foreign_keys(self):
        for col in self.columns.values():
            if isinstance(col, Replacement):
                continue

            if isinstance(col.data_type, JavaAtom):
                if config.simplify_flag and col.data_type.name in types_to_simplify:
                    continue

                col_name = f"{col.col_name}_id"
                ref_tbl_name = col.data_type.name
                # hard coded
                ref_col_name = "id"

                fk = self.find_foreign_key(col.col_name)
                if fk is None:
                    fk = ForeignKey(index_name=col.col_name,
                                    col_names=[col_name],
                                    ref_tbl_name=ref_tbl_name,
                                    ref_col_names=[ref_col_name],
                                    on_delete=ReferenceOption.CASCADE)

                    self.foreign_keys.append(fk)
                    fk.set_parent_node(self)

    def update_refs(self):
        for fk in self.foreign_keys:
            self.refs.add(fk.ref_tbl_name)

    def set_depends(self):
        for col in self.columns.values():
            if isinstance(col, Replacement):
                continue

            if isinstance(col.data_type, JavaAtom):
                self.refs.add(col.data_type.name)  # TODO: remove this
                self.refs.add(col.data_type.name)
            elif isinstance(col.data_type, JavaList):
                self.refs.add(col.data_type.element_type.name)  # TODO: remove this
                self.children.add(col.data_type.element_type.name)

    def simplify(self, template_tables):
        """

        :param template_tables:
        :return:
        """
        for col in self.columns.values():
            if config.simplify_flag and isinstance(col.data_type, JavaAtom) and col.data_type.name in types_to_simplify:
                column_names = types_to_simplify.get(col.data_type.name)

                template_table = template_tables.get(col.data_type.name)
                if template_table is None:
                    raise MyTableException(f"cannot get template table for {self.tbl_name}.{col.col_name}")

                # TODO: name
                if len(column_names) == 1:
                    val_field_name = column_names[0]
                    column_name = val_field_name
                    tpl_col = get_column(template_table, column_name)
                    # self.data_type = tpl_col.data_type
                    nc = Column(col_name=col.col_name, data_type=tpl_col.data_type, comment=col.comment)
                    nc.parent = self

                    new_columns = {
                        column_name: nc
                    }
                else:
                    new_columns = {}
                    for val_field_name in column_names:
                        tpl_col = get_column(template_table, val_field_name)
                        new_col_name = make_col_name(orig_name=col.col_name, val_field_name=val_field_name)
                        nc = Column(col_name=new_col_name, data_type=tpl_col.data_type, comment=col.comment)
                        nc.parent = self

                        new_columns[val_field_name] = nc

                self.columns[col.col_name] = Replacement(original_column=col, new_columns=new_columns)

    def inject_etl_date(self, col_name: str):
        col = Column(
            col_name=col_name,
            data_type=SqlType(name="datetime", maximum=None),
            comment="injected column for recording ETL datetime"
        )
        col.belonged_table = self
        col.parent = self
        self.columns[col_name] = col

    def tweak(self):
        if config.inject_etl_date_col:
            self.inject_etl_date(config.etl_col_name)

        for col in self.columns.values():
            col.parent = self

        self.add_children(*self.definitions)

        if not self.comment:
            for name, value in self.table_options.items():
                if name.value.upper() == "COMMENT":
                    self.comment = value.value

        if self.tweaked:
            return
        else:
            self.add_children(*self.definitions)

            self.update_foreign_keys()
            self.set_depends()

            self.tweaked = True
