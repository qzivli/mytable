# MyTable - a SQL table parser with some extensions

> ⚠️ Project Status: In Progress
>
> This project is currently in progress and under active development. It is not yet considered stable or complete, and
significant changes and improvements may still be made.


MyTable is a SQL table parser with some extensions:

- Support Java generic syntax
- Transpile nested JSON data to simple SQL data type
- Generate SQLAlchemy models (deleted, on rewriting it)
- Generate Pydantic models (deleted, on rewriting it)


## Getting Started

Transpile one-to-many relationship to standard SQL statements:
```python
from mytable.transpiler import transpile_sql

text = r"""
CREATE TABLE Parent
(
    `id` INT AUTO_INCREMENT NOT NULL,
    `children` List<Child>,
    PRIMARY KEY (`id`)
);

CREATE TABLE Child
(
    `id` INT AUTO_INCREMENT NOT NULL,
    PRIMARY KEY (`id`)
);
"""

print(transpile_sql(text=text))

```

## Use-cases

A typical use-case is data pipeline integration. This project is designed to seamlessly integrate into data pipelines 
where there is a need to transpile custom SQL table definitions into standard SQL statements and generate Python 
validator classes.


## License

Copyright (c) 2024 Q. Ziv Li

MyTable is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
