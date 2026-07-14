"""Tests for LangExtract recognizer hierarchy using mocks."""
import pytest
import urllib.error
from unittest.mock import Mock, patch, MagicMock


def create_test_config(
    supported_entities=None,
    entity_mappings=None,
    model_id="qwen2.5:1.5b",
    model_url="http://localhost:11434",
    temperature=0.0,
    min_score=0.5,
    labels_to_ignore=None,
    enable_generic_consolidation=True
):
    """Create test config."""
    if supported_entities is None:
        supported_entities = ["PERSON", "EMAIL_ADDRESS"]
    if entity_mappings is None:
        entity_mappings = {"person": "PERSON", "email": "EMAIL_ADDRESS"}
    if labels_to_ignore is None:
        labels_to_ignore = []
    
    return {
        "lm_recognizer": {
            "supported_entities": supported_entities,
            "labels_to_ignore": labels_to_ignore,
            "enable_generic_consolidation": enable_generic_consolidation,
            "min_score": min_score,
        },
        "langextract": {
            "prompt_file": "presidio-analyzer/presidio_analyzer/conf/langextract_prompts/default_pii_phi_prompt.j2",
            "examples_file": "presidio-analyzer/presidio_analyzer/conf/langextract_prompts/default_pii_phi_examples.yaml",
            "model": {
                "model_id": model_id,
                "provider": {
                    "name": "ollama",
                    "kwargs": {
                        "model_url": model_url,
                    },
                    "extract_params": {
                    },
                    "language_model_params": {
                    }
                },
                "temperature": temperature,
            },
            "entity_mappings": entity_mappings,
        }
    }


