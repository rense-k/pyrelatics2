from base64 import b64decode
from dataclasses import dataclass
from dataclasses import field
from datetime import time as dt_time
from datetime import timedelta
from io import BytesIO
from logging import getLogger
from typing import Literal
from typing import TypeAlias
from zipfile import ZipFile

from colorama import Fore
from colorama import Style
from suds.sax.text import Text
from suds.sudsobject import Object as SudsObject

# Type aliases
ImportMessageStatus: TypeAlias = Literal["Progress", "Comment", "Success", "Warning", "Error"]
ImportElementActions: TypeAlias = Literal["Add", "Update"]

log = getLogger(__name__)


class BaseResult:  # pylint: disable=R0903
    """
    Base class with commonalities for the ExportResult and ImportResult classes.
    """

    has_error: bool = False
    error_msg: str | None = None

    def handle_suds_response_errors(self, suds_response: SudsObject | None) -> None:
        """Handle processing of common error scenarios"""
        if suds_response is None:
            self.has_error = True
            self.error_msg = ""
            log.warning("Empty response received from the request. This indicates an undefined error.")

        # elif suds_response.Export._Error:
        if hasattr(suds_response, "Export"):
            self.has_error = True
            if hasattr(suds_response.Export, "_Error"):
                self.error_msg = str(suds_response.Export._Error)  # pylint: disable=W0212
            else:
                self.error_msg = ""
            log.warning("Received an error response from the export request: %s", self.error_msg)


# pylint: disable=W0212
@dataclass(kw_only=True, slots=True)
class ExportResult(BaseResult):
    """
    Data class containing the result of a get_result.

    Will evaluate as Falsy when an error response was received from the import request, otherwise Truthy.
    """

    data: SudsObject | None = None
    documents: dict[str, bytes] = field(default_factory=dict)

    @staticmethod
    def from_suds(suds_response: SudsObject) -> "ExportResult":
        """
        Parse raw suds response <sudsobject> for any documents and respond with a filled ExportResult object

        Args:
            suds_response : Raw <sudsobject> response from the import request

        Response:
            ExportResult : Parsed result of the export.
        """
        result = ExportResult()

        # Handle common errors
        result.handle_suds_response_errors(suds_response)

        # Handle possibly received documents
        if (
            hasattr(suds_response, "Report")
            and hasattr(suds_response.Report, "Documents")
            and isinstance(suds_response.Report.Documents, Text)
        ):
            result.has_error = False

            # The the base64 encoded contents as a zip file
            result.documents = {}

            with ZipFile(BytesIO(b64decode(str(suds_response.Report.Documents))), "r") as docs_zip:
                for zipped_file in docs_zip.filelist:
                    result.documents[zipped_file.filename] = docs_zip.read(zipped_file.filename)

            # Cleanup variable without further use
            del docs_zip
            if "zipped_file" in locals():
                del zipped_file  # pylint: disable=W0631

            # Delete the Document node from the sudsobject
            del suds_response.Report.Documents

        # Store the SudsObject inside the result
        result.data = suds_response

        if not hasattr(suds_response, "Export") and not hasattr(suds_response, "Report"):
            result.has_error = True
            result.error_msg = repr(suds_response)
            log.warning("Unrecognized response received from the export request.")

        return result

    def __bool__(self) -> bool:
        return not self.has_error

    def __str__(self) -> str:
        result = ""

        if self.has_error:
            result += f"ERROR: {self.error_msg}\n"

        if self.data:
            result += "[Data]: \n"
            result += str(self.data)
            result += "\n"

        if self.documents:
            result += "[Documents]: \n"
            result += Style.BRIGHT + "RelaticsFilename                              Size (bytes)\n" + Style.RESET_ALL
            for key, value in self.documents.items():
                result += f"{key:45} {len(value):>12}\n"

        return result


# pylint: enable=W0212


@dataclass(kw_only=True, slots=True)
class ImportMessage:
    """
    Data class for a message in the result of an import
    """

    time: dt_time | str
    status: ImportMessageStatus
    message: str
    row: int

    status_fore_color = {
        "Progress": Fore.BLUE,
        "Comment": Fore.RESET,
        "Success": Fore.GREEN,
        "Warning": Fore.YELLOW,
        "Error": Fore.RED,
    }

    def __post_init__(self):
        """
        Convert a date given as string into a date
        """
        if isinstance(self.time, str):
            self.time = dt_time.fromisoformat(self.time)

    def __str__(self) -> str:
        status_color = self.status_fore_color[self.status]
        return f"{self.time}  {self.row:05}  {status_color}{self.status:<8}{Fore.RESET}  {self.message}"


@dataclass(kw_only=True, slots=True)
class ImportElement:
    """
    Data class for a changed element in the result of an import
    """

    action: ImportElementActions
    id: str  # pylint: disable=invalid-name
    foreign_key: str

    def __str__(self) -> str:
        return f"{self.action:<6}  {self.id}  {self.foreign_key}"


