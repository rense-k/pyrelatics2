"""
Testing the "client.py" module
"""

import os
import unittest
from uuid import UUID

from pyrelatics2.client import USER_AGENT
from pyrelatics2.client import RelaticsWebservices

# from parameterized import parameterized


# pylint: disable=missing-class-docstring,missing-function-docstring,line-too-long,too-few-public-methods


def determine_output_helper(instance: object):
    """Handy way to find current str() value"""
    print(f"\n> instance as repr: {repr(instance)}")
    print(f"> instance as str : {bytes(str(instance), 'utf-8')}")


class TestRelaticsWebservices(unittest.TestCase):
    def test_init_simple_str(self):
        # Arrange
        # Act
        instance = RelaticsWebservices("Python", "9b167eea-d546-49c3-8cd0-1da09e7e9177")

        # Assert
        self.assertEqual(instance.hostname, "python.relaticsonline.com")
        self.assertEqual(instance.wsdl_url, "https://python.relaticsonline.com/DataExchange.asmx?wsdl")
        self.assertEqual(instance.workspace_id, "9b167eea-d546-49c3-8cd0-1da09e7e9177")
        self.assertEqual(
            repr(instance.identification), "{'Identification': {'Workspace': '9b167eea-d546-49c3-8cd0-1da09e7e9177'}}"
        )
        self.assertEqual(instance.user_agent, USER_AGENT)
        self.assertEqual(instance.keep_zip_file, False)

    def test_init_simple_uuid(self):
        # Arrange
        # Act
        instance = RelaticsWebservices("Python", UUID("9b167eea-d546-49c3-8cd0-1da09e7e9177"))

        # Assert
        self.assertEqual(instance.hostname, "python.relaticsonline.com")
        self.assertEqual(instance.wsdl_url, "https://python.relaticsonline.com/DataExchange.asmx?wsdl")
        self.assertEqual(instance.workspace_id, "9b167eea-d546-49c3-8cd0-1da09e7e9177")
        self.assertEqual(
            repr(instance.identification), "{'Identification': {'Workspace': '9b167eea-d546-49c3-8cd0-1da09e7e9177'}}"
        )
        self.assertEqual(instance.user_agent, USER_AGENT)
        self.assertEqual(instance.keep_zip_file, False)

    def test_init_advanced(self):
        # Arrange
        # Act
        instance = RelaticsWebservices("Python", "285b8253-3bc6-4252-ae53-049b8514fd18", "dispersed-unselfish-tacky")

        # Assert
        self.assertEqual(instance.hostname, "python.relaticsonline.com")
        self.assertEqual(instance.wsdl_url, "https://python.relaticsonline.com/DataExchange.asmx?wsdl")
        self.assertEqual(instance.workspace_id, "285b8253-3bc6-4252-ae53-049b8514fd18")
        self.assertEqual(
            repr(instance.identification), "{'Identification': {'Workspace': '285b8253-3bc6-4252-ae53-049b8514fd18'}}"
        )
        self.assertEqual(instance.user_agent, "dispersed-unselfish-tacky")
        self.assertEqual(instance.keep_zip_file, False)

    def test_init_exception_company_empty(self):
        with self.assertRaises(ValueError):
            RelaticsWebservices("", "fb8267ee-8032-4557-8062-c48d5fd4ff9a")

    def test_init_exception_workspace_empty(self):
        with self.assertRaises(ValueError):
            RelaticsWebservices("Python", "")

    def test_init_logging_warning_workspace_non_guid(self):
        with self.assertLogs("pyrelatics2.client", level="WARNING") as context:
            RelaticsWebservices("Python", "this_is_not_a_guid")

        expected_str = [
            "WARNING:pyrelatics2.client:"
            "The supplied workspace ID isn't a GUID. Make sure the workspace has an overridden 'URL' in Relatics."
        ]
        self.assertEqual(context.output, expected_str)

    def test_get_report_exception_operation_empty(self):
        with self.assertRaises(ValueError) as context:
            RelaticsWebservices("Python", "fb8267ee-8032-4557-8062-c48d5fd4ff9a").get_result("")
        self.assertEqual(str(context.exception), "Supplied operation_name is empty.")

    def test_run_import_exception_operation_empty(self):
        with self.assertRaises(ValueError) as context:
            RelaticsWebservices("Python", "fb8267ee-8032-4557-8062-c48d5fd4ff9a").run_import("", "aa.xml")
        self.assertEqual(str(context.exception), "Supplied operation_name is empty.")

    def test_run_import_exception_data_empty(self):
        with self.assertRaises(ValueError) as context:
            RelaticsWebservices("Python", "fb8267ee-8032-4557-8062-c48d5fd4ff9a").run_import(
                "ascertain-pang-unripe", ""
            )
        self.assertEqual(str(context.exception), "Supplied data is empty.")

    def test_run_import_exception_documents_duplicates(self):
        filename = "frequent-rehab-scary.jpg"

        with self.assertRaises(ValueError) as context:
            RelaticsWebservices("Python", "fb8267ee-8032-4557-8062-c48d5fd4ff9a").run_import(
                operation_name="ascertain-pang-unripe",
                data="tributary-maturely-recoil.xml",
                documents=[filename, os.path.join("pyramid-from-bagpipe", filename)],
            )
        self.assertEqual(str(context.exception), "Duplicate filenames in document list.")


if __name__ == "__main__":
    # unittest.main()
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
