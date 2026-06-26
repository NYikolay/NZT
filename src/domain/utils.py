from enum import Enum


class ErrorCodes(int, Enum):
    """
    Enum class that contains:
    1. Server error code ( usually validation error )
    2. error description, a string describing the error
    3. name of the field that is associated with the error
    """

    @property
    def description(self):
        descriptions = {}
        return descriptions[self]

    @property
    def error_attr(self):
        error_attrs = {}
        return error_attrs[self]