# pylint: disable=W0212
@dataclass(kw_only=True, slots=True)
class ImportResult(BaseResult):
    """
    Data class containing the result of an import

    Will evaluate as Falsy when an error response was received from the import request, otherwise Truthy.
    """

    messages: list[ImportMessage] = field(default_factory=list)
    elements: list[ImportElement] = field(default_factory=list)
    total_rows: int | None = None
    elapsed_time: timedelta | None = None

    # "ImportResult", see https://peps.python.org/pep-0484/#forward-references
    @staticmethod
    def from_suds(suds_response: SudsObject) -> "ImportResult":
        """
        Parse raw suds response <sudsobject> for messages and elements and respond with a filled ImportResult object

        Args:
            suds_response : Raw <sudsobject> response from the import request

        Response:
            ImportResult : Parsed result of the import.
        """
        result = ImportResult()

        # Handle common errors
        result.handle_suds_response_errors(suds_response)

        if hasattr(suds_response, "Import"):
            result.has_error = False

            # Add all the messages when available
            if hasattr(suds_response.Import, "Message"):
                row = 0
                for msg in suds_response.Import.Message:
                    # Monitor any row changes
                    if msg._Result == "Progress":
                        if "Processing row :" in msg.value:
                            row = int(msg.value[17:])
                        elif "Total rows imported:" in msg.value:
                            result.total_rows = int(msg.value[21:])
                        elif "Total time (ms):" in msg.value:
                            result.elapsed_time = timedelta(milliseconds=int(msg.value[17:]))

                    result.messages.append(
                        ImportMessage(time=msg._Time, status=msg._Result, message=msg.value, row=row)
                    )

            # Add all the elements when available
            if hasattr(suds_response.Import, "Elements") and len(suds_response.Import.Elements) > 0:
                # Force a single element into a list and None into an empty list
                _elements = suds_response.Import.Elements[0]
                elements = _elements if isinstance(_elements, list) else [] if _elements is None else [_elements]

                for elem in elements:
                    result.elements.append(
                        ImportElement(action=elem._Action, id=elem._ID, foreign_key=elem._ForeignKey)
                    )

        if not hasattr(suds_response, "Export") and not hasattr(suds_response, "Import"):
            result.has_error = True
            result.error_msg = repr(suds_response)
            log.warning("Unrecognized response received from the import request.")

        return result

    def __bool__(self) -> bool:
        return not self.has_error

    def __str__(self) -> str:
        result = ""

        if self.has_error:
            result += f"ERROR: {self.error_msg}\n"

        if self.total_rows is not None:
            result += f"Rows imported : {self.total_rows}\n"

        if self.elapsed_time is not None:
            result += f"Elapsed time  : {self.elapsed_time} (h:mm:ss.mmmmmm)\n"

        if self.messages:
            result += "[Messages]: \n"
            result += Style.BRIGHT + "Time      Row    Status    Message\n" + Style.RESET_ALL
            for msg in self.messages:
                result += f"{msg.__str__()} \n"

        if self.elements:
            result += "[Elements]: \n"
            result += Style.BRIGHT + "Action  ID                                    Foreign key\n" + Style.RESET_ALL
            for elem in self.elements:
                result += f"{elem.__str__()} \n"

        return result

    def filter_messages(self, status: ImportMessageStatus) -> list[ImportMessage]:
        """
        Return the list of messages with the given status

        Returns:
            list[ImportMessage]: List of messages
        """
        return [_ for _ in self.messages if _.status == status]

    # ["Progress", "Comment", "Success", "Warning", "Error"]
    @property
    def progress_messages(self) -> list[ImportMessage]:
        """Get a list of all the progress messages"""
        return self.filter_messages("Progress")

    @property
    def comment_messages(self) -> list[ImportMessage]:
        """Get a list of all the comment messages"""
        return self.filter_messages("Comment")

    @property
    def success_messages(self) -> list[ImportMessage]:
        """Get a list of all the comment messages"""
        return self.filter_messages("Success")

    @property
    def warning_messages(self) -> list[ImportMessage]:
        """Get a list of all the comment messages"""
        return self.filter_messages("Warning")

    @property
    def error_messages(self) -> list[ImportMessage]:
        """Get a list of all the comment messages"""
        return self.filter_messages("Error")

    def filter_elements(self, action: ImportElementActions) -> list[ImportElement]:
        """
        Return the list of elements with the given action

        Returns:
            list[ImportMessage]: List of messages
        """
        return [_ for _ in self.elements if _.action == action]

    # ["Add", "Update"]
    @property
    def added_elements(self) -> list[ImportElement]:
        """Get a list of all the added elements"""
        return self.filter_elements("Add")

    @property
    def updated_elements(self) -> list[ImportElement]:
        """Get a list of all the updated elements"""
        return self.filter_elements("Update")


# pylint: enable=W0212
