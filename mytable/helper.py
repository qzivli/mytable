from mytable.config import IdentifierType, identifier_length_limits


def sort_dict(d: dict, key=lambda x: x[1], reverse: bool = True) -> dict:
    return dict(sorted(d.items(), key=key, reverse=reverse))


def check_identifier_length(identifier_type, characters):
    if identifier_type not in identifier_length_limits:
        raise TypeError(f"Unknown identifier type: {identifier_type}")

    limit = identifier_length_limits[identifier_type]
    if len(characters) > limit:
        raise ValueError(f"maximum identifier length ({limit}) exceeded: {characters!r}")
