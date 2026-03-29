"""
Testing the "utils.py" module
"""

import unittest

from parameterized import parameterized
from suds.sax.text import Text
from suds.sudsobject import Object as SudsObject

from pyrelatics2.utils import suds_get
from pyrelatics2.utils import suds_get_as_list
from pyrelatics2.utils import suds_get_as_str

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


class TestSudsGetAsList(unittest.TestCase):
    def setUp(self):
        self.child = SudsObject()
        self.child.name = "child_name"
        self.child.text_value = Text("hello from suds text")

        self.obj = SudsObject()
        self.obj.title = "root_title"
        self.obj.single_item = SudsObject()
        self.obj.multi_item = [SudsObject(), SudsObject()]

    # ------------------------------------------------------------------
    # obj is None
    # ------------------------------------------------------------------

    def test_obj_none_returns_empty_list(self):
        result = suds_get_as_list(None, "title")
        self.assertEqual(result, [])

    # ------------------------------------------------------------------
    # missing attribute
    # ------------------------------------------------------------------

    def test_missing_attribute_returns_empty_list(self):
        result = suds_get_as_list(self.obj, "nonexistent")
        self.assertEqual(result, [])

    # ------------------------------------------------------------------
    # single (non-list) value is wrapped in a list
    # ------------------------------------------------------------------

    def test_str_value_wrapped_in_list(self):
        result = suds_get_as_list(self.obj, "title")
        self.assertEqual(result, ["root_title"])

    def test_suds_object_wrapped_in_list(self):
        result = suds_get_as_list(self.obj, "single_item")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIs(result[0], self.obj.single_item)

    def test_text_value_wrapped_in_list_as_str(self):
        result = suds_get_as_list(self.child, "text_value")
        self.assertEqual(result, ["hello from suds text"])
        self.assertIsInstance(result[0], str)

    # ------------------------------------------------------------------
    # existing list is returned as-is
    # ------------------------------------------------------------------

    def test_list_value_returned_unchanged(self):
        result = suds_get_as_list(self.obj, "multi_item")
        self.assertIs(result, self.obj.multi_item)
        self.assertEqual(len(result), 2)

    # ------------------------------------------------------------------
    # nested path
    # ------------------------------------------------------------------

    def test_nested_path_returns_wrapped_value(self):
        result = suds_get_as_list(self.obj, "single_item")
        self.assertIsInstance(result, list)

    def test_missing_nested_path_returns_empty_list(self):
        result = suds_get_as_list(self.obj, "nonexistent", "name")
        self.assertEqual(result, [])


class TestSudsGetAsStr(unittest.TestCase):
    def setUp(self):
        self.child = SudsObject()
        self.child.text_value = Text("hello from suds text")
        self.child.name = "child_name"

        self.obj = SudsObject()
        self.obj.title = "root_title"
        self.obj.count = 42
        self.obj.child = self.child

    # ------------------------------------------------------------------
    # obj is None
    # ------------------------------------------------------------------

    def test_obj_none_returns_none(self):
        result = suds_get_as_str(None, "title")
        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # missing attribute
    # ------------------------------------------------------------------

    def test_missing_attribute_returns_none(self):
        result = suds_get_as_str(self.obj, "nonexistent")
        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # str value is returned as-is
    # ------------------------------------------------------------------

    def test_str_value_returned_unchanged(self):
        result = suds_get_as_str(self.obj, "title")
        self.assertEqual(result, "root_title")
        self.assertIsInstance(result, str)

    # ------------------------------------------------------------------
    # non-str value is cast to str
    # ------------------------------------------------------------------

    def test_int_value_cast_to_str(self):
        result = suds_get_as_str(self.obj, "count")
        self.assertEqual(result, "42")
        self.assertIsInstance(result, str)

    # ------------------------------------------------------------------
    # Text value is converted to str
    # ------------------------------------------------------------------

    def test_text_value_converted_to_str(self):
        result = suds_get_as_str(self.child, "text_value")
        self.assertEqual(result, "hello from suds text")
        self.assertIsInstance(result, str)

    # ------------------------------------------------------------------
    # nested path
    # ------------------------------------------------------------------

    def test_nested_path_returns_value(self):
        result = suds_get_as_str(self.obj, "child", "name")
        self.assertEqual(result, "child_name")

    def test_nested_missing_path_returns_none(self):
        result = suds_get_as_str(self.obj, "nonexistent", "name")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
