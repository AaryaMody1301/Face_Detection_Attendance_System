"""Fail a release when the Git tag and package version disagree."""
from __future__ import annotations

import argparse

from src.core.version import get_version


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True, help="Release tag such as v1.5.0")
    args = parser.parse_args()

    tag_version = args.tag.removeprefix("v")
    package_version = get_version()
    if tag_version != package_version:
        print(f"Release version mismatch: tag={tag_version}, package={package_version}")
        return 1
    print(f"Release version verified: {package_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
