"""Utility script to build a zip archive of the project.

This script excludes cache directories and compiled Python files.  Run
`python scripts/make_zip.py` from the project root to produce
`paulownia_dash.zip` in the current working directory.
"""

import os
import zipfile


def should_include(path: str) -> bool:
    # exclude pycache and test caches
    exclude_dirs = {"__pycache__", ".pytest_cache", "build", "dist"}
    parts = path.split(os.sep)
    return not any(part in exclude_dirs for part in parts)


def build_zip(root: str = ".", zip_name: str = "paulownia_dash.zip") -> None:
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(root):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                relpath = os.path.relpath(filepath, root)
                if should_include(relpath):
                    zf.write(filepath, relpath)


if __name__ == "__main__":
    build_zip()