class TestBasicLangExtractRecognizerInitialization:
    """Test BasicLangExtractRecognizer initialization and configuration loading."""

    def test_when_langextract_not_installed_then_raises_import_error(self):
        """Test that ImportError is raised when langextract is not installed."""
        with patch(
            'presidio_analyzer.llm_utils.langextract_helper.lx',
            None
        ):
            from presidio_analyzer.predefined_recognizers.third_party.basic_langextract_recognizer import BasicLangExtractRecognizer
            with pytest.raises(ImportError, match="LangExtract is not installed"):
                BasicLangExtractRecognizer()

    def test_when_initialized_with_mocked_ollama_then_succeeds(self, tmp_path):
        """Test BasicLangExtractRecognizer initialization."""
        import yaml
        
        config = create_test_config(
            supported_entities=["PERSON", "EMAIL_ADDRESS"],
            entity_mappings={"person": "PERSON", "email": "EMAIL_ADDRESS"},
            model_id="qwen2.5:1.5b",
            model_url="http://localhost:11434",
            temperature=0.0,
            min_score=0.5
        )

        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        with patch('presidio_analyzer.llm_utils.langextract_helper.lx',
                   return_value=Mock()):
            
            from presidio_analyzer.predefined_recognizers.third_party.basic_langextract_recognizer import BasicLangExtractRecognizer
            recognizer = BasicLangExtractRecognizer(config_path=str(config_file))
            
            # Verify initialization
            assert recognizer.name == "BasicLangExtractRecognizer"
            assert recognizer.model_id == "qwen2.5:1.5b"
            assert len(recognizer.supported_entities) == 3  # PERSON, EMAIL_ADDRESS, GENERIC_PII_ENTITY
            assert "PERSON" in recognizer.supported_entities
            assert "EMAIL_ADDRESS" in recognizer.supported_entities
            assert "GENERIC_PII_ENTITY" in recognizer.supported_entities
            
            # Verify inheritance hierarchy
            from presidio_analyzer.lm_recognizer import LMRecognizer
            from presidio_analyzer.predefined_recognizers.third_party.langextract_recognizer import LangExtractRecognizer
            assert isinstance(recognizer, BasicLangExtractRecognizer)
            assert isinstance(recognizer, LangExtractRecognizer)
            assert isinstance(recognizer, LMRecognizer)

    def test_when_config_file_missing_then_raises_file_not_found_error(self):
        """Test FileNotFoundError when config file doesn't exist."""
        with patch('presidio_analyzer.llm_utils.langextract_helper.lx',
                   return_value=Mock()):
            from presidio_analyzer.predefined_recognizers.third_party.basic_langextract_recognizer import BasicLangExtractRecognizer
            with pytest.raises(FileNotFoundError, match="File not found"):
                BasicLangExtractRecognizer(config_path="/nonexistent/path.yaml")

    def test_when_model_section_missing_then_raises_value_error(self, tmp_path):
        """Test ValueError when config missing 'langextract.model' section."""
        import yaml
        
        config = {
            "lm_recognizer": {
                "supported_entities": ["PERSON"],
                "labels_to_ignore": [],
                "enable_generic_consolidation": True,
                "min_score": 0.5,
            },
            "langextract": {
                "prompt_file": "presidio-analyzer/presidio_analyzer/conf/langextract_prompts/default_pii_phi_prompt.j2",
                "examples_file": "presidio-analyzer/presidio_analyzer/conf/langextract_prompts/default_pii_phi_examples.yaml",
                "entity_mappings": {"person": "PERSON"},
                # Missing 'model' section
            }
        }
        
        config_file = tmp_path / "bad_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        with patch('presidio_analyzer.llm_utils.langextract_helper.lx',
                   return_value=Mock()):
            from presidio_analyzer.predefined_recognizers.third_party.basic_langextract_recognizer import BasicLangExtractRecognizer
            with pytest.raises(ValueError, match="Configuration must contain 'langextract.model'"):
                BasicLangExtractRecognizer(config_path=str(config_file))

    def test_when_model_id_missing_then_raises_value_error(self, tmp_path):
        """Test ValueError when model_id is missing."""
        import yaml
        
        config = {
            "lm_recognizer": {
                "supported_entities": ["PERSON"],
                "labels_to_ignore": [],
                "enable_generic_consolidation": True,
                "min_score": 0.5,
            },
            "langextract": {
                "prompt_file": "presidio-analyzer/presidio_analyzer/conf/langextract_prompts/default_pii_phi_prompt.j2",
                "examples_file": "presidio-analyzer/presidio_analyzer/conf/langextract_prompts/default_pii_phi_examples.yaml",
                "entity_mappings": {"person": "PERSON"},
                "model": {
                    # Missing model_id
                    "provider": {
                        "name": "ollama",
                    },
                },
            }
        }
        
        config_file = tmp_path / "bad_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        with patch('presidio_analyzer.llm_utils.langextract_helper.lx',
                   return_value=Mock()):
            from presidio_analyzer.predefined_recognizers.third_party.basic_langextract_recognizer import BasicLangExtractRecognizer
            with pytest.raises(ValueError, match="Configuration must contain 'langextract.model.model_id'"):
                BasicLangExtractRecognizer(config_path=str(config_file))

    def test_when_provider_missing_then_raises_value_error(self, tmp_path):
        """Test ValueError when model_url is missing."""
        import yaml
        
        config = {
            "lm_recognizer": {
                "supported_entities": ["PERSON"],
                "labels_to_ignore": [],
                "enable_generic_consolidation": True,
                "min_score": 0.5,
            },
            "langextract": {
                "prompt_file": "presidio-analyzer/presidio_analyzer/conf/langextract_prompts/default_pii_phi_prompt.j2",
                "examples_file": "presidio-analyzer/presidio_analyzer/conf/langextract_prompts/default_pii_phi_examples.yaml",
                "entity_mappings": {"person": "PERSON"},
                "model": {
                    "model_id": "qwen2.5:1.5b"
                    # Missing provider
                }
            }
        }
        
        config_file = tmp_path / "bad_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        with patch('presidio_analyzer.llm_utils.langextract_helper.lx',
                   return_value=Mock()):
            from presidio_analyzer.predefined_recognizers.third_party.basic_langextract_recognizer import BasicLangExtractRecognizer
            with pytest.raises(ValueError, match="Configuration must contain 'langextract.model.provider.name'"):
                BasicLangExtractRecognizer(config_path=str(config_file))


