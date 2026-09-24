from __future__ import annotations

import logging
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

import yaml

from presidio_analyzer import EntityRecognizer

logger = logging.getLogger("presidio-analyzer")


class PredefinedRecognizerNotFoundError(Exception):
    """Exception raised when a predefined recognizer is not found."""

    pass


# Module path segment that identifies country-specific recognizers. Matches
# the ``predefined_recognizers/country_specific/<country>/...`` directory
# layout used for the bundled predefined recognizers. Kept as a module-level
# constant so country detection stays in lockstep with the directory tree.
_COUNTRY_SPECIFIC_MODULE_SEGMENT = "country_specific"


class RecognizerListLoader:
    """A utility class that initializes recognizers based on configuration."""

    SUPPORTED_ENTITY: ClassVar[str] = "supported_entity"
    SUPPORTED_ENTITIES: ClassVar[str] = "supported_entities"

    @staticmethod
    def is_recognizer_enabled(recognizer_conf: Union[Dict[str, Any], str]) -> bool:
        """Return True if the recognizer is enabled.

        :param recognizer_conf: The recognizer configuration.
        """
        return "enabled" not in recognizer_conf or recognizer_conf["enabled"]

    @staticmethod
    def _get_recognizer_context(
        recognizer: Union[Dict[str, Any], str],
    ) -> Optional[List[str]]:
        if isinstance(recognizer, str):
            return None
        return recognizer.get("context", None)

    @staticmethod
    def _split_recognizers(
        recognizers_conf: Iterable[Union[Dict[str, Any], str]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Split the recognizer list to predefined and custom.

        All recognizers are custom by default though
        type: 'custom' can be mentioned as well.
        This function supports the previous format as well.

        A bare string entry (``- CreditCardRecognizer``) is the shorthand the
        configuration schema accepts for a predefined recognizer that needs no
        further settings. It is expanded to its dict equivalent here, because
        every step after this one indexes the entry as a mapping: left as a
        string it matches neither list and the recognizer is never built.

        :param recognizers_conf: The recognizers' configuration
        """

        normalized = [
            {"name": recognizer_conf, "type": "predefined"}
            if isinstance(recognizer_conf, str)
            else recognizer_conf
            for recognizer_conf in recognizers_conf
        ]

        predefined = [
            recognizer_conf
            for recognizer_conf in normalized
            if isinstance(recognizer_conf, dict)
            and ("type" in recognizer_conf and recognizer_conf["type"] == "predefined")
        ]
        custom = [
            recognizer_conf
            for recognizer_conf in normalized
            if isinstance(recognizer_conf, dict)
            and ("type" not in recognizer_conf or recognizer_conf["type"] == "custom")
        ]
        return predefined, custom

    @staticmethod
    def _get_recognizer_languages(
        recognizer_conf: Union[Dict[str, Any], str],
        supported_languages: Iterable[str],
    ) -> List[Dict[str, Any]]:
        """
        Get the different language properties for each recognizer.

        Creating a new recognizer for each supported language.
        If language wasn't specified, create a recognizer for each supported language.

        :param recognizer_conf: The aforementioned recognizer.
        :return: The list of recognizers in the supported languages.
        """
        if isinstance(recognizer_conf, dict) and recognizer_conf.get(
            "supported_language"
        ):
            return [
                {
                    "supported_language": recognizer_conf["supported_language"],
                    "context": recognizer_conf.get("context"),
                }
            ]
        if (
            isinstance(recognizer_conf, str)
            or "supported_languages" not in recognizer_conf
            or recognizer_conf["supported_languages"] is None
        ):
            return [
                {
                    "supported_language": language,
                    "context": RecognizerListLoader._get_recognizer_context(
                        recognizer=recognizer_conf
                    ),
                }
                for language in supported_languages
            ]

        if not recognizer_conf["supported_languages"]:
            return []
        if isinstance(recognizer_conf["supported_languages"][0], str):
            return [
                {
                    "supported_language": language,
                    "context": recognizer_conf.get("context"),
                }
                for language in recognizer_conf["supported_languages"]
            ]

        return [
            {
                "supported_language": language["language"],
                "context": language.get("context", recognizer_conf.get("context")),
            }
            for language in recognizer_conf["supported_languages"]
        ]

    @staticmethod
    def get_recognizer_name(recognizer_conf: Union[Dict[str, Any], str]) -> str:
        """Get the class name for recognizer instantiation.

        Uses 'class_name' if present, otherwise 'name'.

        Logic:
        - If only 'name' exists: Use 'name' as both class name (for instantiation)
          and instance name (passed to __init__)
        - If 'class_name' exists: Use 'class_name' for instantiation and 'name'
          as the instance name (passed to __init__)

        :param recognizer_conf: The recognizer configuration.
        """
        if isinstance(recognizer_conf, str):
            return recognizer_conf
        class_name = recognizer_conf.get("class_name")
        if class_name:
            return class_name
        return recognizer_conf["name"]

    @staticmethod
    def get_all_existing_recognizers(
        cls: Optional[Type[EntityRecognizer]] = None,
    ) -> Set[Type[EntityRecognizer]]:
        """
        Return all subclasses of EntityRecognizer, recursively.

        :param cls: The initial class, if None, cls=EntityRecognizer.
        """

        if not cls:
            cls = EntityRecognizer

        return set(cls.__subclasses__()).union(
            [
                s
                for c in cls.__subclasses__()
                for s in RecognizerListLoader.get_all_existing_recognizers(c)
            ]
        )

    @staticmethod
    def get_existing_recognizer_cls(recognizer_name: str) -> Type[EntityRecognizer]:
        """
        Get the recognizer class by name.

        Returns the requested recognizer class out of the list of all existing
        recognizers currently inheriting from EntityRecognizer.
        Raises a ValueError if the recognizer is not found.

        :param recognizer_name: The name of the recognizer.
        """
        all_existing_recognizers = RecognizerListLoader.get_all_existing_recognizers()
        for recognizer in all_existing_recognizers:
            if recognizer_name == recognizer.__name__:
                return recognizer

        raise PredefinedRecognizerNotFoundError(
            f"Recognizer of name {recognizer_name} was not found in the "
            f"list of recognizers inheriting the EntityRecognizer class"
        )

    @staticmethod
    def _reachable_init_param_names(recognizer_cls: Type[EntityRecognizer]) -> Set[str]:
        """Return constructor-derived parameter names for compatibility callers."""
        from presidio_analyzer.input_validation.recognizer_configuration import (
            constructor_parameters,
        )

        return set(constructor_parameters(recognizer_cls))

    @staticmethod
    def _prepare_recognizer_kwargs(
        recognizer_conf: Dict[str, Any],
        language_conf: Dict[str, Any],
        recognizer_cls: Type[EntityRecognizer],
    ) -> Dict[str, Any]:
        """Delegate legacy helper callers to the shared constructor normalization."""
        from .recognizer_factory import RecognizerFactory

        return RecognizerFactory.prepare_kwargs(
            {**recognizer_conf, **language_conf}, recognizer_cls
        )

    @staticmethod
    def get(
        recognizers: Dict[str, Any],
        supported_languages: Iterable[str],
        global_regex_flags: int,
        supported_countries: Optional[Iterable[str]] = None,
    ) -> Iterable[EntityRecognizer]:
        """
        Create an iterator of recognizers.

        The recognizers are initialized according to configuration loaded
        previously.

        :param recognizers: The recognizer configuration block.
        :param supported_languages: Languages this registry should support.
            Recognizers whose ``supported_language`` falls outside this set
            are dropped.
        :param global_regex_flags: Regex flags applied to pattern recognizers.
        :param supported_countries: Optional country filter (case-insensitive
            ISO-3166 alpha-2 codes — e.g. ``["us", "uk"]``). Mirrors the
            ``supported_languages`` filter: when provided, recognizers
            tagged with a country (via the class-level ``COUNTRY_CODE``
            attribute) are kept only when their code is in this set.
            Locale-agnostic recognizers (``COUNTRY_CODE`` unset / ``None``)
            are always kept. Pass ``None`` (the default) to skip the filter.
        """
        from .recognizer_factory import RecognizerFactory

        recognizers = list(recognizers)
        if not recognizers:
            return []
        specs = RecognizerFactory.create_specs(
            {
                "recognizers": recognizers,
                "supported_languages": list(supported_languages),
                "global_regex_flags": global_regex_flags,
            }
        )
        recognizer_instances = RecognizerFactory.build_all(specs)
        if supported_countries is not None:
            recognizer_instances = RecognizerListLoader.filter_by_countries(
                recognizer_instances, supported_countries
            )

        return recognizer_instances

    @staticmethod
    def _normalize_countries(countries: Iterable[str]) -> Set[str]:
        """Normalize and validate a country-code iterable.

        Accepts any iterable of strings, lower-cases and strips each entry,
        and rejects common footguns up front so misuse fails loudly instead
        of silently returning the wrong subset of recognizers.

        Rejected inputs:

        - A bare ``str`` (e.g. ``"us"`` instead of ``["us"]``) — would
          otherwise iterate over characters and silently match nothing.
        - Non-iterable scalars (``int``, ``None`` is handled by callers).
        - Iterables containing non-string elements.
        - Iterables containing blank / empty strings.

        :param countries: Iterable of ISO-3166-1 alpha-2 codes (case-insensitive).
        :return: A set of lower-cased, trimmed codes; empty set means
            "keep only locale-agnostic recognizers".
        :raises TypeError: If ``countries`` is a bare ``str`` or contains
            non-string elements.
        :raises ValueError: If any element is empty after trimming.
        """
        if isinstance(countries, str):
            raise TypeError(
                "``countries`` must be an iterable of strings (e.g. "
                f"['us', 'uk']), not a bare string {countries!r}."
            )
        try:
            iterator = iter(countries)
        except TypeError as exc:
            raise TypeError(
                "``countries`` must be an iterable of strings (e.g. "
                f"['us', 'uk']), got {type(countries).__name__}."
            ) from exc

        normalized: Set[str] = set()
        for code in iterator:
            if not isinstance(code, str):
                raise TypeError(
                    "Each entry in ``countries`` must be a string, got "
                    f"{type(code).__name__}: {code!r}."
                )
            trimmed = code.strip()
            if not trimmed:
                raise ValueError(
                    f"Country codes must be non-empty strings; got {code!r}."
                )
            normalized.add(trimmed.lower())
        return normalized

    @staticmethod
    def _validate_yaml_country_code(
        recognizer_conf: Union[Dict[str, Any], str],
        recognizer_cls: Type[EntityRecognizer],
        recognizer_name: str,
    ) -> None:
        """Validate the optional YAML ``country_code`` for a predefined recognizer.

        The YAML field is advisory metadata for no-code users; the class
        attribute ``COUNTRY_CODE`` is the source of truth. This method
        catches drift between the two: if the YAML declares a country code
        that disagrees with the class, we raise a ``ValueError`` at load
        time so misconfigurations don't silently weaken the country
        filter. Missing-from-YAML is allowed (the class attribute stands
        on its own); missing-from-class with a YAML value is also a
        misconfiguration and raises.

        :param recognizer_conf: The YAML configuration block for a single
            predefined recognizer.
        :param recognizer_cls: The recognizer class resolved from the
            ``name`` / ``class_name`` field.
        :param recognizer_name: The name used in the YAML, included in
            error messages for actionability.
        """
        if not isinstance(recognizer_conf, dict):
            return
        yaml_country = recognizer_conf.get("country_code")
        if yaml_country is None:
            return

        if not isinstance(yaml_country, str) or not yaml_country.strip():
            raise ValueError(
                f"Recognizer {recognizer_name!r}: YAML ``country_code`` must be "
                f"a non-empty string, got {yaml_country!r}."
            )

        normalized_yaml = yaml_country.strip().lower()
        # Read the ClassVar directly. ``country_code()`` is now an instance
        # method (custom recognizers can carry a tag without subclassing),
        # so we can't call it on the class — but the class attribute is
        # still the canonical declaration for predefined recognizers.
        raw_class_code = getattr(recognizer_cls, "COUNTRY_CODE", None)
        cls_country = (
            raw_class_code.lower() if isinstance(raw_class_code, str) else None
        )

        if cls_country is None:
            raise ValueError(
                f"Recognizer {recognizer_name!r}: YAML declares "
                f"``country_code: {normalized_yaml!r}`` but the recognizer "
                f"class {recognizer_cls.__name__} has no ``COUNTRY_CODE`` "
                f"attribute. Set ``COUNTRY_CODE = {normalized_yaml!r}`` on "
                f"the class, or remove the YAML field."
            )

        if cls_country != normalized_yaml:
            raise ValueError(
                f"Recognizer {recognizer_name!r}: YAML "
                f"``country_code: {normalized_yaml!r}`` disagrees with "
                f"class-level ``{recognizer_cls.__name__}.COUNTRY_CODE = "
                f"{raw_class_code!r}``. The class attribute is the source "
                f"of truth — update one to match the other."
            )

    @staticmethod
    def _get_recognizer_country(recognizer: EntityRecognizer) -> Optional[str]:
        """Return the country code for a recognizer, or ``None`` if generic.

        Resolution order:

        1. The instance's :meth:`EntityRecognizer.country_code`, which
           returns whichever of the class-level ``COUNTRY_CODE`` attribute
           or the constructor ``country_code=`` kwarg was set (already
           reconciled at construction time). This covers both predefined
           recognizers (class-level) and custom recognizers tagged via
           YAML / ``from_dict`` / Python kwargs (instance-level).
        2. **Transitional fallback**: if neither path produced a country,
           try to infer one from the module path. Predefined recognizers
           live under ``predefined_recognizers/country_specific/<country>/
           ...``, so the segment immediately following ``country_specific``
           is taken as the country code. This fallback exists for any
           custom recognizer that follows the same directory layout but
           has not yet adopted either tagging mechanism.

        Recognizers outside both paths (generic, NER, NLP engine,
        third-party, and locale-agnostic user-supplied recognizers) return
        ``None``.

        :param recognizer: The recognizer instance whose country to resolve.
        """
        try:
            declared = recognizer.country_code()
        except Exception:  # pragma: no cover — defensive: third-party subclasses
            declared = None
        if isinstance(declared, str) and declared:
            return declared.lower()

        module_name = type(recognizer).__module__ or ""
        parts = module_name.split(".")
        try:
            idx = parts.index(_COUNTRY_SPECIFIC_MODULE_SEGMENT)
        except ValueError:
            return None
        if idx + 1 >= len(parts):
            return None
        return parts[idx + 1].lower()

    @staticmethod
    def filter_by_countries(
        recognizers: Iterable[EntityRecognizer],
        countries: Iterable[str],
    ) -> List[EntityRecognizer]:
        """Filter a list of recognizers to the requested countries.

        Filtering rule (single invariant):

        - ``country_code is None`` → **always kept**. Locale-agnostic
          recognizers (generic built-ins like ``CreditCardRecognizer``, NER /
          NLP engine recognizers, and any custom recognizer that has not
          opted into the country tag) are unaffected by the filter.
        - ``country_code is not None`` → kept iff the code appears in
          ``countries`` (case-insensitive).

        The "untagged = always included" rule is what keeps the migration
        backwards compatible: custom recognizers built before ``country_code``
        existed continue to fire regardless of the requested country set, and
        users opt into stricter filtering simply by setting ``country_code``
        on their custom recognizers.

        When ``countries`` contains a code that does not match any recognizer
        in the input list, a ``WARNING`` is logged with the country and a
        hint about ``country_code`` so silent zero-result filters are easier
        to debug.

        :param recognizers: The recognizers to filter.
        :param countries: Country codes to keep (e.g. ``["us", "uk"]``). An
            empty iterable keeps only locale-agnostic recognizers.
        :return: A new list preserving the original order.
        :raises TypeError: If ``countries`` is a bare string or otherwise
            not an iterable of strings.
        :raises ValueError: If any element is empty / blank after trimming.
        """
        recognizer_list = list(recognizers)
        allowed = RecognizerListLoader._normalize_countries(countries)

        filtered: List[EntityRecognizer] = []
        seen_countries: Set[str] = set()
        for recognizer in recognizer_list:
            country = RecognizerListLoader._get_recognizer_country(recognizer)
            if country is None:
                filtered.append(recognizer)
                continue
            seen_countries.add(country)
            if country in allowed:
                filtered.append(recognizer)

        missing = sorted(allowed - seen_countries)
        for code in missing:
            logger.warning(
                "Country filter: no recognizer matched country_code=%r. "
                "If you have custom recognizers for %r, set country_code=%r "
                "on them to include them in country-filtered loads.",
                code,
                code,
                code,
            )

        return filtered


class RecognizerConfigurationLoader:
    """A utility class that initializes recognizer registry configuration."""

    mandatory_keys = [
        "supported_languages",
        "recognizers",
        "global_regex_flags",
    ]

    @staticmethod
    def _merge_configuration(
        registry_configuration: Dict, config_from_file: Dict[str, Any]
    ) -> Dict:
        """
        Add missing keys to the configuration.

        Missing keys are added using the configuration read from file.
        :param registry_configuration: The configuration to update.
        :param config_from_file: The configuration coming from the conf file.
        """
        registry_configuration.update(
            {
                k: v
                for k, v in config_from_file.items()
                if k not in list(registry_configuration.keys())
            }
        )

        # Validation is now handled by Pydantic via ConfigurationValidator
        return registry_configuration

    @staticmethod
    def get(
        conf_file: Optional[Union[Path, str]] = None,
        registry_configuration: Optional[Dict] = None,
    ) -> Union[Dict[str, Any]]:
        """Get the configuration from the provided file or dict.

        :param conf_file: The configuration file
        to read the recognizer registry configuration from.
        :param registry_configuration: The configuration to use.
        """

        if conf_file and registry_configuration:
            raise ValueError(
                "Either conf_file or registry_configuration should"
                " be provided, not both."
            )

        configuration = {}
        config_from_file = {}
        use_defaults = True

        if registry_configuration:
            configuration = registry_configuration.copy()
            # Check if registry_configuration has all mandatory keys
            # Note: supported_languages is now optional,
            # so we only check for recognizers
            mandatory_keys_set = {"recognizers", "global_regex_flags"}
            config_keys = set(configuration.keys())
            if mandatory_keys_set.issubset(config_keys):
                use_defaults = False

        if conf_file:
            try:
                with open(conf_file) as file:
                    config_from_file = yaml.safe_load(file)
                use_defaults = False

            except OSError:
                logger.warning(
                    f"configuration file {conf_file} not found.  Using default config."
                )
                with open(RecognizerConfigurationLoader._get_full_conf_path()) as file:
                    config_from_file = yaml.safe_load(file)
                use_defaults = False

            except Exception as e:
                raise ValueError(f"Failed to parse file {conf_file}. Error: {str(e)}")

        # Load defaults if needed (no config provided,
        # or registry_configuration is incomplete)
        if use_defaults:
            with open(RecognizerConfigurationLoader._get_full_conf_path()) as file:
                config_from_file = yaml.safe_load(file)

        if config_from_file and not isinstance(config_from_file, dict):
            raise TypeError(
                f"The configuration in file {conf_file} should be a valid YAML, "
                f"got {type(config_from_file)}"
            )

        if registry_configuration and not isinstance(registry_configuration, dict):
            raise TypeError(
                f"Expected registry_configuration to be a dict, "
                f"got {type(registry_configuration)}"
            )

        # Check if config_from_file has any invalid keys
        # (keys that aren't mandatory or valid optional keys)
        # If it has keys but none of them are mandatory keys,
        # it's likely an invalid config
        if config_from_file and conf_file:
            config_keys = set(config_from_file.keys())
            mandatory_keys_set = {"recognizers"}  # Only recognizers is truly mandatory

            # If config has keys but none are mandatory and it's from a conf_file,
            # it's probably invalid - don't merge with defaults
            if config_keys and not config_keys.intersection(mandatory_keys_set):
                raise ValueError(
                    f"Configuration file {conf_file} does not contain any of the "
                    f"mandatory keys: {list(mandatory_keys_set)}. "
                    f"Found keys: {list(config_keys)}"
                )

        configuration = RecognizerConfigurationLoader._merge_configuration(
            registry_configuration=configuration, config_from_file=config_from_file
        )

        return configuration

    @staticmethod
    def _get_full_conf_path(
        default_conf_file: Union[Path, str] = "default_recognizers.yaml",
    ) -> Path:
        """Return a Path to the default conf file."""
        return Path(Path(__file__).parent, "../conf", default_conf_file)
