"""
Testing the "utils.py" module
"""

import unittest

from parameterized import parameterized
from suds.sax.text import Text
from suds.sudsobject import Object as SudsObject

from pyrelatics2.utils import suds_get

# pylint: disable=missing-class-docstring,missing-function-docstring,line-too-long,too-few-public-methods


def make_sample_suds_object() -> SudsObject:
    """Create a sample SudsObject with nested attributes for use in tests."""
    child = SudsObject()
    child.name = "child_name"
    child.text_value = Text("hello from suds text")

    obj = SudsObject()
    obj.title = "root_title"
    obj.count = 42
    obj.child = child

    return obj


class TestSudsGet(unittest.TestCase):
    def setUp(self):
        self.obj = make_sample_suds_object()

    # ------------------------------------------------------------------
    # obj is None
    # ------------------------------------------------------------------

    def test_obj_none_returns_none(self):
        result = suds_get(None, "title")
        self.assertIsNone(result)

    def test_obj_none_list_path_returns_none(self):
        result = suds_get(None, ["child", "name"])
        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # path as str
    # ------------------------------------------------------------------

    @parameterized.expand(
        [
            ("title", "root_title"),
            ("count", 42),
        ]
    )
    def test_str_path_returns_value(self, attribute: str, expected):
        result = suds_get(self.obj, attribute)
        self.assertEqual(result, expected)

    def test_str_path_missing_attribute_returns_none(self):
        result = suds_get(self.obj, "nonexistent")
        self.assertIsNone(result)

    def test_str_path_text_value_converted_to_str(self):
        result = suds_get(self.obj.child, "text_value")
        self.assertIsInstance(result, str)
        self.assertEqual(result, "hello from suds text")

    # ------------------------------------------------------------------
    # path as list[str]
    # ------------------------------------------------------------------

    def test_list_path_single_element_returns_value(self):
        result = suds_get(self.obj, ["title"])
        self.assertEqual(result, "root_title")

    def test_list_path_nested_returns_value(self):
        result = suds_get(self.obj, ["child", "name"])
        self.assertEqual(result, "child_name")

    def test_list_path_missing_intermediate_returns_none(self):
        result = suds_get(self.obj, ["nonexistent", "name"])
        self.assertIsNone(result)

    def test_list_path_missing_leaf_returns_none(self):
        result = suds_get(self.obj, ["child", "nonexistent"])
        self.assertIsNone(result)

    def test_list_path_text_value_converted_to_str(self):
        result = suds_get(self.obj, ["child", "text_value"])
        self.assertIsInstance(result, str)
        self.assertEqual(result, "hello from suds text")

    # ------------------------------------------------------------------
    # path as list vs str equivalence
    # ------------------------------------------------------------------

    def test_str_path_and_single_element_list_path_are_equivalent(self):
        result_str = suds_get(self.obj, "title")
        result_list = suds_get(self.obj, ["title"])
        self.assertEqual(result_str, result_list)


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
