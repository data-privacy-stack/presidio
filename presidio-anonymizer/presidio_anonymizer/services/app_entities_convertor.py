from typing import Dict, List

from presidio_anonymizer.entities import (
    InvalidParamError,
    OperatorConfig,
    OperatorResult,
    RecognizerResult,
)


class AppEntitiesConvertor:
    """Assisting class to convert API json entities to engine entities."""

    @staticmethod
    def analyzer_results_from_json(data: List[Dict]) -> List["RecognizerResult"]:
        """
        Go over analyzer results, validate them and convert to List[RecognizerResult].

        :param data: contains the anonymizers and analyzer_results_json
        """
        if data is None:
            raise InvalidParamError(
                "Invalid input, " "request must contain analyzer results"
            )
        return [RecognizerResult.from_json(analyzer_result) for analyzer_result in data]

    @staticmethod
    def operators_config_from_json(data: Dict) -> Dict[str, "OperatorConfig"]:
        """
        Go over the operators list and get the relevant create operator config entity.

        :param data: contains the list of configuration
        value - OperatorConfig
        """
        if data is not None:
            return {
                key: OperatorConfig.from_json(operator_json)
                for (key, operator_json) in data.items()
            }
        return {}

    @staticmethod
    def deanonymize_entities_from_json(json: Dict) -> List["OperatorResult"]:
        """
        Create DecryptEntity list.

        :param json:
        {
            "text": text,
            "encrypt_results": [{
                "start": 0,
                "end": 10,
                "key": "1111111111111111",
                "entity_type":"PHONE_NUMBER"
            }],
        }
        :return: List[OperatorResult]
        """
        decrypt_entity = json.get("anonymizer_results")
        return (
            [OperatorResult.from_json(result) for result in decrypt_entity]
            if decrypt_entity
            else []
        )

    @staticmethod
    def check_custom_operator(operators: Dict[str, OperatorConfig]):
        """Check if an operator is of type custom."""
        return any([config.operator_name == "custom" for config in operators.values()])
