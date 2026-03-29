"""
Testing the "result_classes.py" module
"""

import logging
import unittest

from parameterized import parameterized

from pyrelatics2.result_classes import ExportResult
from pyrelatics2.result_classes import ImportElement
from pyrelatics2.result_classes import ImportElementActions
from pyrelatics2.result_classes import ImportMessage
from pyrelatics2.result_classes import ImportMessageStatus
from pyrelatics2.result_classes import ImportResult

# pylint: disable=missing-class-docstring,missing-function-docstring,line-too-long,too-few-public-methods,too-many-positional-arguments

logging.getLogger("pyrelatics2.result_classes").setLevel(logging.ERROR)


def determine_output_helper(instance: object):
    """Handy way to find current str() value"""
    print(f"\n> instance as repr: {repr(instance)}")
    print(f"> instance as str : {bytes(str(instance), 'utf-8')}")


class TestExportResult(unittest.TestCase):
    def test_from_suds_none(self):
        # Arrange
        # Act
        instance = ExportResult.from_suds(None)  # type: ignore

        # determine_output_helper(instance)  # Handy way to find current results

        # Assert
        self.assertEqual(repr(instance), "ExportResult(data=None, documents={})", "wrong __repr__()")
        self.assertEqual(str(instance), "ERROR: None\n", "wrong __str__()")


class TestImportResult(unittest.TestCase):
    def test_from_suds_none(self):
        # Arrange
        # Act
        instance = ImportResult.from_suds(None)  # type: ignore

        # determine_output_helper(instance)  # Handy way to find current results

        # Assert
        self.assertEqual(
            repr(instance),
            "ImportResult(messages=[], elements=[], total_rows=None, elapsed_time=None)",
            "wrong __repr__()",
        )
        self.assertEqual(str(instance), "ERROR: None\n", "wrong __str__()")


class TestImportMessage(unittest.TestCase):
    @parameterized.expand(
        [
            (
                "13:17:54",
                "Progress",
                "Successfully created ImportLog.",
                0,
                "ImportMessage(time=datetime.time(13, 17, 54), status='Progress', message='Successfully created ImportLog.', row=0)",
                "13:17:54  00000  \x1b[34mProgress\x1b[39m  Successfully created ImportLog.",
            ),
            (
                "13:27:54",
                "Comment",
                "Cleared 0 empty row(s) from the table.",
                0,
                "ImportMessage(time=datetime.time(13, 27, 54), status='Comment', message='Cleared 0 empty row(s) from the table.', row=0)",
                "13:27:54  00000  \x1b[39mComment \x1b[39m  Cleared 0 empty row(s) from the table.",
            ),
        ]
    )
    def test_import_message(
        self, time: str, status: ImportMessageStatus, message: str, row: int, expected_repr: str, expected_str: str
    ):
        """Test the creation of an ImportMessage instance, including conversing the string time to a datetime.time"""
        # Arrange
        # Act
        instance = ImportMessage(time=time, status=status, message=message, row=row)

        # determine_output_helper(instance)  # Handy way to find current results

        # Assert
        self.assertEqual(repr(instance), expected_repr, "wrong __repr__()")
        self.assertEqual(str(instance), expected_str, "wrong __str__()")


class TestImportElement(unittest.TestCase):
    @parameterized.expand(
        [
            (
                "Add",
                "4ed6d088-e236-4b6b-8cc6-aa0327e7b402",
                "VVRGLTgiPz4KPEltcG9yd",
                "ImportElement(action='Add', id='4ed6d088-e236-4b6b-8cc6-aa0327e7b402', foreign_key='VVRGLTgiPz4KPEltcG9yd')",
                "Add     4ed6d088-e236-4b6b-8cc6-aa0327e7b402  VVRGLTgiPz4KPEltcG9yd",
            ),
            (
                "Update",
                "4e4d7f01-c881-4666-b078-9e5ec05e53ad",
                "YW1lPSJBY3RpZSBPQXV0aDI",
                "ImportElement(action='Update', id='4e4d7f01-c881-4666-b078-9e5ec05e53ad', foreign_key='YW1lPSJBY3RpZSBPQXV0aDI')",
                "Update  4e4d7f01-c881-4666-b078-9e5ec05e53ad  YW1lPSJBY3RpZSBPQXV0aDI",
            ),
        ]
    )
    def test_import_element(
        self, action: ImportElementActions, guid: str, foreign_key: str, expected_repr: str, expected_str: str
    ):
        """Test the creation of an ImportMessage instance, including conversing the string time to a datetime.time"""
        # Arrange
        # Act
        instance = ImportElement(action=action, id=guid, foreign_key=foreign_key)

        # determine_output_helper(instance)  # Handy way to find current results

        # Assert
        self.assertEqual(repr(instance), expected_repr, "wrong __repr__()")
        self.assertEqual(str(instance), expected_str, "wrong __str__()")

    # def test_import_result(self, ....):
    #     # Still to be done


if __name__ == "__main__":
    # unittest.main()
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
