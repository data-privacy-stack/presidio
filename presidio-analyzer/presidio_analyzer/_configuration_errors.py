"""ValueError-compatible metadata for value-safe configuration diagnostics."""

from typing import Optional, Tuple, Union

ConfigPath = Tuple[Union[str, int], ...]


class ConfigValidationError(ValueError):
    """Carry a safe diagnostic without changing existing exception messages.

    :param message: Backward-compatible exception text.
    :param code: Stable diagnostic category.
    :param path: Location relative to the current validation context.
    :param safe_message: Value-free text; defaults to message for trusted templates.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "value_error",
        path: ConfigPath = (),
        safe_message: Optional[str] = None,
    ):
        super().__init__(message)
        self.code = code
        self.path = path
        self.safe_message = message if safe_message is None else safe_message
