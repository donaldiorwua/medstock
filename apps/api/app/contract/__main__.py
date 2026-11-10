"""Command line for the contract files.

python -m app.contract export   regenerate docs/contract/*.json from the code
python -m app.contract check    fail (exit 1) if the committed files are out of date
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from app.contract.build import CONTRACT_DIR, check, export


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.contract")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("export", "regenerate the contract files from the code"),
        ("check", "fail if the committed contract files differ from the code"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--dir", type=Path, default=CONTRACT_DIR, help="contract directory")
    args = parser.parse_args(argv)

    if args.command == "export":
        for path in export(args.dir):
            print(f"wrote {path}")
        return 0

    problems = check(args.dir)
    if problems:
        print("\n\n".join(problems), file=sys.stderr)
        print(
            "\nThe contract files are out of date. If the change is intended, run:\n"
            "  python -m app.contract export\n"
            "and commit the result (breaking changes need the 'breaking-contract' label).",
            file=sys.stderr,
        )
        return 1
    print("Contract files are up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
