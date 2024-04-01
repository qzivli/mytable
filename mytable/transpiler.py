from typing import Any, Dict
import io

from pygraph.classes.digraph import digraph

from mytable.ast.table import Column, CreateTable
from mytable.ast.types import SqlType
from mytable.helper import sort_dict
from mytable.parser import parse_sql_file, parse_sql

should_simplify = {
    "AmountInput": {"field": "amount", "type": "decimal", "nullable": False},
}
simplify_policy = "field"


def simplify_custom_type(name: str):
    if simplify_policy == "field":
        return custom_type_to_field(name)
    else:
        return custom_type_to_json(name)


def custom_type_to_field(type_name: str):
    if type_name in should_simplify:
        info = should_simplify[type_name]
        return Column(
            col_name=info["field"],
            data_type=SqlType(name=info["type"], maximum=None),
            nullable=info["nullable"]
        )
    else:
        return None


def custom_type_to_json(type_name: str):
    if type_name in should_simplify:
        info = should_simplify[type_name]
        return Column(
            col_name=info["field"],
            data_type=SqlType(name="JSON", maximum=None),
            nullable=info["nullable"]
        )
    else:
        return None


def write_tables(tables: Dict[str, CreateTable], output_file: str, ranks: Dict[str, float]):
    rendered_tables = {}

    for name, table in tables.items():
        sql = table.render()
        rendered_tables[name] = sql + "\n"

    with open(output_file, mode="w") as fw:
        for k, v in ranks.items():
            fw.write(rendered_tables[k])

        for k, v in rendered_tables.items():
            if k not in ranks:
                fw.write(v)


def extract_tables(tree):
    tables = {}

    def flatten(tree):
        for node in tree.nodes:
            if isinstance(node, CreateTable):
                tables[node.tbl_name] = node
            elif hasattr(node, "nodes"):
                flatten(node)

    flatten(tree)

    return tables


def get_tables(sql_file: str) -> Dict[str, CreateTable]:
    """
    Parse a SQL file, extract CREATE TABLE statements.

    :param sql_file:
    :return:
    """
    tree = parse_sql_file(sql_file)
    tables = extract_tables(tree)
    return tables


def generate_create_stmts(fw, tables: dict, ranks: dict):
    for k, v in ranks.items():
        fw.write(tables[k])

    for k, v in tables.items():
        if k not in ranks:
            fw.write(v)


def table_dependency_scores(tables: Dict[str, CreateTable]) -> Dict[str, int]:
    """
    计算table的依赖得分，被直接和间接依赖的越多的table，得分越高。

    :param tables:
    :return:
    """
    dg = digraph()
    nodes = list(tables.keys())
    dg.add_nodes(nodes)
    for name, table in tables.items():
        for ref in table.refs:
            dg.add_edge((name, ref))

    ranks = dict.fromkeys(dg.nodes(), 1)

    def toplevel_inc():
        for edge in dg.edges():
            a, b = edge
            # a依赖b，b加分
            ranks[b] += ranks[a]
            # 递归更新b的所有间接依赖的得分
            recur_inc(edge)

    def recur_inc(cmp_edge):
        for edge in dg.edges():
            # 避免重复计算
            if edge != cmp_edge:
                a, b = edge
                if a == cmp_edge[1]:
                    ranks[b] += ranks[a]
                    recur_inc(edge)

    toplevel_inc()

    return sort_dict(ranks, key=lambda x: x[1])


def generate_drop_stmts(fw, tables: dict, ranks: dict, use_drop_cascade_syntax: bool = False):
    def gen(tbl_name):
        if use_drop_cascade_syntax:
            return f"DROP TABLE IF EXISTS {tbl_name} CASCADE;\n"
        else:
            return f"DROP TABLE IF EXISTS {tbl_name};\n"

    # small to big
    r = sort_dict(ranks, reverse=True)
    for k, v in r.items():
        fw.write(gen(k))

    for k, v in tables.items():
        if k not in ranks:
            fw.write(gen(k))


def get_processed_tables(template_tables: Dict[str, CreateTable]):
    generated_tables = template_tables.copy()

    for name, table in template_tables.items():
        table.simplify(template_tables)
        for col in table.columns.values():
            if isinstance(col, Column):
                col.generate_table(template_tables, generated_tables)

    collector2 = {}
    # special case for many-to-many assoc table
    for name, table in generated_tables.items():
        for col in table.columns.values():
            if isinstance(col, Column):
                col.update_assoc_table(template_tables, generated_tables, collector2)

    # merge
    for name, table in collector2.items():
        generated_tables[name] = table

    return generated_tables


def transpile_sql(
        text: str,
        drop_table_if_exists: bool = False,
        use_drop_cascade_syntax: bool = False,
) -> str:
    tree = parse_sql(text)
    template_tables = extract_tables(tree)

    rendered_tables = {}
    generated_tables = get_processed_tables(template_tables)

    for name, table in generated_tables.items():
        rendered_tables[name] = table.render()

    scores = table_dependency_scores(generated_tables)
    memory_file = io.StringIO()
    if drop_table_if_exists:
        generate_drop_stmts(memory_file, rendered_tables, scores, use_drop_cascade_syntax)

    generate_create_stmts(memory_file, rendered_tables, scores)

    return memory_file.getvalue()


def transpile_sql_file(
        input_file: str,
        output_file: str,
        drop_table_if_exists: bool = False,
        use_drop_cascade_syntax: bool = False,
):
    """
    Transpile custom(extended) SQL into pure standard SQL.

    :param input_file:
    :param output_file:
    :param drop_table_if_exists:
    :param use_drop_cascade_syntax:
    :return:
    """
    template_tables = get_tables(input_file)
    rendered_tables = {}
    generated_tables = get_processed_tables(template_tables)

    for name, table in generated_tables.items():
        rendered_tables[name] = table.render()

    scores = table_dependency_scores(generated_tables)
    with open(output_file, mode="w") as fw:
        if drop_table_if_exists:
            generate_drop_stmts(fw, rendered_tables, scores, use_drop_cascade_syntax)

        generate_create_stmts(fw, rendered_tables, scores)
