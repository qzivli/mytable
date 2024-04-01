import enum

from dataclasses import dataclass


@dataclass
class Config:
    debug_mode: bool = True

    use_json: bool = False

    default_collate = "utf8mb4_0900_ai_ci"

    symbol_case_ignore: bool = False

    allow_primary_key_missing: bool = False

    # e.g., use Reimburse.formCode rather than Reimburse.id
    foreign_key_use_unique_code: bool = True

    base_alchemy_class_name: str = "AlchemyModel"
    base_pydantic_class_name: str = "BaseModel"

    to_alchemy_back_populates: bool = False

    inject_etl_date_col: bool = True
    etl_col_name: str = "etl_date"

    simplify_flag: bool = True


config = Config()


class IdentifierType(str, enum.Enum):
    DATABASE = "Database"
    TABLE = "Table"
    COLUMN = "Column"
    INDEX = "Index"
    CONSTRAINT = "Constraint"
    STORED_PROGRAM = "Stored Program"
    VIEW = "View"
    TABLESPACE = "Tablespace"
    SERVER = "Server"
    LOG_FILE_GROUP = "Log File Group"
    ALIAS = "Alias"
    COMPOUND_STATEMENT_LABEL = "Compound Statement Label"
    USER_DEFINED_VARIABLE = "User-Defined Variable"
    RESOURCE_GROUP = "Resource Group"


# https://dev.mysql.com/doc/refman/8.0/en/identifier-length.html
identifier_length_limits = {
    IdentifierType.DATABASE: 64,
    IdentifierType.TABLE: 64,
    IdentifierType.COLUMN: 64,
    IdentifierType.INDEX: 64,
    IdentifierType.CONSTRAINT: 64,
    IdentifierType.STORED_PROGRAM: 64,
    IdentifierType.VIEW: 64,
    IdentifierType.TABLESPACE: 64,
    IdentifierType.SERVER: 64,
    IdentifierType.LOG_FILE_GROUP: 64,
    IdentifierType.ALIAS: 256,
    IdentifierType.COMPOUND_STATEMENT_LABEL: 16,
    IdentifierType.USER_DEFINED_VARIABLE: 64,
    IdentifierType.RESOURCE_GROUP: 64,
}

MYSQL = "MySQL"
sql_dialect = MYSQL
