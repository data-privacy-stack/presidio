#!/usr/bin/env python3
"""Build (or serve) the Presidio documentation with Zensical.

Zensical (https://zensical.org) is the successor to Material for MkDocs. It can
read an existing ``mkdocs.yml`` natively, but it does **not** run MkDocs plugins
- it only supports a curated set of plugins that it shims into Python-Markdown
extensions. Presidio's docs nav still includes notebook samples (``*.ipynb``),
so this script pre-converts them to Markdown before invoking Zensical.

Notebook support is accepted on the Zensical backlog but unscheduled:
  - request : https://github.com/zensical/zensical/issues/52
  - backlog : https://github.com/zensical/backlog/issues/9

Until it ships, this script bridges the gap by pre-converting every ``*.ipynb``
referenced in the navigation to Markdown with ``nbconvert``. Zensical then
renders those pages natively, with full theme, navigation, search and table of
contents integration (unlike dumping standalone HTML into the build output).

Steps
-----
1. Load ``mkdocs.yml`` and collect every ``*.ipynb`` referenced in the nav.
2. Mirror ``docs/`` into ``.zensical-build/docs/`` so the real source tree
   stays untouched (Material-compatible, minimal diff, easy to rebase).
3. In the staging copy, convert each notebook to Markdown (images land in a
   sibling ``<name>_files/`` directory that Zensical copies as static assets)
   and rewrite in-repo ``*.ipynb`` links to the converted ``*.md`` pages so
   they navigate instead of downloading the raw notebook.
4. Emit a generated ``zensical.yml`` whose ``docs_dir`` is the staging tree,
   whose nav points at the ``.md`` files, and which no longer enables the
   ``mkdocs-jupyter`` plugin.
5. Run ``zensical build`` (default) or ``zensical serve`` against that config.

Executables are taken from ``PATH`` by default. In a split-virtualenv setup the
following environment variables can override them:

  JUPYTER_BIN          path to the ``jupyter`` entry point (default: ``jupyter``)
  ZENSICAL_BIN         path to the ``zensical`` entry point (default: ``zensical``)
  ZENSICAL_PYTHONPATH  extra PYTHONPATH for the zensical process (e.g. so that
                       the documented Python packages and ``mkdocstrings`` are
                       importable for the API reference)

Usage
-----
  python scripts/zensical_build.py                # build
  python scripts/zensical_build.py serve -a :8001 # serve (extra args passed on)
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MKDOCS_CONFIG = REPO_ROOT / "mkdocs.yml"
GENERATED_CONFIG = REPO_ROOT / "zensical.yml"

# Everything Zensical-specific is generated into this staging tree so the real
# ``docs/`` stays pristine (Material-compatible, minimal diff, easy rebase).
STAGING_DIR = REPO_ROOT / ".zensical-build"
STAGING_DOCS = STAGING_DIR / "docs"
STAGING_DOCS_REL = STAGING_DOCS.relative_to(REPO_ROOT).as_posix()


# --------------------------------------------------------------------------- #
# YAML loading
# --------------------------------------------------------------------------- #
class _TolerantLoader(yaml.SafeLoader):
    """SafeLoader that tolerates MkDocs' ``!!python/name:`` tags.

    We only need to *read* the config to discover notebooks; the generated
    config is produced by string transformation so these tags round-trip
    untouched.
    """


def _ignore_python_name(loader, suffix, node):  # noqa: ANN001, ARG001
    return None


_TolerantLoader.add_multi_constructor(
    "tag:yaml.org,2002:python/name:", _ignore_python_name
)


def _collect_notebooks(nav) -> list[str]:
    """Return every ``*.ipynb`` path referenced in a MkDocs nav structure."""
    found: list[str] = []

    def walk(node) -> None:
        if isinstance(node, str):
            if node.endswith(".ipynb"):
                found.append(node)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)

    walk(nav)
    # De-duplicate while preserving order.
    return list(dict.fromkeys(found))


# --------------------------------------------------------------------------- #
# Staging
# --------------------------------------------------------------------------- #
def _stage_docs(src: Path, dst: Path) -> None:
    """Mirror the real docs tree into the staging dir (source stays untouched)."""
    if shutil.which("rsync"):
        dst.mkdir(parents=True, exist_ok=True)
        subprocess.run(["rsync", "-a", "--delete", f"{src}/", f"{dst}/"], check=True)
    else:
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)


# --------------------------------------------------------------------------- #
# Notebook conversion
# --------------------------------------------------------------------------- #
def _convert_notebooks(notebooks: list[str], docs_dir: Path) -> list[Path]:
    """Convert notebooks to Markdown in place; return generated paths."""
    jupyter = os.environ.get("JUPYTER_BIN", "jupyter")
    generated: list[Path] = []

    for rel in notebooks:
        src = docs_dir / rel
        if not src.exists():
            print(f"  ! skip (missing): {rel}", file=sys.stderr)
            continue

        out_md = src.with_suffix(".md")
        print(f"  - {rel} -> {out_md.relative_to(docs_dir)}")
        subprocess.run(
            [
                jupyter,
                "nbconvert",
                "--to",
                "markdown",
                "--output",
                src.stem,
                "--output-dir",
                str(src.parent),
                str(src),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        generated.append(out_md)

    return generated


# --------------------------------------------------------------------------- #
# Link rewriting
# --------------------------------------------------------------------------- #
# Matches the URL of a Markdown link ``](...ipynb`` or an HTML ``href="...ipynb``.
# The match stops at ``.ipynb`` so any ``#fragment`` is preserved untouched.
_LINK_RE = re.compile(r"""(\]\(|href=["'])([^)"'#?\s]+\.ipynb)""")


def _rewrite_links(docs_dir: Path, notebooks: list[str]) -> None:
    """Point in-repo ``*.ipynb`` links at the converted ``*.md`` pages.

    MkDocs + mkdocs-jupyter rewrote notebook links to the rendered page; under
    Zensical the page is the converted Markdown, so links to a notebook that we
    converted must end in ``.md`` (otherwise the browser downloads the raw
    ``.ipynb``). Only links that resolve to a converted notebook are touched —
    external (GitHub) links and links to non-converted notebooks are left alone.
    """
    converted = {(docs_dir / rel).resolve() for rel in notebooks}
    total = 0

    for md in docs_dir.rglob("*.md"):
        base = md.parent
        text = md.read_text(encoding="utf-8")
        hits = 0

        def repl(match: re.Match) -> str:
            nonlocal hits
            prefix, url = match.group(1), match.group(2)
            if url.startswith(("http://", "https://", "//", "mailto:")):
                return match.group(0)
            target = (base / urllib.parse.unquote(url)).resolve()
            if target in converted:
                hits += 1
                return prefix + url[: -len(".ipynb")] + ".md"
            return match.group(0)

        new = _LINK_RE.sub(repl, text)
        if hits:
            md.write_text(new, encoding="utf-8")
            total += hits

    print(f"  rewrote {total} notebook link(s) to .md")


# --------------------------------------------------------------------------- #
# Generated config
# --------------------------------------------------------------------------- #
def _write_generated_config(raw: str, notebooks: list[str]) -> None:
    """Rewrite nav .ipynb -> .md, drop mkdocs-jupyter, point at the staging docs."""
    text = raw
    for rel in notebooks:
        text = text.replace(rel, rel[: -len(".ipynb")] + ".md")

    # Remove the ``- mkdocs-jupyter:`` plugin entry and its indented children.
    text = re.sub(
        r"[ \t]*-[ \t]*mkdocs-jupyter:[^\n]*\n(?:[ \t]+[^\n]*\n)*",
        "",
        text,
    )

    # Build from the staging copy (converted notebooks + rewritten links).
    if re.search(r"(?m)^docs_dir:.*$", text):
        text = re.sub(r"(?m)^docs_dir:.*$", f"docs_dir: {STAGING_DOCS_REL}", text)
    else:
        text = f"docs_dir: {STAGING_DOCS_REL}\n" + text

    banner = (
        "# AUTOGENERATED by scripts/zensical_build.py - DO NOT EDIT.\n"
        "# Source of truth is mkdocs.yml. Notebook nav entries have been\n"
        "# converted to Markdown and the mkdocs-jupyter plugin removed,\n"
        "# because Zensical does not run MkDocs plugins (backlog: "
        "zensical/backlog#9).\n"
        f"# docs_dir points at the generated staging tree ({STAGING_DOCS_REL}).\n\n"
    )
    GENERATED_CONFIG.write_text(banner + text, encoding="utf-8")
    print(f"  wrote {GENERATED_CONFIG.relative_to(REPO_ROOT)}")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv: list[str]) -> int:
    """Stage docs, convert notebooks, write zensical.yml, and build or serve."""
    command = argv[0] if argv else "build"
    passthrough = argv[1:]
    if command not in {"build", "serve"}:
        # Treat unknown first arg as a passthrough flag for `build`.
        command, passthrough = "build", argv

    raw = MKDOCS_CONFIG.read_text(encoding="utf-8")
    config = yaml.load(raw, Loader=_TolerantLoader)
    docs_dir = REPO_ROOT / config.get("docs_dir", "docs")

    notebooks = _collect_notebooks(config.get("nav", []))

    print(f"Staging docs -> {STAGING_DOCS_REL}")
    _stage_docs(docs_dir, STAGING_DOCS)

    print(f"Found {len(notebooks)} notebook(s) in nav.")
    _convert_notebooks(notebooks, STAGING_DOCS)

    print("Rewriting notebook links...")
    _rewrite_links(STAGING_DOCS, notebooks)

    print("Generating Zensical config...")
    _write_generated_config(raw, notebooks)

    zensical = os.environ.get("ZENSICAL_BIN", "zensical")
    env = os.environ.copy()
    extra_pp = os.environ.get("ZENSICAL_PYTHONPATH")
    if extra_pp:
        env["PYTHONPATH"] = os.pathsep.join(
            p for p in (extra_pp, env.get("PYTHONPATH", "")) if p
        )

    cmd = [zensical, command, "-f", str(GENERATED_CONFIG), *passthrough]
    print(f"Running: {' '.join(cmd)}")

    # ``serve`` is interactive/long-running, so run it once. ``build`` can be
    # killed by the OS (e.g. exit code 247 == 256-9, SIGKILL) when memory spikes
    # while griffe imports the documented ML packages; that crash is transient,
    # so retry a couple of times before giving up.
    if command != "build":
        return subprocess.run(cmd, env=env, check=False).returncode

    attempts = max(1, int(os.environ.get("ZENSICAL_BUILD_RETRIES", "3")))
    rc = 0
    for attempt in range(1, attempts + 1):
        rc = subprocess.run(cmd, env=env, check=False).returncode
        if rc == 0:
            return 0
        print(f"  zensical build failed (exit {rc}), attempt {attempt}/{attempts}")
    print(f"  zensical build still failing after {attempts} attempt(s)")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
