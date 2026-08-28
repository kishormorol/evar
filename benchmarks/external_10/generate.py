from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
SOURCES = ROOT / "sources"
REPOS = ROOT / "repos"
CASES = ROOT / "cases.jsonl"


SOURCE_FILES = {
    "markupsafe_native": SOURCES / "markupsafe" / "src" / "markupsafe" / "_native.py",
    "zipp_functools": SOURCES / "zipp" / "zipp" / "_functools.py",
    "zipp_glob": SOURCES / "zipp" / "zipp" / "glob.py",
    "zipp_py313": SOURCES / "zipp" / "zipp" / "compat" / "py313.py",
}


def main() -> None:
    _require_sources()
    REPOS.mkdir(parents=True, exist_ok=True)
    rows = [
        _case(
            1,
            source_key="markupsafe_native",
            target="markupsafe/_native.py",
            task="Review MarkupSafe native escaping for ampersands.",
            claim="_escape_inner replaces ampersands with &amp;.",
            ground_truth="SUPPORTED",
            ground_truth_evidence="_escape_inner calls s.replace('&', '&amp;').",
            claim_family="behavior_inversion",
        ),
        _case(
            2,
            source_key="markupsafe_native",
            target="markupsafe/_native.py",
            task="Review MarkupSafe native escaping for single quotes.",
            claim="_escape_inner leaves single quotes unchanged.",
            ground_truth="UNSUPPORTED",
            ground_truth_evidence="_escape_inner replaces single quotes with &#39;.",
            claim_family="behavior_inversion",
        ),
        _case(
            3,
            source_key="markupsafe_native",
            target="markupsafe/_native.py",
            task="Review MarkupSafe native escaping for double quotes.",
            claim="_escape_inner replaces double quotes with &#34;.",
            ground_truth="SUPPORTED",
            ground_truth_evidence="_escape_inner calls .replace('\"', '&#34;').",
            claim_family="incorrect_call_relationship",
        ),
        _case(
            4,
            source_key="markupsafe_native",
            target="markupsafe/_native.py",
            task="Review MarkupSafe native escaping for spaces.",
            claim="_escape_inner escapes spaces to &nbsp;.",
            ground_truth="UNSUPPORTED",
            ground_truth_evidence="_escape_inner has no replacement for spaces.",
            claim_family="incorrect_call_relationship",
        ),
        _case(
            5,
            source_key="zipp_functools",
            target="zipp/_functools.py",
            task="Review zipp none_as handling for None.",
            claim="none_as(None, replacement) returns replacement.",
            ground_truth="SUPPORTED",
            ground_truth_evidence="none_as returns replacement if value is None.",
            claim_family="missing_guard",
        ),
        _case(
            6,
            source_key="zipp_functools",
            target="zipp/_functools.py",
            task="Review zipp none_as handling for falsey values.",
            claim="none_as replaces every falsey value with replacement.",
            ground_truth="UNSUPPORTED",
            ground_truth_evidence="none_as checks value is None, not general truthiness.",
            claim_family="missing_guard",
        ),
        _case(
            7,
            source_key="zipp_functools",
            target="zipp/_functools.py",
            task="Review zipp saved method argument storage.",
            claim="save_method_args stores args and kwargs on an attribute named with _saved_ plus the method name.",
            ground_truth="SUPPORTED",
            ground_truth_evidence="wrapper builds attr_name = '_saved_' + method.__name__ and calls setattr.",
            claim_family="stale_evidence",
        ),
        _case(
            8,
            source_key="zipp_functools",
            target="zipp/_functools.py",
            task="Review zipp saved method argument storage location.",
            claim="save_method_args stores saved arguments in a module-level global dictionary.",
            ground_truth="UNSUPPORTED",
            ground_truth_evidence="save_method_args stores the namedtuple on self with setattr.",
            claim_family="stale_evidence",
        ),
        _case(
            9,
            source_key="zipp_glob",
            target="zipp/glob.py",
            extra_files=[("zipp_py313", "zipp/compat/py313.py")],
            task="Review zipp recursive glob validation.",
            claim="Translator.restrict_rglob raises ValueError when ** appears inside a larger path segment.",
            ground_truth="SUPPORTED",
            ground_truth_evidence="restrict_rglob raises ValueError if a segment contains ** and is not exactly **.",
            claim_family="causal_mislocalization",
        ),
        _case(
            10,
            source_key="zipp_glob",
            target="zipp/glob.py",
            extra_files=[("zipp_py313", "zipp/compat/py313.py")],
            task="Review zipp directory glob matching.",
            claim="Translator.match_dirs requires directory names to end with a slash.",
            ground_truth="UNSUPPORTED",
            ground_truth_evidence="match_dirs appends [/]? so the trailing slash is optional.",
            claim_family="causal_mislocalization",
        ),
    ]
    with CASES.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _require_sources() -> None:
    missing = [str(path) for path in SOURCE_FILES.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing external source files. Clone sources first, for example: "
            "gh repo clone pallets/markupsafe benchmarks/external_10/sources/markupsafe; "
            "gh repo clone jaraco/zipp benchmarks/external_10/sources/zipp. "
            f"Missing: {missing}"
        )


def _case(
    number: int,
    *,
    source_key: str,
    target: str,
    task: str,
    claim: str,
    ground_truth: str,
    ground_truth_evidence: str,
    claim_family: str,
    extra_files: list[tuple[str, str]] | None = None,
) -> dict[str, object]:
    case_id = f"external10_{number:03d}_{claim_family}_{ground_truth.lower()}"
    repo = REPOS / f"case_{number:03d}"
    repo.mkdir(parents=True, exist_ok=True)
    _copy(source_key, repo / target)
    for extra_source_key, extra_target in extra_files or []:
        _copy(extra_source_key, repo / extra_target)
    return {
        "case_id": case_id,
        "repo_path": str(repo.relative_to(PROJECT)).replace("\\", "/"),
        "task_description": task,
        "claim": claim,
        "ground_truth": ground_truth,
        "ground_truth_evidence": ground_truth_evidence,
        "validation_command": ["python", "-m", "unittest", "discover"],
        "claim_family": claim_family,
    }


def _copy(source_key: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE_FILES[source_key], target)


if __name__ == "__main__":
    main()
