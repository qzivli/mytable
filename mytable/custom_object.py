__all__ = ["set_lift_tables"]

example_lift_tables = {
    "F001": {
        "project_code": ["customObject", "CF19", "detailBusinessCode"],
        "project_text": ["customObject", "CF19", "text"],
    },
    None: {

    }
}

lift_tables = example_lift_tables


def set_lift_tables(tables):
    global lift_tables
    lift_tables = tables
