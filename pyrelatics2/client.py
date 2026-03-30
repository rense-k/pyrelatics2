import json
import os
import sys
from base64 import b64encode
from datetime import datetime
from datetime import timedelta
from http.client import HTTPSConnection
from logging import getLogger
from platform import machine
from platform import platform
from platform import python_version
from pprint import pformat
from tempfile import gettempdir
from typing import Literal
from typing import TypeAlias
from typing import TypedDict
from typing import overload
from uuid import UUID
from zipfile import ZipFile

from suds.client import Client
from suds.plugin import MessageContext
from suds.plugin import MessagePlugin
from suds.sax.document import Document
from suds.sax.element import Element
from suds.sudsobject import Object as SudsObject

from .exceptions import TokenRequestError
from .result_classes import ExportResult
from .result_classes import ImportResult
from .version import __version__

log = getLogger(__name__)


# Type aliases
ParametersOrNone: TypeAlias = None | dict[str, str]


class TokenData(TypedDict):
    """Simple immutable dict containing token information"""

    token: str
    """The actual token"""
    expires_on: datetime
    """Expire time of the token"""


# Constants
TOKEN_PATH = "/oauth2/token"
IMPORT_BASENAME = "pyrelatics_webservice"
SUPPORTED_EXTENSIONS = ["xlsx", "xlsm", "xlsb", "xls", "csv"]

USER_AGENT = (
    f"PyRelatics2/{__version__} "
    f"({platform()}; {machine()}; python-{python_version()}) "
    f"{os.path.split(sys.modules['__main__'].__file__)[1]}"  # pylint: disable=E1101
)


def is_valid_uuid(s: str) -> bool:
    """
    Check if the given string can be converted into a valid UUID.

    Args:
        workspace_id: The string to be checked.

    Returns:
        True if the string can be converted into a valid UUID, False otherwise.
    """
    try:
        UUID(s)
        return True
    except ValueError:
        return False


class ClientCredential:
    """
    Class containing OAuth2 client credentials and helper methods to get a token from the Relatics host.

    Args:
        client_id : The OAuth2 client_id
        client_secret : The OAuth2 client_secret
    """

    client_id: str
    client_secret: str
    tokens: dict[str, TokenData]

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tokens = {}

    def get_token(self, hostname: str, force_refresh: bool = False, user_agent: str = USER_AGENT) -> str:
        """
        Get the token for the given hostname

        Args:
            hostname : The Relatics hostname from where the token should be get.
            force_refresh : When True, force a new token to be requested, instead of trying to reuse an
                existing token. Defaults to False.
            user_agent : The user-agent used in the http request to Relatics. Since this name will show up in the
                logs in Relatics, it can be useful to specify a custom value. Defaults to USER_AGENT.

        Returns:
            str: Token for the given hostname
        """
        if (
            force_refresh is True
            or hostname not in self.tokens
            or (self.tokens[hostname]["expires_on"] - datetime.now()).seconds <= 300
        ):
            log.info("No previous token for %s, retrieving new token", hostname)
            self.retrieve_token(hostname, user_agent)
        else:
            log.info("Reuse previous token for %s", hostname)

        return self.tokens[hostname]["token"]

    def retrieve_token(self, hostname: str, user_agent: str = USER_AGENT) -> None:
        """_summary_

        Args:
            hostname : The Relatics hostname from where the token should be get.
            user_agent : The user-agent used in the http request to Relatics. Since this name will show up in the
                logs in Relatics, it can be useful to specify a custom value. Defaults to USER_AGENT.

        Raises:
            RuntimeError: When Relatics sends back an error response
            KeyError: When there is no token in the response from Relatics
        """
        requested_on = datetime.now()
        auth_credentials = b64encode(bytes(f"{self.client_id}:{self.client_secret}", "utf-8"))
        payload = "grant_type=client_credentials"
        headers = {
            "Authorization": f"Basic {auth_credentials.decode('utf-8')}",
            "Content-Type": "text/plain",
            "User-Agent": user_agent,
        }

        conn = HTTPSConnection(hostname)
        conn.request("POST", TOKEN_PATH, payload, headers)
        res = conn.getresponse()
        data = res.read()
        response = json.loads(data.decode("utf-8"))

        log.debug("Response from %s: %s", TOKEN_PATH, pformat(response, indent=2))

        if "error" in response:
            # Known errors:
            # * `invalid_client` (description=_"Client not found."_). Happens when:
            #   * An unknown client_id is submitted
            #   * An incorrect client_secret is submitted
            #   * The client_id is disabled in Relatics
            raise TokenRequestError(response)

        if "access_token" not in response:
            raise KeyError("Token request failed: No access_token was given.")

        # Store the token for later use
        self.tokens[hostname] = TokenData(
            token=response["access_token"],
            expires_on=requested_on + timedelta(seconds=response["expires_in"]),
        )


