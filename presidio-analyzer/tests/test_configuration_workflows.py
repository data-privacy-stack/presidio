"""Keep the executable, model-free user workflow sample covered by CI."""

import subprocess
import sys
from pathlib import Path


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
    ]
