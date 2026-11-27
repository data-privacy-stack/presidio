import logging
from typing import Dict

from presidio_anonymizer.services.validators import validate_parameter_not_empty

logger = logging.getLogger("presidio-anonymizer")


class OperatorConfig:
    """Hold the data of the required operator."""

    def __init__(self, operator_name: str, params: Dict = None):
        """
        Create an operator config instance.

        :param operator_name: the name of the operator we want to work with
        :param params: the parameters the operator needs in order to work
        """
        self.operator_name = operator_name
        if not params:
            params = {}
        self.params = params
        self.__validate_fields()

    def __repr__(self):
        """Return a string representation of the object."""
        return f"operator_name: {self.operator_name}, params: {self.params}"

    @classmethod
    def from_json(cls, params: Dict) -> "OperatorConfig":
        """
        Create OperatorConfig from json.

        :param params: json e.g.: {
            "type": "mask",
            "masking_char": "*",
            "chars_to_mask": 4,
            "from_end": true
            }
        :return: OperatorConfig
        """
        params = dict(params)
        operator_name = params.get("type")
        if operator_name:
            params.pop("type")
        return cls(operator_name, params)

    def __eq__(self, other: "OperatorConfig"):
        """Verify two OperatorConfigs are equal."""
        operator_name = self.operator_name == other.operator_name
        return self.params == other.params and operator_name

    def __validate_fields(self):
        validate_parameter_not_empty(
            self.operator_name, "operator config", "operator_name"
        )
