from typing import overload

from suds.sax.text import Text
from suds.sudsobject import Object as SudsObject


def suds_get(obj: SudsObject | None, *paths: str) -> SudsObject | str | None | list[SudsObject]:
    """
    Safely get the attribute with the given path from a SudsObject. Additionally convert any sax.text object
    into a regular string.

    Args:
        obj: The SudsObject to be queried
        path: The query path to the desired attribute

    Returns:
        The attribute value or None if not found
    """
    if obj is None:
        return None

    current = obj

    # For backward compatibility when `*paths` could be `list[str]`
    if len(paths) == 1 and isinstance(paths[0], list):
        paths = tuple(paths[0])

    # Iterate through the the path
    for attribute_name in paths:
        current = getattr(current, attribute_name, None)

    # Convert any sax.text objects into regular string
    if isinstance(current, Text):  # type: ignore
        current = str(current)

    # Return the result
    return current


def suds_get_as_list(obj: SudsObject | None, *paths: str) -> list[SudsObject] | list[SudsObject | str]:
    """
    Safely get the attribute with the given path from a SudsObject and return is as a list.

    Handy since suds won't return a list with a single item as a list, but as the object directly. By forcing it to be
    a list, you can safely iterate over it.

    Args:
        obj: The SudsObject to be queried
        path: The query path to the desired attribute

    Returns:
        The list containing the attribute values or an empty list if not found
    """
    if obj is None:
        return []

    current = suds_get(obj, *paths)

    if isinstance(current, list):
        result = current
    elif current is None:
        result = []
    else:
        result = [current]

    return result


@overload
def suds_get_as_str(obj: SudsObject, *paths: str) -> str | None: ...


@overload
def suds_get_as_str(obj: None, *paths: str) -> None: ...


def suds_get_as_str(obj: SudsObject | None, *paths: str) -> str | None:
    """
    Safely get the attribute with the given path from a SudsObject and return is as a string.

    Args:
        obj: The SudsObject to be queried
        path: The query path to the desired attribute

    Returns:
        The attribute value or None if not found. If the attribute was not a str, it will be
        cast into a str. Beware to expect this behavior.
    """
    if obj is None:
        return None

    current = suds_get(obj, *paths)

    if isinstance(current, str):
        result = current
    elif current is None:
        result = None
    else:
        result = str(current)

    return result
