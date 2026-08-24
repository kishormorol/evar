from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path


class raises:
    def __init__(self, expected_exception: type[BaseException]) -> None:
        self.expected_exception = expected_exception

    def __enter__(self) -> None:
        return None

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object,
    ) -> bool:
        del exc, traceback
        if exc_type is None:
            raise AssertionError(f"Expected {self.expected_exception.__name__} to be raised.")
        return issubclass(exc_type, self.expected_exception)


def main() -> int:
    args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
    if not args:
        print("No test file supplied.")
        return 2

    failures = 0
    for arg in args:
        path = Path(arg)
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            print(f"Could not load {path}.")
            return 2
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name, value in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            try:
                value()
            except Exception as exc:
                failures += 1
                print(f"{name} FAILED: {exc}")

    if failures:
        print(f"{failures} failed")
        return 1
    print("EVAR_WITNESS_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
