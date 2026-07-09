"""A Python CLI for analyzing PII Entities with the Presidio framework."""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("presidio-cli")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"

APP_DESCRIPTION = __doc__
SHELL_NAME = "presidio"

APP_VERSION = __version__