class TestBasicLangExtractRecognizerAnalyze:
    """Test the analyze method with mocked LangExtract."""

    @pytest.fixture
    def mock_recognizer(self, tmp_path):
        """Fixture to create a mocked BasicLangExtractRecognizer."""
        import yaml
        
        config = create_test_config(
            supported_entities=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER"],
            entity_mappings={
                "person": "PERSON",
                "email": "EMAIL_ADDRESS",
                "phone": "PHONE_NUMBER"
            },
            model_id="qwen2.5:1.5b",
            model_url="http://localhost:11434",
            temperature=0.0,
            min_score=0.5
        )

        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        with patch('presidio_analyzer.llm_utils.langextract_helper.lx',
                   return_value=Mock()):
            from presidio_analyzer.predefined_recognizers.third_party.basic_langextract_recognizer import BasicLangExtractRecognizer
            return BasicLangExtractRecognizer(config_path=str(config_file))

    def test_when_text_contains_person_then_detects_entity(self, mock_recognizer):
        """Test analysis detecting a person entity with mocked LangExtract."""
        text = "My name is John Doe"

        # Create mock extraction
        mock_extraction = Mock()
        mock_extraction.extraction_class = "person"
        mock_extraction.extraction_text = "John Doe"
        mock_extraction.char_interval = Mock()
        mock_extraction.char_interval.start_pos = 11
        mock_extraction.char_interval.end_pos = 19
        mock_extraction.alignment_status = "MATCH_EXACT"
        mock_extraction.attributes = {"type": "full_name"}

        mock_result = Mock()
        mock_result.extractions = [mock_extraction]

        with patch('langextract.extract', return_value=mock_result):
            results = mock_recognizer.analyze(text, entities=["PERSON"])

        assert len(results) == 1
        assert results[0].entity_type == "PERSON"
        assert results[0].start == 11
        assert results[0].end == 19
        assert results[0].score == 0.95  # MATCH_EXACT score

    def test_when_text_contains_multiple_entities_then_detects_all(self, mock_recognizer):
        """Test analysis detecting multiple entity types."""
        text = "Contact John Doe at john@example.com or 555-1234"

        # Create mock extractions
        person_extraction = Mock()
        person_extraction.extraction_class = "person"
        person_extraction.extraction_text = "John Doe"
        person_extraction.char_interval = Mock(start_pos=8, end_pos=16)
        person_extraction.alignment_status = "MATCH_EXACT"
        person_extraction.attributes = {}

        email_extraction = Mock()
        email_extraction.extraction_class = "email"
        email_extraction.extraction_text = "john@example.com"
        email_extraction.char_interval = Mock(start_pos=20, end_pos=36)
        email_extraction.alignment_status = "MATCH_EXACT"
        email_extraction.attributes = {}

        phone_extraction = Mock()
        phone_extraction.extraction_class = "phone"
        phone_extraction.extraction_text = "555-1234"
        phone_extraction.char_interval = Mock(start_pos=40, end_pos=48)
        phone_extraction.alignment_status = "MATCH_FUZZY"
        phone_extraction.attributes = {}

        mock_result = Mock()
        mock_result.extractions = [person_extraction, email_extraction, phone_extraction]

        with patch('langextract.extract', return_value=mock_result):
            results = mock_recognizer.analyze(text)

        assert len(results) == 3
        assert results[0].entity_type == "PERSON"
        assert results[1].entity_type == "EMAIL_ADDRESS"
        assert results[2].entity_type == "PHONE_NUMBER"
        assert results[2].score == 0.80  # MATCH_FUZZY score

    def test_when_text_is_empty_then_returns_no_results(self, mock_recognizer):
        """Test analysis with empty text returns no results."""
        results = mock_recognizer.analyze("")
        assert len(results) == 0

        results = mock_recognizer.analyze("   ")
        assert len(results) == 0

    def test_when_no_entities_match_then_returns_empty_list(self, mock_recognizer):
        """Test analysis when requested entities don't match supported entities."""
        text = "Some text here"
        
        # Request unsupported entity type
        results = mock_recognizer.analyze(text, entities=["CREDIT_CARD"])
        assert len(results) == 0

    def test_when_entities_requested_then_filters_results(self, mock_recognizer):
        """Test that analyze filters results based on requested entities."""
        from presidio_analyzer import RecognizerResult
        
        text = "Contact John Doe at john@example.com"

        # Create RecognizerResult objects (what _call_llm returns)
        person_result = RecognizerResult(
            entity_type="PERSON",
            start=8,
            end=16,
            score=0.95
        )
        
        email_result = RecognizerResult(
            entity_type="EMAIL_ADDRESS",
            start=20,
            end=36,
            score=0.95
        )

        with patch.object(mock_recognizer, '_call_llm', return_value=[person_result, email_result]):
            # Request only PERSON entities - EMAIL_ADDRESS should be filtered out by analyze()
            results = mock_recognizer.analyze(text, entities=["PERSON"])

        # Should only return PERSON, EMAIL_ADDRESS filtered by analyze() method
        assert len(results) == 1
        assert results[0].entity_type == "PERSON"
        assert results[0].start == 8
        assert results[0].end == 16

    def test_when_min_score_set_then_filters_low_confidence_results(self, mock_recognizer):
        """Test that results below min_score are filtered out."""
        # Set min_score to 0.5 (default in config)
        text = "Some text"

        mock_extraction = Mock()
        mock_extraction.extraction_class = "person"
        mock_extraction.extraction_text = "Some text"
        mock_extraction.char_interval = Mock(start_pos=0, end_pos=9)
        mock_extraction.alignment_status = "NOT_ALIGNED"  # Score 0.60
        mock_extraction.attributes = {}

        mock_result = Mock()
        mock_result.extractions = [mock_extraction]

        with patch('langextract.extract', return_value=mock_result):
            results = mock_recognizer.analyze(text)

        # NOT_ALIGNED has score 0.60, which is above min_score 0.5
        assert len(results) == 1

    def test_when_langextract_raises_exception_then_exception_propagates(self, mock_recognizer):
        """Test that exceptions from LangExtract propagate to caller."""
        text = "Some text"

        with patch('langextract.extract', side_effect=Exception("LangExtract error")):
            with pytest.raises(Exception, match="LangExtract error"):
                mock_recognizer.analyze(text)

    def test_when_entity_has_no_mapping_and_consolidation_enabled_then_creates_generic(
        self, mock_recognizer
    ):
        """Test that extractions with unknown entity classes become GENERIC_PII_ENTITY."""
        text = "Some text"

        mock_extraction = Mock()
        mock_extraction.extraction_class = "unknown_type"  # Not in entity_mappings
        mock_extraction.extraction_text = "Some text"
        mock_extraction.char_interval = Mock(start_pos=0, end_pos=9)
        mock_extraction.alignment_status = "MATCH_EXACT"
        mock_extraction.attributes = {}

        mock_result = Mock()
        mock_result.extractions = [mock_extraction]

        with patch('langextract.extract', return_value=mock_result):
            results = mock_recognizer.analyze(text)

        # Unknown entity type should be consolidated to GENERIC_PII_ENTITY
        assert len(results) == 1
        assert results[0].entity_type == "GENERIC_PII_ENTITY"
        assert results[0].recognition_metadata["original_entity_type"] == "UNKNOWN_TYPE"
        assert results[0].start == 0
        assert results[0].end == 9

    def test_when_entity_has_no_mapping_and_consolidation_disabled_then_skips(self, tmp_path):
        """Test that unknown entities are skipped when consolidation is disabled."""
        import yaml
        
        # Create config with consolidation disabled
        config = create_test_config(
            supported_entities=["PERSON", "EMAIL_ADDRESS"],
            entity_mappings={"person": "PERSON", "email": "EMAIL_ADDRESS"},
            enable_generic_consolidation=False
        )

        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        with patch('presidio_analyzer.llm_utils.langextract_helper.lx',
                   return_value=Mock()):
            
            from presidio_analyzer.predefined_recognizers.third_party.basic_langextract_recognizer import BasicLangExtractRecognizer
            recognizer = BasicLangExtractRecognizer(config_path=str(config_file))

        text = "Some text"

        mock_extraction = Mock()
        mock_extraction.extraction_class = "unknown_type"  # Not in entity_mappings
        mock_extraction.extraction_text = "Some text"
        mock_extraction.char_interval = Mock(start_pos=0, end_pos=9)
        mock_extraction.alignment_status = "MATCH_EXACT"
        mock_extraction.attributes = {}

        mock_result = Mock()
        mock_result.extractions = [mock_extraction]

        with patch('langextract.extract', return_value=mock_result):
            results = recognizer.analyze(text)

        # Unknown entity type should be skipped when consolidation is disabled
        assert len(results) == 0


