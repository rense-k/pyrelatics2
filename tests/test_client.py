"""
Testing the "client.py" module
"""

import os
import unittest
from uuid import UUID

from parameterized import parameterized
from suds.plugin import MessageContext
from suds.sax.element import Element

from pyrelatics2.client import USER_AGENT
from pyrelatics2.client import AddParametersPlugin
from pyrelatics2.client import RelaticsWebservices
from pyrelatics2.client import is_valid_uuid

# pylint: disable=missing-class-docstring,missing-function-docstring,line-too-long,too-few-public-methods


def determine_output_helper(instance: object):
    """Handy way to find current str() value"""
    print(f"\n> instance as repr: {repr(instance)}")
    print(f"> instance as str : {bytes(str(instance), 'utf-8')}")


class TestRelaticsWebservices(unittest.TestCase):
    @parameterized.expand(
        [
            ("", False),
            ("9b167eea-d546-49c3-8cd0-1da09e7e9177", True),
        ]
    )
    def test_is_valid_uuid(self, input_s: str, expected_result: bool):
        # Arrange
        # Act
        result = is_valid_uuid(input_s)

        # Assert
        self.assertEqual(result, expected_result)

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


class TestAddParametersPlugin(unittest.TestCase):
    NS_RELATICS = "http://www.relatics.com/"
    NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"

    def _make_context(self) -> MessageContext:
        """Build a minimal fake SOAP envelope wrapped in a MessageContext."""
        envelope = Element("Envelope")
        envelope.addPrefix("soapenv", self.NS_SOAP)
        envelope.addPrefix("rel", self.NS_RELATICS)
        envelope.setPrefix("soapenv")

        body = Element("Body", parent=envelope)
        body.setPrefix("soapenv")
        envelope.append(body)

        get_result = Element("GetResult", parent=body)
        get_result.addPrefix("rel", self.NS_RELATICS)
        get_result.setPrefix("rel")
        body.append(get_result)

        ctx = MessageContext()
        ctx.envelope = envelope
        return ctx

    def test_parameters_are_injected(self):
        ctx = self._make_context()
        AddParametersPlugin({"a": "b", "c": "d"}).marshalled(ctx)

        # Navigate: Envelope -> Body -> GetResult
        body = ctx.envelope.getChild("Body")
        get_result = body[0]

        # Outer <Parameters> must be the first (and only) child of <GetResult>
        outer_params = get_result[0]
        self.assertEqual(outer_params.name, "Parameters", "Outer Parameters element missing")

        # Inner <Parameters> must be a child of the outer one
        inner_params = outer_params[0]
        self.assertEqual(inner_params.name, "Parameters", "Inner Parameters element missing")

        # Both Parameter children must be present with the correct attributes
        param_elems = inner_params.getChildren()
        self.assertEqual(len(param_elems), 2)
        self.assertEqual(param_elems[0].name, "Parameter")
        self.assertEqual(param_elems[0].get("Name"), "a")
        self.assertEqual(param_elems[0].get("Value"), "b")
        self.assertEqual(param_elems[1].name, "Parameter")
        self.assertEqual(param_elems[1].get("Name"), "c")
        self.assertEqual(param_elems[1].get("Value"), "d")

    def test_parameters_none_omits_parameters_block(self):
        ctx = self._make_context()
        AddParametersPlugin(None).marshalled(ctx)

        body = ctx.envelope.getChild("Body")
        get_result = body[0]
        self.assertEqual(get_result.getChildren(), [], "Parameters element should not be present when parameters=None")

    def test_parameters_empty_dict_omits_parameters_block(self):
        ctx = self._make_context()
        AddParametersPlugin({}).marshalled(ctx)

        body = ctx.envelope.getChild("Body")
        get_result = body[0]
        self.assertEqual(get_result.getChildren(), [], "Parameters element should not be present when parameters={}")


if __name__ == "__main__":
    # unittest.main()
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
