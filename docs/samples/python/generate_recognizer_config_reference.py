"""Generate or check the constructor-derived recognizer configuration reference."""

import argparse
from pathlib import Path

from presidio_analyzer.input_validation import render_recognizer_config_reference


def main() -> None:
    """Update generated documentation, or fail if it is stale."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if docs are stale")
    args = parser.parse_args()
    path = (
        Path(__file__).resolve().parents[2] / "analyzer/recognizer_config_reference.md"
    )
    expected = render_recognizer_config_reference()
    if args.check:
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            raise SystemExit(
                "Recognizer config reference is stale; rerun the generator."
            )
    else:
        path.write_text(expected, encoding="utf-8")


if __name__ == "__main__":
    main()
