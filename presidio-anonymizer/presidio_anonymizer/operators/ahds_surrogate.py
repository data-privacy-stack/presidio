"""AHDS surrogate operator that uses AHDS de-identification service."""

import logging
import os
from typing import Dict, List

try:
    from azure.health.deidentification import DeidentificationClient
    from azure.health.deidentification.models import (
        DeidentificationContent,
        DeidentificationCustomizationOptions,
        DeidentificationOperationType,
        DeidentificationResult,
        PhiCategory,
        SimplePhiEntity,
        TaggedPhiEntities,
        TextEncodingType,
    )
except ImportError:
    DeidentificationClient = None
    DeidentificationContent = None
    DeidentificationCustomizationOptions = None
    DeidentificationResult = None
    PhiCategory = None
    SimplePhiEntity = None
    TaggedPhiEntities = None
    DeidentificationOperationType = None
    TextEncodingType = None

try:
    from presidio_analyzer.llm_utils.azure_auth_helper import (
        get_azure_credential,
    )
except ImportError:
    get_azure_credential = None

from presidio_anonymizer.entities import InvalidParamError
from presidio_anonymizer.operators import Operator, OperatorType

logger = logging.getLogger("presidio-anonymizer")


class AHDSSurrogate(Operator):
    """AHDS Surrogate operator using AHDS de-identification service surrogation."""

    ENDPOINT = "endpoint"
    ENTITIES = "entities"
    INPUT_LOCALE = "input_locale"
    SURROGATE_LOCALE = "surrogate_locale"


    ENTITY_TYPE_MAPPING = {
        # === GLOBAL PRESIDIO ENTITIES ===

        # Person-related entities
        'PERSON': 'PATIENT',  # Global Presidio entity
        'PATIENT': 'PATIENT',
        'DOCTOR': 'DOCTOR',
        'PHYSICIAN': 'DOCTOR',
        'NURSE': 'DOCTOR',  # Medical professional
        'PRACTITIONER': 'DOCTOR',
        'NRP': 'PATIENT',  # Nationality, religious or political group

        # Contact information
        'PHONE_NUMBER': 'PHONE',  # Global Presidio entity
        'PHONE': 'PHONE',
        'FAX_NUMBER': 'FAX',
        'FAX': 'FAX',
        'EMAIL_ADDRESS': 'EMAIL',  # Global Presidio entity
        'EMAIL': 'EMAIL',

        # Temporal information
        'DATE_TIME': 'DATE',  # Global Presidio entity
        'DATE': 'DATE',
        'TIME': 'DATE',
        'AGE': 'AGE',

        # Location information
        'LOCATION': 'LOCATION_OTHER',  # Global Presidio entity
        'ADDRESS': 'STREET',
        'STREET_ADDRESS': 'STREET',
        'CITY': 'CITY',
        'STATE': 'STATE',
        'COUNTRY': 'COUNTRY_OR_REGION',
        'ZIP_CODE': 'ZIP',
        'POSTAL_CODE': 'ZIP',

        # Financial/Account information
        'CREDIT_CARD': 'ACCOUNT',  # Global Presidio entity
        'ACCOUNT_NUMBER': 'ACCOUNT',
        'BANK_ACCOUNT': 'ACCOUNT',
        'ROUTING_NUMBER': 'ACCOUNT',
        'IBAN_CODE': 'ACCOUNT',  # Global Presidio entity
        'CRYPTO': 'ACCOUNT',  # Global Presidio entity - cryptocurrency

        # Medical/Health related
        'MEDICAL_LICENSE': 'LICENSE',  # Global Presidio entity
        'LICENSE': 'LICENSE',
        'NPI': 'LICENSE',  # National Provider Identifier
        'DEA_NUMBER': 'LICENSE',  # Drug Enforcement Administration number
        'CONDITION': 'PATIENT',  # Medical condition (patient-related)
        'MEDICATION': 'PATIENT',  # Patient-related medical info
        'PROCEDURE': 'PATIENT',  # Medical procedure
        'TREATMENT': 'PATIENT',  # Medical treatment
        'HEALTH_PLAN': 'HEALTH_PLAN',
        'INSURANCE': 'HEALTH_PLAN',
        'HOSPITAL': 'HOSPITAL',
        'CLINIC': 'HOSPITAL',  # Medical institution
        'MEDICAL_RECORD_NUMBER': 'MEDICAL_RECORD',
        'MRN': 'MEDICAL_RECORD',

        # Technology/Digital
        'IP_ADDRESS': 'IP_ADDRESS',  # Global Presidio entity
        'URL': 'URL',  # Global Presidio entity
        'USERNAME': 'USERNAME',
        'PASSWORD': 'USERNAME',  # No specific password category, use username
        'DEVICE': 'DEVICE',
        'DEVICE_ID': 'DEVICE',
        'MAC_ADDRESS': 'MAC_ADDRESS',

        # Organization/Institution/Profession
        'ORGANIZATION': 'ORGANIZATION',
        'ORG': 'ORGANIZATION',
        'COMPANY': 'ORGANIZATION',
        'PROFESSION': 'PROFESSION',
        'JOB_TITLE': 'PROFESSION',
        'OCCUPATION': 'PROFESSION',

        # Vehicle information
        'VEHICLE': 'VEHICLE',
        'LICENSE_PLATE': 'VEHICLE',
        'VIN': 'VEHICLE',
        'CAR': 'VEHICLE',

        # === US-SPECIFIC PRESIDIO ENTITIES ===
        'US_SSN': 'SOCIAL_SECURITY',  # US Social Security Number
        'US_DRIVER_LICENSE': 'ID_NUM',  # US Driver's license
        'US_PASSPORT': 'ID_NUM',  # US Passport
        'US_ITIN': 'ID_NUM',  # US Individual Taxpayer Identification Number
        'US_BANK_NUMBER': 'ACCOUNT',  # US Bank account number

        # === UK-SPECIFIC PRESIDIO ENTITIES ===
        'UK_NHS': 'ID_NUM',  # UK NHS number
        'UK_NINO': 'ID_NUM',  # UK National Insurance Number

        # === SPAIN-SPECIFIC PRESIDIO ENTITIES ===
        'ES_NIF': 'ID_NUM',  # Spanish NIF number
        'ES_NIE': 'ID_NUM',  # Spanish NIE number

        # === ITALY-SPECIFIC PRESIDIO ENTITIES ===
        'IT_FISCAL_CODE': 'ID_NUM',  # Italian fiscal code
        'IT_DRIVER_LICENSE': 'ID_NUM',  # Italian driver license
        'IT_VAT_CODE': 'ID_NUM',  # Italian VAT code
        'IT_PASSPORT': 'ID_NUM',  # Italian passport
        'IT_IDENTITY_CARD': 'ID_NUM',  # Italian identity card

        # === POLAND-SPECIFIC PRESIDIO ENTITIES ===
        'PL_PESEL': 'ID_NUM',  # Polish PESEL number

        # === SINGAPORE-SPECIFIC PRESIDIO ENTITIES ===
        'SG_NRIC_FIN': 'ID_NUM',  # Singapore NRIC/FIN
        'SG_UEN': 'ID_NUM',  # Singapore Unique Entity Number

        # === AUSTRALIA-SPECIFIC PRESIDIO ENTITIES ===
        'AU_ABN': 'ID_NUM',  # Australian Business Number
        'AU_ACN': 'ID_NUM',  # Australian Company Number
        'AU_TFN': 'ID_NUM',  # Australian Tax File Number
        'AU_MEDICARE': 'ID_NUM',  # Australian Medicare number

        # === INDIA-SPECIFIC PRESIDIO ENTITIES ===
        'IN_PAN': 'ID_NUM',  # Indian Permanent Account Number
        'IN_AADHAAR': 'ID_NUM',  # Indian Aadhaar number
        'IN_VEHICLE_REGISTRATION': 'VEHICLE',  # Indian vehicle registration
        'IN_VOTER': 'ID_NUM',  # Indian voter ID
        'IN_PASSPORT': 'ID_NUM',  # Indian passport

        # === FINLAND-SPECIFIC PRESIDIO ENTITIES ===
        'FI_PERSONAL_IDENTITY_CODE': 'ID_NUM',  # Finnish personal identity code

        # === KOREA-SPECIFIC PRESIDIO ENTITIES ===
        'KR_RRN': 'ID_NUM',  # Korean Resident Registration Number
        'KR_PASSPORT': 'ID_NUM',  # Korean Passport Number

        # === GENERIC CATEGORIES ===
        'ID_NUMBER': 'ID_NUM',
        'PASSPORT': 'ID_NUM',
        'DRIVER_LICENSE': 'ID_NUM',
        'SSN': 'SOCIAL_SECURITY',
        'SOCIAL_SECURITY_NUMBER': 'SOCIAL_SECURITY',
        'BIO_ID': 'BIO_ID',
        'BIOMETRIC_ID': 'BIO_ID',

        # === FALLBACK/UNKNOWN CATEGORIES ===
        'GENERIC_PII': 'UNKNOWN',
        'PII': 'UNKNOWN',
        'OTHER': 'UNKNOWN',
        'UNKNOWN': 'UNKNOWN',
    }

    def __init__(self):
        """Initialize AHDS Surrogate operator."""
        pass

    def operate(self, text: str = None, params: Dict = None) -> str:
        """
        Replace PII entities using the AHDS de-identification service.

        This operator uses AHDS de-identification service surrogation
        to generate contextually appropriate replacements for detected
        PII entities, maintaining text readability while protecting
        sensitive information.

        :param text: The full text being processed
        :param params: Parameters including:
            - endpoint: AHDS de-identification service endpoint
              (optional, can use AHDS_ENDPOINT env var)
            - entities: List of entities detected by analyzer
            - input_locale: Input locale (default: "en-US")
            - surrogate_locale: Surrogate locale (default: "en-US")
        :return: Text with surrogates generated by AHDS
        """

        if not DeidentificationClient:
            raise ImportError(
                "Azure Health Data Services de-identification "
                "service SDK is not available. "
                "Please install azure-health-deidentification "
                "and azure-identity."
            )

        if not text:
            return ""

        endpoint = params.get(self.ENDPOINT) or os.getenv("AHDS_ENDPOINT")
        if not endpoint:
            raise InvalidParamError(
                "AHDS de-identification service endpoint is required. "
                "Provide via 'endpoint' parameter "
                "or set AHDS_ENDPOINT environment variable."
            )

        entities = params.get(self.ENTITIES, [])
        input_locale = params.get(self.INPUT_LOCALE, "en-US")
        surrogate_locale = params.get(self.SURROGATE_LOCALE, "en-US")

        # Convert analyzer results to AHDS tagged entities
        tagged_entities = self._convert_to_tagged_entities(entities)

        try:
            # Use environment-aware credential (DefaultAzureCredential for dev,
            # ChainedTokenCredential for production)
            credential = get_azure_credential()
            client = DeidentificationClient(endpoint, credential,
                                            api_version="2025-07-15-preview")

            # Create tagged entity collection
            tagged_entity_collection = TaggedPhiEntities(
                encoding=TextEncodingType.CODE_POINT,
                entities=tagged_entities
            )

            customizations = None
            if input_locale or surrogate_locale:
                customizations = DeidentificationCustomizationOptions()
                if input_locale:
                    customizations.input_locale = input_locale
                if surrogate_locale:
                    customizations.surrogate_locale = surrogate_locale

            content = DeidentificationContent(
                input_text=text,
                operation_type=DeidentificationOperationType.SURROGATE_ONLY,
                tagged_entities=tagged_entity_collection,
                customizations=customizations
            )

            result = client.deidentify_text(content)
            if not result.output_text:
                raise InvalidParamError("Operation returned empty output text.")
            if result.output_text == text:
                raise InvalidParamError("Operation returned input text.")
            return result.output_text
        except Exception as e:
            raise InvalidParamError(f"AHDS Surrogate operation failed: {e}")

    def _convert_to_tagged_entities(self, entities: List) -> List:
        """Convert analyzer results to AHDS SimplePhiEntity format."""
        tagged_entities = []

        for entity in entities:
            # Handle both RecognizerResult objects and dict format
            if hasattr(entity, 'entity_type'):
                # RecognizerResult object
                category_name = entity.entity_type
                start = entity.start
                end = entity.end
            else:
                # Dict format
                category_name = entity.get('entity_type', entity.get('category', ''))
                start = entity.get('start', entity.get('offset', 0))
                end = entity.get('end', start + entity.get('length', 0))

            # Map entity type to PhiCategory
            phi_category = self._map_to_phi_category(category_name)

            tagged_entity = SimplePhiEntity(
                category=phi_category,
                offset=start,
                length=end - start
            )
            tagged_entities.append(tagged_entity)

        return tagged_entities

    def _map_to_phi_category(self, entity_type: str):
        """Map Presidio entity types to AHDS PhiCategory.

        Maps common Presidio PII entity types to their most appropriate AHDS PhiCategory
        counterparts for surrogate generation.

        :param entity_type: The Presidio entity type (e.g., 'PERSON', 'PHONE_NUMBER')
        :return: Corresponding PhiCategory enum value
        """
        # Convert to uppercase for case-insensitive matching
        entity_upper = entity_type.upper()

        # Try exact match first
        if entity_upper in self.ENTITY_TYPE_MAPPING:
            category_name = self.ENTITY_TYPE_MAPPING[entity_upper]
            return self._get_safe_phi_category(category_name)

        return PhiCategory.UNKNOWN

    def _get_safe_phi_category(self, category_name: str):
        """Safely get PhiCategory enum value, with fallback to UNKNOWN."""
        try:
            # Try to get the category by name
            return getattr(PhiCategory, category_name)
        except AttributeError:
            return PhiCategory.UNKNOWN

    def validate(self, params: Dict = None) -> None:
        """Validate operator parameters."""
        if not DeidentificationClient:
            raise ImportError(
                "Azure Health Data Services SDK is not available. "
                "Please install azure-health-deidentification and azure-identity."
            )

        if params is None:
            params = {}

        endpoint = params.get(self.ENDPOINT) or os.getenv("AHDS_ENDPOINT")
        if not endpoint:
            raise InvalidParamError(
                "AHDS endpoint is required. Provide via 'endpoint' parameter "
                "or set AHDS_ENDPOINT environment variable."
            )

        entities = params.get(self.ENTITIES, [])
        if not isinstance(entities, list):
            raise InvalidParamError("Entities must be a list")

    def operator_name(self) -> str:
        """Return operator name."""
        return "surrogate_ahds"

    def operator_type(self) -> OperatorType:
        """Return operator type."""
        return OperatorType.Anonymize

