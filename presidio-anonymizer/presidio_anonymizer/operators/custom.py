"""Replaces the PII text with function result."""

from typing import Dict

from presidio_anonymizer.entities import InvalidParamError
from presidio_anonymizer.operators import Operator, OperatorType


class Custom(Operator):
    """
    Replace PII text entity with the results of a function executed on the PII text.

    The function return type must be a string
    """

    LAMBDA = "lambda"

    def operate(self, text: str = None, params: Dict = None) -> str:
        """:return: result of function executed on the text."""
        new_val = params.get(self.LAMBDA)
        result = new_val(text)
        if not isinstance(result, str):
            raise InvalidParamError("Function return type must be a str")
        return result

    def validate(self, params: Dict) -> None:
        """Validate the provided function is callable.

        Note: we intentionally do NOT call the lambda here. Invoking it with a
        dummy value causes side effects in stateful lambdas (e.g. those that
        accumulate a token-to-original-value map for de-anonymization). The
        return-type contract is enforced in operate() when the lambda runs on
        real data, raising InvalidParamError if it does not return a str.

        See: https://github.com/data-privacy-stack/presidio/issues/2024
        """
        new_val = params.get(self.LAMBDA)
        if not callable(new_val):
            raise InvalidParamError("New value must be a callable function")

    def operator_name(self) -> str:
        """Return operator name."""
        return "custom"

    def operator_type(self) -> OperatorType:
        """Return operator type."""
        return OperatorType.Anonymize
