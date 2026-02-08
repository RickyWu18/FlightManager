"""Version information for the Flight Manager application."""

import subprocess
import sys

# Default version used if git is unavailable or fails
DEFAULT_VERSION = "1.0.1"


def get_current_version():
    """
    Determine the version based on git tags.
    If frozen (exe), returns DEFAULT_VERSION.
    If ahead of a tag OR dirty, returns tag with '-dev' appended.
    """
    if getattr(sys, "frozen", False):
        return DEFAULT_VERSION

    try:
        # Get the closest tag (e.g. v1.0.1)
        tag = (
            subprocess.check_output(
                ["git", "describe", "--tags", "--abbrev=0"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )

        version_str = tag.lstrip("v")

        # Check if we are exactly on a tag (commit-wise)
        is_exact_commit = False
        try:
            subprocess.check_call(
                ["git", "describe", "--tags", "--exact-match"],
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )
            is_exact_commit = True
        except subprocess.CalledProcessError:
            is_exact_commit = False

        # Check for uncommitted changes (dirty)
        is_dirty = False
        try:
            subprocess.check_call(
                ["git", "diff", "--quiet"], stderr=subprocess.DEVNULL
            )
            subprocess.check_call(
                ["git", "diff", "--cached", "--quiet"],
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            is_dirty = True

        if not is_exact_commit or is_dirty:
            return f"{version_str}-dev"

        return version_str

    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        # Git failed or not found (e.g., no tags, no .git directory)
        return f"{DEFAULT_VERSION}-dev"


__version__ = get_current_version()
APP_NAME = "Flight Manager Logger"
AUTHOR = "PoHsun.Wu"
COPYRIGHT = "Copyright (c) 2026"

