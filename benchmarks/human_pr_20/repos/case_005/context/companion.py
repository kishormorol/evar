Original path: testing/test_pathlib.py
Snapshot commit: e25d981ec0ca25a6bda1f5513d6df61e5240e69e
Original lines: 14-62

import sys
from textwrap import dedent
from types import ModuleType
from typing import Any
import unittest.mock

from _pytest.config import ExitCode
from _pytest.monkeypatch import MonkeyPatch
from _pytest.pathlib import _import_module_using_spec
from _pytest.pathlib import bestrelpath
from _pytest.pathlib import commonpath
from _pytest.pathlib import compute_module_name
from _pytest.pathlib import CouldNotResolvePathError
from _pytest.pathlib import ensure_deletable
from _pytest.pathlib import fnmatch_ex
from _pytest.pathlib import get_extended_length_path_str
from _pytest.pathlib import get_lock_path
from _pytest.pathlib import import_path
from _pytest.pathlib import ImportMode
from _pytest.pathlib import ImportPathMismatchError
from _pytest.pathlib import insert_missing_modules
from _pytest.pathlib import is_importable
from _pytest.pathlib import maybe_delete_a_numbered_dir
from _pytest.pathlib import module_name_from_path
from _pytest.pathlib import resolve_package_path
from _pytest.pathlib import resolve_pkg_root_and_module_name
from _pytest.pathlib import safe_exists
from _pytest.pathlib import samefile_nofollow
from _pytest.pathlib import scandir
from _pytest.pathlib import spec_matches_module_path
from _pytest.pathlib import symlink_or_skip
from _pytest.pathlib import visit
from _pytest.pytester import Pytester
from _pytest.pytester import RunResult
from _pytest.tmpdir import TempPathFactory
import pytest


@pytest.fixture(autouse=True)
def autouse_pytester(pytester: Pytester) -> None:
    """
    Fixture to make pytester() being autouse for all tests in this module.

    pytester makes sure to restore sys.path to its previous state, and many tests in this module
    import modules and change sys.path because of that, so common module names such as "test" or "test.conftest"
    end up leaking to tests in other modules.

    Note: we might consider extracting the sys.path restoration aspect into its own fixture, and apply it
    to the entire test suite always.
