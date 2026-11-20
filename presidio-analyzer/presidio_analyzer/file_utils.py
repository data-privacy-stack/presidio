"""Helpers for reading configuration and prompt files."""

from pathlib import Path
from typing import Union

__all__ = ["ConfigFileEncodingError", "read_utf8_file"]


class ConfigFileEncodingError(ValueError):
    """A configuration or prompt file is not valid UTF-8."""


def read_utf8_file(path: Union[str, Path]) -> str:
    """Read a configuration or prompt file as UTF-8 text.

    Presidio reads these files as UTF-8 whatever the locale's preferred
    encoding is.

    :param path: Path of the file to read.
    :return: The file contents.
    :raises ConfigFileEncodingError: If the file is not valid UTF-8.
    :raises OSError: If the file cannot be read.
    """
    try:
        with open(path, encoding="utf-8") as file:
            return file.read()
    except UnicodeDecodeError as e:
        raise ConfigFileEncodingError(
            f"Configuration file {path} is not valid UTF-8; "
            f"re-save it as UTF-8. Error: {e}"
        ) from e