class AddParametersPlugin(MessagePlugin):  # pylint: disable=R0903
    """
    Plugin for Suds Client to add parameters to the request before sending to Relatics. Because parameters use
    attributes, they can not be defined through the default mechanisms within Suds.

    Args:
        parameters : Dictionary with the parameters
    """

    def __init__(self, parameters: ParametersOrNone):
        self.parameters = parameters

    def marshalled(self, context: MessageContext):
        if self.parameters:  # So not None nor an empty dict
            # Try to get "Parameters" element, or built when missing
            try:
                params = context.envelope.getChild("Body")[0].getChild("Parameters")[0]
            except (TypeError, IndexError, AttributeError):
                log.info("Adding parameters to SOAP request")
                root = context.envelope.getChild("Body")[0]
                root_prefix = root.findPrefix("http://www.relatics.com/")

                p_1 = Element("Parameters", parent=root)
                p_1.setPrefix(root_prefix)
                root.append(p_1)

                p_2 = Element("Parameters", parent=p_1)
                p_2.setPrefix(root_prefix)
                p_1.append(p_2)

                params = context.envelope.getChild("Body")[0].getChild("Parameters")[0]

            prefix = params.findPrefix("http://www.relatics.com/")

            # Add the parameters
            for param_name, param_value in self.parameters.items():
                elem = Element("Parameter", parent=params)
                elem.setPrefix(prefix)
                elem.set(name="Name", value=param_name)
                elem.set(name="Value", value=param_value)
                params.append(elem)

        log.debug("Final SOAP envelope: \n%s", context.envelope.str())


