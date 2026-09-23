"""Keep the executable, model-free user workflow sample covered by CI."""

import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path

import pytest


def test_configuration_workflow_script_completes_without_external_models():
    script = (
        Path(__file__).resolve().parents[2]
        / "docs/samples/python/recognizer_config_workflows.py"
    )
    result = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == [
        f"PASS: {step} threshold, reload YAML, detect and reject lookalike"
        for step in ("omit", "override", "clear", "restore")
    ] + [
        "PASS: unknown-key warning, strict rejection, correction and reload",
        "PASS: derive model names, reject ambiguity, rename and reload",
        "PASS: switch provider, YAML and dict APIs with identical detections",
        "PASS: override predefined patterns, preserve checksum, reject invalid edit",
    ]


@pytest.mark.skipif(
    find_spec("langextract") is None, reason="LangExtract SDK not installed"
)
def test_langextract_workflow_checks_configuration_without_a_service():
    script = (
        Path(__file__).resolve().parents[2]
        / "docs/samples/python/recognizer_config_workflows.py"
    )
    result = subprocess.run(
        [sys.executable, str(script), "--langextract"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines()[-1] == (
        "PASS: LangExtract provider-file edit and ignored-key diagnostic, no service call"
    )
