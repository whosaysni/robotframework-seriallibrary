"""Generates docs/SerialLibrary.html, or checks that it is up to date.

Libdoc output depends on the machine it is generated on: it embeds absolute
source paths, the generation time and the Python version. This script makes
source paths relative to the repository and, with ``--check``, reuses the
generation time of the existing file and ignores the Python version, so the
check only fails when the documentation itself changed.

    python tools/libdoc.py               # regenerate the documentation
    python tools/libdoc.py --check       # fail if it is out of date
    python tools/libdoc.py --rf-version  # Robot Framework version it was generated with

The output also depends on the Robot Framework version, so ``--check`` must
run with the version given by ``--rf-version``.
"""

import argparse
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
OUTPUT = ROOT / "docs" / "SerialLibrary.html"
GENERATOR = re.compile(r'<meta content="Robot Framework (\S+)[^"]*" name="Generator">')
GENERATED = re.compile(r'"generated": "([^"]+)"')


def generate(output: Path) -> None:
    sys.path.insert(0, str(SRC))
    from robot.libdocpkg import LibraryDocumentation

    doc = LibraryDocumentation("SerialLibrary")
    for item in [doc, *doc.inits, *doc.keywords]:
        if item.source:
            item.source = Path(item.source).relative_to(ROOT).as_posix()
    # The libdoc command line does this before writing HTML; without it the
    # documentation is shown as raw Robot Framework markup.
    doc.convert_docs_to_html()
    doc.save(str(output), "HTML")


def rf_version(html: str) -> str:
    match = GENERATOR.search(html)
    if not match:
        raise SystemExit(f"Cannot find the Robot Framework version in {OUTPUT}.")
    return match.group(1)


def check() -> int:
    from robot.version import VERSION

    current = OUTPUT.read_text(encoding="utf-8")
    expected_version = rf_version(current)
    if VERSION != expected_version:
        print(
            f"{OUTPUT.name} was generated with Robot Framework {expected_version} but {VERSION} is installed. "
            f"Install robotframework=={expected_version} to check it, or regenerate it."
        )
        return 1
    generated = GENERATED.search(current)
    if generated:
        os.environ["SOURCE_DATE_EPOCH"] = str(int(datetime.fromisoformat(generated.group(1)).timestamp()))
    with tempfile.TemporaryDirectory() as tmp:
        fresh_path = Path(tmp) / OUTPUT.name
        generate(fresh_path)
        fresh = fresh_path.read_text(encoding="utf-8")
    if GENERATOR.sub("", current) != GENERATOR.sub("", fresh):
        print(f"{OUTPUT.relative_to(ROOT)} is out of date. Run 'python tools/libdoc.py' and commit the result.")
        return 1
    print(f"{OUTPUT.relative_to(ROOT)} is up to date.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="fail if the documentation is out of date")
    group.add_argument("--rf-version", action="store_true", help="print the Robot Framework version used")
    args = parser.parse_args()
    if args.rf_version:
        print(rf_version(OUTPUT.read_text(encoding="utf-8")))
        return 0
    if args.check:
        return check()
    generate(OUTPUT)
    print(OUTPUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