class RelaticsWebservices:
    """
    Class to communicate with Relatics webservices

    Args:
        company_subdomain : The company's subdomain (before ".relaticsonline.com")
        workspace_id : The ID of the Relatics workspace were the request will be send to
        user_agent : The user agent sent as part of the request. Will show up in the webservice-log in Relatics. Can
            be used to distinguished different applications.

    """

    company_subdomain: str
    """The company subdomain used in the full Relatics hostname"""
    workspace_id: str
    """The Relatics ID of the workspace to communicate with"""
    user_agent: str
    """The user agent that will show up in the Relatics webservice logs"""
    keep_zip_file: bool
    """Optionally keep the created zipfile. For debugging purpose only"""

    _client_cache: Client | None = None
    _default_headers: dict[str, str]

    def __init__(self, company_subdomain: str, workspace_id: UUID | str, user_agent: str = USER_AGENT):
        # Check whether mandatory arguments are given
        if company_subdomain == "":
            raise ValueError("The 'company_subdomain' can not be empty.")
        if workspace_id == "":
            raise ValueError("The 'workspace_id' can not be empty.")

        # Check if supplied workspace_id str can be converted into a GUID
        if isinstance(workspace_id, str) and not is_valid_uuid(workspace_id):
            log.warning(
                "The supplied workspace ID isn't a GUID. Make sure the workspace has an overridden 'URL' in Relatics."
            )

        # Store instance variables
        self.company_subdomain = company_subdomain
        self.workspace_id = str(workspace_id) if isinstance(workspace_id, UUID) else workspace_id
        self.user_agent = user_agent
        self.keep_zip_file = False  # Optionally keep the created zipfile. For debugging purpose only

        # Initialize reusable instance variables
        self._default_headers = {"User-Agent": self.user_agent}

    @property
    def wsdl_url(self) -> str:
        """Return the complete WSDL url"""
        return f"https://{self.hostname}/DataExchange.asmx?wsdl"

    @property
    def identification(self) -> dict[str, dict[str, str]]:
        """Identification part of the soap request"""
        return {"Identification": {"Workspace": self.workspace_id}}

    @property
    def hostname(self) -> str:
        """The full hostname in the form: {company_subdomain}.relaticsonline.com"""
        return f"{self.company_subdomain.lower()}.relaticsonline.com"

    @property
    def _client(self) -> Client:
        """The locally cached Client"""
        if self._client_cache is None:
            self._client_cache = Client(self.wsdl_url)

        return self._client_cache

    @staticmethod
    def _check_operation_name(operation_name: str) -> None:
        if operation_name == "":
            raise ValueError("Supplied operation_name is empty.")

    @staticmethod
    def _generate_auth_parameter(authentication: None | str | ClientCredential = None) -> dict[str, dict[str, str]]:
        if isinstance(authentication, str):
            auth = {"Authentication": {"Entrycode": authentication}}
        else:
            # Default value, because Relatics doesn't like this to be empty
            auth: dict[str, dict[str, str]] = {"Authentication": {}}

        return auth

    def _generate_client(self, authentication: None | str | ClientCredential = None) -> Client:
        """Generate a suds client and set the user-agent and OAuth2 headers"""

        # Create the client
        client = Client(self.wsdl_url)

        # Define header
        headers = {"User-Agent": self.user_agent}

        # Add auth header for OAuth2 requests
        if isinstance(authentication, ClientCredential):
            headers["Authorization"] = f"Bearer {authentication.get_token(self.hostname)}"

        client.set_options(headers=headers)

        return client

    def _setup_client_headers(self, authentication: None | str | ClientCredential) -> None:
        """
        Sets up the headers for in the client. Uses the default headers and includes bearer token for OAuth2.

        Args:
            authentication: The authentication used for the webservice
        """
        # Retrieve the default headers
        headers = self._default_headers

        # Add auth header for OAuth2 requests
        if isinstance(authentication, ClientCredential):
            headers["Authorization"] = f"Bearer {authentication.get_token(self.hostname)}"

        # Apply the headers
        self._client.set_options(headers=headers)

    @overload
    def get_result(
        self,
        operation_name: str,
        parameters: ParametersOrNone = None,
        *,
        authentication: None | str | ClientCredential = None,
        auto_parse_response: Literal[True],
    ) -> ExportResult: ...

    @overload
    def get_result(
        self,
        operation_name: str,
        parameters: ParametersOrNone = None,
        *,
        authentication: None | str | ClientCredential = None,
        auto_parse_response: Literal[False],
    ) -> SudsObject: ...

    @overload
    def get_result(
        self,
        operation_name: str,
        parameters: ParametersOrNone = None,
        *,
        authentication: None | str | ClientCredential = None,
    ) -> ExportResult: ...

    def get_result(
        self,
        operation_name: str,
        parameters: ParametersOrNone = None,
        *,
        authentication: None | str | ClientCredential = None,
        auto_parse_response: bool = True,
    ) -> ExportResult | SudsObject:
        """
        Retrieve results from a "Server for providing data" in Relatics, without checking any results

        Args:
            operation_name : The "OperationName" of the webservice to call
            parameters : The parameters to pass to the webservice
            authentication : Authentication for the webservice, either:
                * None for no authentication,
                * str for entryCode authentication or
                * ClientCredential for OAuth2 client credentials
            auto_parse_response: Convert the return object, and parse for any documents, for easy access.

        Returns:
            ExportResult : Result object when the retrieved response is parsed
            suds.sudsobject.Object : The retrieved response, when not parsed
        """
        # Basic check of mandatory arguments
        self._check_operation_name(operation_name=operation_name)

        # Add parameter plugin to handle parameters, when those are set
        if parameters is not None:
            self._client.set_options(plugins=[AddParametersPlugin(parameters)])

        self._setup_client_headers(authentication)

        # Any parameters will be handled by the AddParametersPlugin, so don't pass them here
        # GetResult(xs:string Operation, Identification Identification, Parameters Parameters,
        #           Authentication Authentication)
        suds_response = self._client.service.GetResult(
            Operation=operation_name,
            Identification=self.identification,
            Parameters=None,
            Authentication=self._generate_auth_parameter(authentication),
        )

        if auto_parse_response:
            # Parse the raw response into something useful
            export_result = ExportResult.from_suds(suds_response)
        else:
            export_result = suds_response

        return export_result

    def emulate_report(
        self,
        xslt_xml: str,
        operation_name: str,
        parameters: ParametersOrNone = None,
        authentication: None | str | ClientCredential = None,
    ):
        # TODO: Maybe move somewhere else, since this will probably require extra packages
        # First, get the report content from the webservice
        export_result = self.get_result(operation_name, parameters, authentication, True)

        # Get the last_received() from the client
        # response_xml = self._client.last_received()

        # Get the raw xml
        # response_xml.root().childAtPath("Body/GetResultResponse/GetResultResult").children[0].plain()

        # How to actually perform a xslt, including any documents?
        # `lxml` looks promising, and is actively updated: https://pypi.org/project/lxml/
        # see: https://lxml.de/xpathxslt.html#xslt

    @staticmethod
    def _generate_data_xml(data: list[dict[str, str]]) -> Document:
        # Build data xml
        root = Element("Import")
        doc = Document(root)

        for data_row in data:
            row = Element("Row", parent=root)
            for key, value in data_row.items():
                row.set(name=key, value=value)
            root.append(row)

        return doc

    @staticmethod
    def _generate_zip_b64(
        prepared_data: str | Document,
        documents: list[str],
        file_basename: str,
        file_extension: str,
        keep_zip_file: bool,
    ) -> str:
        # Generate the full filename for the zip file
        import_zip_path = os.path.join(gettempdir(), f"{file_basename}.zip")

        # Create the zip file
        with ZipFile(import_zip_path, "w") as import_zip:
            # Add all the supplied documents
            for document_path in documents:
                archive_name = os.path.join("Documents", os.path.split(document_path)[1])
                import_zip.write(filename=document_path, arcname=archive_name)

            # Add the data file
            if isinstance(prepared_data, Document):
                import_zip.writestr(zinfo_or_arcname=f"{file_basename}.{file_extension}", data=prepared_data.str())
            elif isinstance(prepared_data, str):
                import_zip.write(filename=prepared_data, arcname=os.path.split(prepared_data)[1])

            # log.debug(f"Zip-file created {import_zip_path}: \n{pformat(import_zip.namelist(), indent=2)}")
            log.debug("Zip-file created %s: \n%s", import_zip_path, pformat(import_zip.namelist(), indent=2))

        # Cleanup references to the ZipFile
        del import_zip

        # Convert zipfile to base64
        with open(import_zip_path, "rb") as import_zip_file:
            data_str = b64encode(import_zip_file.read()).decode("utf-8")

        # Remove the zip file from disk
        if not keep_zip_file:
            os.remove(import_zip_path)

        return data_str

    @overload
    def run_import(
        self,
        operation_name: str,
        data: str | list[dict[str, str]],
        *,
        authentication: None | str | ClientCredential = None,
        file_name: None | str = None,
        documents: None | list[str] = None,
        auto_parse_response: Literal[True],
    ) -> ImportResult: ...

    @overload
    def run_import(
        self,
        operation_name: str,
        data: str | list[dict[str, str]],
        *,
        authentication: None | str | ClientCredential = None,
        file_name: None | str = None,
        documents: None | list[str] = None,
        auto_parse_response: Literal[False],
    ) -> SudsObject: ...

    @overload
    def run_import(
        self,
        operation_name: str,
        data: str | list[dict[str, str]],
        *,
        authentication: None | str | ClientCredential = None,
        file_name: None | str = None,
        documents: None | list[str] = None,
    ) -> ImportResult: ...

    def run_import(
        self,
        operation_name: str,
        data: str | list[dict[str, str]],
        *,
        authentication: None | str | ClientCredential = None,
        file_name: None | str = None,
        documents: None | list[str] = None,
        auto_parse_response: bool = True,
    ) -> ImportResult | SudsObject:
        """
        Retrieve results from a "Server for providing data" in Relatics, with checking of the results

        "data" can be given in the following formats:
        * a `str` with the name of the data file. Can be an Excel file or csv file.
        * a `list` of `dict[str, str]`, for example:
            ```python
            data=[
                {"name": "Object 1", "description": "Lorem ipsum dolor sit amet."},
                {"name": "Object 2", "description": "Ut enim ad minim veniam."},
            ]
            ```

        Args:
            operation_name : The "OperationName" of the webservice to call
            data : The data to send to the import. See description above.
            authentication : Authentication for the webservice, either:
                * None for no authentication,
                * str for entryCode authentication or
                * ClientCredential for OAuth2 client credentials
            file_name : Filename send to Relatics. Will show up in the "Imported file" column in the import log. If
                no extension is given or the extension doesn't match the supplied data, the correct extension will
                be added
            documents : Optional list of filepaths to include in the import. Must be unique names.
                See https://kb.relaticsonline.com/published/ShowObject.aspx?Key=7126fb9d-58df-e311-9406-00155de0940e
            auto_parse_response : Convert the return object for easy access

        Returns:
            ImportResult : Result object when the retrieved response is parsed
            suds.sudsobject.Object : The retrieved response, when not parsed
        """
        # Basic check of mandatory arguments
        self._check_operation_name(operation_name=operation_name)

        if not data:
            # Above "if" checks for both empty str or empty list,
            # see https://docs.python.org/3/library/stdtypes.html#truth-value-testing
            raise ValueError("Supplied data is empty.")
        if not isinstance(data, list) and not isinstance(data, str):
            raise TypeError("Invalid type of data supplied.")
        if documents:
            # Detect duplicate names. Remove duplicate tails in the path with set(). Optimized with set comprehension.
            if len({os.path.split(path)[1] for path in documents}) != len(documents):
                raise ValueError("Duplicate filenames in document list.")

        file_extension = None

        # Prepare the data part
        if isinstance(data, list):
            # Set appropriate filename
            file_extension = "xml"

            # Build data xml
            prepared_data = self._generate_data_xml(data)

        else:
            # Set appropriate filename, based on the given filename in "data"
            file_extension = os.path.splitext(data)[1][1:]

            # Validate if given extensions is supported
            if file_extension not in SUPPORTED_EXTENSIONS:
                raise TypeError("Supplied file has unsupported file extension.")

            prepared_data = data

        # Set appropriate filename
        if file_name is None:
            file_basename = f"{IMPORT_BASENAME}"
        else:
            # Clean any possible path from the filename and remove a possible extension
            file_basename = os.path.splitext(os.path.split(file_name)[1])[0]

        # Choose how to create the base64 data: when document are supplied, create a zip; otherwise
        # use the file or xml data
        if documents is not None:
            # Generate the base64 encoded zip-file
            data_str = self._generate_zip_b64(
                prepared_data=prepared_data,
                documents=documents,
                file_basename=file_basename,
                file_extension=file_extension,
                keep_zip_file=self.keep_zip_file,
            )

            # Set the file extension to zip
            file_extension = "zip"

        else:  # documents is None
            if isinstance(data, list):
                # Convert previously generated xml to base64
                data_str = b64encode(bytes(prepared_data.str(), "utf-8")).decode("utf-8")

            else:
                # Convert supplied data file to base64
                with open(data, "rb") as data_file:
                    data_str = b64encode(data_file.read()).decode("utf-8")

        self._setup_client_headers(authentication)

        # Import(xs:string Operation, Identification Identification, Authentication Authentication, xs:string Filename,
        #        xs:string Data)
        suds_response = self._client.service.Import(
            Operation=operation_name,
            Identification=self.identification,
            Authentication=self._generate_auth_parameter(authentication),
            Filename=f"{file_basename}.{file_extension}",
            Data=data_str,
        )
        # KNOWLEDGE: Convert sudsobject to dict: self._client.dict(sudsobject)

        if auto_parse_response:
            # Parse the raw response into something useful
            import_result = ImportResult.from_suds(suds_response)
        else:
            import_result = suds_response

        return import_result