class TestBasicLangExtractRecognizerParameterConfiguration:
    """Test parameter configuration with defaults and YAML overrides."""

    def test_when_no_config_params_then_uses_defaults(self, tmp_path):
        """Test that default extract params are used when not in config."""
        import yaml
        
        config = create_test_config()
        # No extract params in config - should use defaults
        
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        with patch('presidio_analyzer.llm_utils.langextract_helper.lx',
                   return_value=Mock()):
            from presidio_analyzer.predefined_recognizers.third_party.basic_langextract_recognizer import BasicLangExtractRecognizer
            recognizer = BasicLangExtractRecognizer(config_path=str(config_file))
            
            # Verify defaults are set
            assert recognizer._extract_params["max_char_buffer"] == 400
            assert recognizer._extract_params["use_schema_constraints"] is False
            assert recognizer._extract_params["fence_output"] is False
            assert recognizer._language_model_params["timeout"] == 240
            assert recognizer._language_model_params["num_ctx"] == 8192

    def test_when_config_has_params_then_overrides_defaults(self, tmp_path):
        """Test that config values override defaults."""
        import yaml
        
        config = create_test_config()
        # Add custom values to override defaults
        config["langextract"]["model"]["provider"]["extract_params"]["max_char_buffer"] = 1000
        config["langextract"]["model"]["provider"]["extract_params"]["use_schema_constraints"] = True
        config["langextract"]["model"]["provider"]["extract_params"]["fence_output"] = True
        config["langextract"]["model"]["provider"]["language_model_params"]["timeout"] = 120
        config["langextract"]["model"]["provider"]["language_model_params"]["num_ctx"] = 4096
        
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        with patch('presidio_analyzer.llm_utils.langextract_helper.lx',
                   return_value=Mock()):
            from presidio_analyzer.predefined_recognizers.third_party.basic_langextract_recognizer import BasicLangExtractRecognizer
            recognizer = BasicLangExtractRecognizer(config_path=str(config_file))
            
            # Verify config values override defaults
            assert recognizer._extract_params["max_char_buffer"] == 1000
            assert recognizer._extract_params["use_schema_constraints"] is True
            assert recognizer._extract_params["fence_output"] is True
            assert recognizer._language_model_params["timeout"] == 120
            assert recognizer._language_model_params["num_ctx"] == 4096

    def test_when_partial_config_params_then_uses_defaults_for_missing(self, tmp_path):
        """Test that only some params can be overridden."""
        import yaml
        
        config = create_test_config()
        # Override only some params
        config["langextract"]["model"]["provider"]["extract_params"]["max_char_buffer"] = 500
        config["langextract"]["model"]["provider"]["language_model_params"]["timeout"] = 60
        
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        with patch('presidio_analyzer.llm_utils.langextract_helper.lx',
                   return_value=Mock()):
            from presidio_analyzer.predefined_recognizers.third_party.basic_langextract_recognizer import BasicLangExtractRecognizer
            recognizer = BasicLangExtractRecognizer(config_path=str(config_file))
            
            # Verify overridden values
            assert recognizer._extract_params["max_char_buffer"] == 500
            assert recognizer._language_model_params["timeout"] == 60
            
            # Verify defaults for non-overridden params
            assert recognizer._extract_params["use_schema_constraints"] is False
            assert recognizer._extract_params["fence_output"] is False
            assert recognizer._language_model_params["num_ctx"] == 8192

    def test_when_analyze_called_then_params_passed_to_langextract(self, tmp_path):
        """Test that configured params are passed to langextract.extract()."""
        import yaml
        
        config = create_test_config()
        config["langextract"]["model"]["provider"]["extract_params"]["max_char_buffer"] = 1500
        config["langextract"]["model"]["provider"]["language_model_params"]["timeout"] = 180
        
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        with patch('presidio_analyzer.llm_utils.langextract_helper.lx',
                   return_value=Mock()):
            from presidio_analyzer.predefined_recognizers.third_party.basic_langextract_recognizer import BasicLangExtractRecognizer
            recognizer = BasicLangExtractRecognizer(config_path=str(config_file))

        text = "My name is John Doe"
        
        mock_extraction = Mock()
        mock_extraction.extraction_class = "person"
        mock_extraction.extraction_text = "John Doe"
        mock_extraction.char_interval = Mock(start_pos=11, end_pos=19)
        mock_extraction.alignment_status = "MATCH_EXACT"
        mock_extraction.attributes = {}

        mock_result = Mock()
        mock_result.extractions = [mock_extraction]

        with patch('langextract.extract', return_value=mock_result) as mock_extract:
            recognizer.analyze(text)
            
            # Verify extract was called
            assert mock_extract.called
            call_kwargs = mock_extract.call_args[1]

            # Verify extract params were passed
            assert call_kwargs["max_char_buffer"] == 1500
            assert call_kwargs["use_schema_constraints"] is False
            assert call_kwargs["fence_output"] is False
            
            # Verify language model params were passed
            assert "language_model_params" in call_kwargs
            assert call_kwargs["language_model_params"]["timeout"] == 180
            assert call_kwargs["language_model_params"]["num_ctx"] == 8192
            
            # Verify provider params
            assert call_kwargs["config"].model_id == "qwen2.5:1.5b"
            assert call_kwargs["config"].provider == "ollama"
            assert call_kwargs["config"].provider_kwargs["model_url"] == "http://localhost:11434"

            # Regression: language_model_params must also surface on
            # ModelConfig.provider_kwargs, because langextract.extract()
            # ignores `language_model_params` when `config` is passed and
            # only reads values from ModelConfig.provider_kwargs in that
            # branch. Without this, `timeout` and `num_ctx` are silently
            # dropped and Ollama falls back to its 120s default.
            assert call_kwargs["config"].provider_kwargs["timeout"] == 180
            assert call_kwargs["config"].provider_kwargs["num_ctx"] == 8192

    def test_language_model_params_reach_provider_kwargs(self, tmp_path):
        """Regression test: values under provider.language_model_params in the
        yaml must end up on ModelConfig.provider_kwargs so they actually reach
        the provider constructor (e.g. OllamaLanguageModel(timeout=...)).

        Prior to the fix, BasicLangExtractRecognizer only copied
        provider.kwargs onto ModelConfig.provider_kwargs, and
        provider.language_model_params was forwarded to lx.extract() as a
        separate argument — but langextract.extract() ignores that argument
        when config is passed directly, so values like `timeout` and
        `num_ctx` were silently dropped.
        """
        import yaml

        config = create_test_config()
        config["langextract"]["model"]["provider"]["language_model_params"]["timeout"] = 600
        config["langextract"]["model"]["provider"]["language_model_params"]["num_ctx"] = 16384

        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        with patch('presidio_analyzer.llm_utils.langextract_helper.lx',
                   return_value=Mock()):
            from presidio_analyzer.predefined_recognizers.third_party.basic_langextract_recognizer import BasicLangExtractRecognizer
            recognizer = BasicLangExtractRecognizer(config_path=str(config_file))

        provider_kwargs = recognizer._get_provider_params()["config"].provider_kwargs
        assert provider_kwargs["timeout"] == 600
        assert provider_kwargs["num_ctx"] == 16384

    def test_provider_kwargs_take_precedence_over_language_model_params(self, tmp_path):
        """Explicit `provider.kwargs:` entries must win over values of the
        same name under `provider.language_model_params:`. This preserves
        backward compatibility for configs that already place timeout in
        `kwargs:` as a workaround.
        """
        import yaml

        config = create_test_config()
        config["langextract"]["model"]["provider"]["kwargs"]["timeout"] = 900
        config["langextract"]["model"]["provider"]["language_model_params"]["timeout"] = 60

        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        with patch('presidio_analyzer.llm_utils.langextract_helper.lx',
                   return_value=Mock()):
            from presidio_analyzer.predefined_recognizers.third_party.basic_langextract_recognizer import BasicLangExtractRecognizer
            recognizer = BasicLangExtractRecognizer(config_path=str(config_file))

        provider_kwargs = recognizer._get_provider_params()["config"].provider_kwargs
        # The explicit kwargs: value wins
        assert provider_kwargs["timeout"] == 900

    def test_when_kwargs_null_in_yaml_then_no_crash(self, tmp_path):
        """Verify that `kwargs: null` (or an empty `kwargs:` key) in the YAML
        does not raise a TypeError. Both provider.kwargs and
        provider.language_model_params must tolerate None values from the
        YAML parser.
        """
        import yaml

        config = create_test_config()
        # Simulate `kwargs: null` in YAML
        config["langextract"]["model"]["provider"]["kwargs"] = None
        config["langextract"]["model"]["provider"]["language_model_params"] = None

        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        with patch('presidio_analyzer.llm_utils.langextract_helper.lx',
                   return_value=Mock()):
            from presidio_analyzer.predefined_recognizers.third_party.basic_langextract_recognizer import BasicLangExtractRecognizer
            # Should not raise TypeError
            recognizer = BasicLangExtractRecognizer(config_path=str(config_file))

        provider_kwargs = recognizer._get_provider_params()["config"].provider_kwargs
        # When kwargs/language_model_params are null, explicit kwargs are empty
        # but the class-level DEFAULT_LANGUAGE_MODEL_PARAMS are still merged in.
        # The key requirement is that no TypeError is raised, and the defaults are present.
        assert "timeout" in provider_kwargs
        assert "num_ctx" in provider_kwargs

