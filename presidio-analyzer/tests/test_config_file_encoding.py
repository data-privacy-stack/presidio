"""Configuration files are UTF-8, whatever the locale's preferred encoding is."""

import json
import os
import subprocess
import sys
import textwrap

import pytest

RECOGNIZER_YAML = """
supported_languages:
  - es
global_regex_flags: 26
recognizers:
  - name: TitleRecognizer
    supported_language: es
    supported_entity: TITLE
    type: custom
    deny_list:
      - Señor
"""

ANALYZER_YAML = """
supported_languages:
  - es
default_score_threshold: 0
recognizer_registry:
  supported_languages:
    - es
  global_regex_flags: 26
  recognizers:
    - name: TitleRecognizer
      supported_language: es
      supported_entity: TITLE
      type: custom
      deny_list:
        - Señor
"""

NLP_ENGINE_YAML = """
nlp_engine_name: spacy
models:
  - lang_code: es
    model_name: es_core_news_md
ner_model_configuration:
  model_to_presidio_entity_mapping:
    Señor: TITLE
"""

TEXT = "Hola Señor García"

PROMPT = "Extrae los datos personales del señor García."

# Each snippet reads the file at ``path`` through a public loader and prints
# what it read as JSON, which keeps the subprocess output ASCII.
LOADERS = {
    "recognizer_registry_provider": (
        RECOGNIZER_YAML,
        """
        from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider
        provider = RecognizerRegistryProvider(conf_file=path)
        registry = provider.create_recognizer_registry()
        title = next(r for r in registry.recognizers if r.name == "TitleRecognizer")
        result = title.analyze(TEXT, entities=["TITLE"])
        print(json.dumps([[r.start, r.end] for r in result]))
        """,
        [[5, 10]],
    ),
    "analyzer_engine_provider": (
        ANALYZER_YAML,
        """
        from presidio_analyzer import AnalyzerEngineProvider
        configuration = AnalyzerEngineProvider(path).configuration
        recognizer = configuration["recognizer_registry"]["recognizers"][0]
        print(json.dumps(recognizer["deny_list"]))
        """,
        ["Señor"],
    ),
    "nlp_engine_provider": (
        NLP_ENGINE_YAML,
        """
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        configuration = NlpEngineProvider(conf_file=path).nlp_configuration
        mapping = configuration["ner_model_configuration"][
            "model_to_presidio_entity_mapping"
        ]
        print(json.dumps(list(mapping)))
        """,
        ["Señor"],
    ),
    "llm_load_yaml_file": (
        RECOGNIZER_YAML,
        """
        from presidio_analyzer.llm_utils import load_yaml_file
        print(json.dumps(load_yaml_file(path)["recognizers"][0]["deny_list"]))
        """,
        ["Señor"],
    ),
    "llm_load_prompt_file": (
        PROMPT,
        """
        from presidio_analyzer.llm_utils import load_prompt_file
        print(json.dumps(load_prompt_file(path)))
        """,
        PROMPT,
    ),
}


@pytest.mark.parametrize("loader", sorted(LOADERS))
def test_config_file_is_read_as_utf8_under_a_non_utf8_locale(tmp_path, loader):
    """A UTF-8 file loads unchanged when the locale encoding is not UTF-8.

    The loader runs in a child interpreter whose locale encoding is ASCII on
    POSIX (C locale, no coercion, UTF-8 mode off) and the ANSI code page on
    Windows, so reading the file with the locale encoding garbles or rejects it.
    """
    content, snippet, expected = LOADERS[loader]
    path = tmp_path / "config.yaml"
    path.write_bytes(content.encode("utf-8"))

    # The child decodes its command line with the locale encoding, so the
    # script itself stays ASCII and spells the analyzed text with escapes.
    script = (
        "import json, sys\n"
        "path = sys.argv[1]\n"
        f"TEXT = {ascii(TEXT)}\n" + textwrap.dedent(snippet)
    )
    env = {
        **os.environ,
        "LC_ALL": "C",
        "PYTHONCOERCECLOCALE": "0",
        "PYTHONUTF8": "0",
    }
    completed = subprocess.run(
        [sys.executable, "-c", script, str(path)],
        capture_output=True,
        env=env,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    assert json.loads(completed.stdout.decode("ascii").splitlines()[-1]) == expected
