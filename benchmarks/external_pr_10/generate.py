from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
SOURCE_CACHE = PROJECT / "benchmarks" / "external_10" / "sources"
REPOS = ROOT / "repos"
CASES = ROOT / "cases.jsonl"


SOURCES = {
    "markupsafe": SOURCE_CACHE / "markupsafe",
    "zipp": SOURCE_CACHE / "zipp",
}


def main() -> None:
    _require_sources()
    REPOS.mkdir(parents=True, exist_ok=True)
    rows = [
        _case(
            1,
            repo_name="zipp",
            commit="84be2a5570778549503492d094f40a7203197bb2",
            files={"zipp/__init__.py": "zipp/__init__.py"},
            task="Review zipp Path.iterdir behavior after commit 84be2a5.",
            claim="Path.iterdir raises NotADirectoryError when called on a file.",
            ground_truth="SUPPORTED",
            ground_truth_evidence="The commit changes Path.iterdir to raise NotADirectoryError when not self.is_dir().",
            claim_family="behavior_inversion",
        ),
        _case(
            2,
            repo_name="zipp",
            commit="84be2a5570778549503492d094f40a7203197bb2",
            files={"zipp/__init__.py": "zipp/__init__.py"},
            task="Review zipp Path.iterdir behavior after commit 84be2a5.",
            claim="Path.iterdir still raises ValueError when called on a file.",
            ground_truth="UNSUPPORTED",
            ground_truth_evidence="The updated implementation raises NotADirectoryError, not ValueError.",
            claim_family="behavior_inversion",
        ),
        _case(
            3,
            repo_name="zipp",
            commit="d860de467a5887a6f09e5b66e4ef51f2e9c516fa",
            files={"zipp/glob.py": "zipp/glob.py"},
            task="Review zipp glob regex terminator after commit d860de4.",
            claim="Translator.extend appends \\z to the generated regex.",
            ground_truth="SUPPORTED",
            ground_truth_evidence="Translator.extend returns rf'(?s:{pattern})\\z'.",
            claim_family="incorrect_call_relationship",
        ),
        _case(
            4,
            repo_name="zipp",
            commit="d860de467a5887a6f09e5b66e4ef51f2e9c516fa",
            files={"zipp/glob.py": "zipp/glob.py"},
            task="Review zipp glob regex terminator after commit d860de4.",
            claim="Translator.extend still appends \\Z to the generated regex.",
            ground_truth="UNSUPPORTED",
            ground_truth_evidence="The updated implementation and docstring use \\z, not \\Z.",
            claim_family="incorrect_call_relationship",
        ),
        _case(
            5,
            repo_name="markupsafe",
            commit="0b6bee071fbd8d3171fb1ac4fb669baace808438",
            files={"src/markupsafe/__init__.py": "markupsafe/__init__.py"},
            task="Review MarkupSafe striptags whitespace handling after commit 0b6bee0.",
            claim="Markup.striptags collapses whitespace after removing comments and tags.",
            ground_truth="SUPPORTED",
            ground_truth_evidence="The commit moves value = ' '.join(value.split()) to after the comment and tag removal loops.",
            claim_family="stale_evidence",
        ),
        _case(
            6,
            repo_name="markupsafe",
            commit="0b6bee071fbd8d3171fb1ac4fb669baace808438",
            files={"src/markupsafe/__init__.py": "markupsafe/__init__.py"},
            task="Review MarkupSafe striptags whitespace handling after commit 0b6bee0.",
            claim="Markup.striptags collapses whitespace before removing comments and tags.",
            ground_truth="UNSUPPORTED",
            ground_truth_evidence="The updated implementation converts to str first, removes comments and tags, then collapses whitespace.",
            claim_family="stale_evidence",
        ),
        _case(
            7,
            repo_name="zipp",
            commit="3503c8b2e47f28eb49aad9ddb4f5c002146404ad",
            files={"zipp/__init__.py": "zipp/__init__.py"},
            task="Review zipp Path._base after commit 3503c8b.",
            claim="Path._base uses pathlib.PurePath for the zipfile filename when self.at is empty.",
            ground_truth="SUPPORTED",
            ground_truth_evidence="The updated _base returns pathlib.PurePath(self.root.filename) in the else branch.",
            claim_family="causal_mislocalization",
        ),
        _case(
            8,
            repo_name="zipp",
            commit="3503c8b2e47f28eb49aad9ddb4f5c002146404ad",
            files={"zipp/__init__.py": "zipp/__init__.py"},
            task="Review zipp Path._base after commit 3503c8b.",
            claim="Path._base always wraps self.root.filename with pathlib.PurePosixPath.",
            ground_truth="UNSUPPORTED",
            ground_truth_evidence="The updated _base only uses PurePosixPath for self.at; otherwise it uses PurePath.",
            claim_family="causal_mislocalization",
        ),
        _case(
            9,
            repo_name="zipp",
            commit="f89b93f0370dd85d23d243e25dfc1f99f4d8de48",
            files={"zipp/__init__.py": "zipp/__init__.py"},
            task="Review zipp malformed path ancestry after commit f89b93f.",
            claim="_ancestry treats multiple separators like a single path separator.",
            ground_truth="SUPPORTED",
            ground_truth_evidence="The updated docstring states multiple separators are treated like a single and the loop stops on path.endswith(posixpath.sep).",
            claim_family="missing_guard",
        ),
        _case(
            10,
            repo_name="zipp",
            commit="f89b93f0370dd85d23d243e25dfc1f99f4d8de48",
            files={"zipp/__init__.py": "zipp/__init__.py"},
            task="Review zipp malformed path ancestry after commit f89b93f.",
            claim="_ancestry still loops until path equals exactly posixpath.sep.",
            ground_truth="UNSUPPORTED",
            ground_truth_evidence="The updated loop condition is while path and not path.endswith(posixpath.sep).",
            claim_family="missing_guard",
        ),
    ]
    with CASES.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _require_sources() -> None:
    missing = [str(path) for path in SOURCES.values() if not (path / ".git").exists()]
    if missing:
        raise FileNotFoundError(
            "Missing external source git repositories. Clone sources with: "
            "gh repo clone pallets/markupsafe benchmarks/external_10/sources/markupsafe; "
            "gh repo clone jaraco/zipp benchmarks/external_10/sources/zipp. "
            f"Missing: {missing}"
        )


def _case(
    number: int,
    *,
    repo_name: str,
    commit: str,
    files: dict[str, str],
    task: str,
    claim: str,
    ground_truth: str,
    ground_truth_evidence: str,
    claim_family: str,
) -> dict[str, object]:
    case_id = f"externalpr10_{number:03d}_{claim_family}_{ground_truth.lower()}"
    case_repo = REPOS / f"case_{number:03d}"
    case_repo.mkdir(parents=True, exist_ok=True)
    for source, target in files.items():
        _write_git_file(repo_name, commit, source, case_repo / target)
    return {
        "case_id": case_id,
        "repo_path": str(case_repo.relative_to(PROJECT)).replace("\\", "/"),
        "task_description": task,
        "claim": claim,
        "ground_truth": ground_truth,
        "ground_truth_evidence": ground_truth_evidence,
        "validation_command": ["python", "-m", "unittest", "discover"],
        "claim_family": claim_family,
        "source_repository": repo_name,
        "source_commit": commit,
    }


def _write_git_file(repo_name: str, commit: str, source: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["git", "-C", str(SOURCES[repo_name]), "show", f"{commit}:{source}"],
        check=True,
        capture_output=True,
        text=True,
    )
    target.write_text(completed.stdout, encoding="utf-8")


if __name__ == "__main__":
    main()
