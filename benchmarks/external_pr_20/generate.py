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
        _case(1, "zipp", "84be2a5570778549503492d094f40a7203197bb2", _zipp_init_files(),
              "Review zipp Path.iterdir behavior after commit 84be2a5.",
              "Path.iterdir raises NotADirectoryError when called on a file.", "SUPPORTED",
              "The commit changes Path.iterdir to raise NotADirectoryError when not self.is_dir().",
              "behavior_inversion"),
        _case(2, "zipp", "84be2a5570778549503492d094f40a7203197bb2", _zipp_init_files(),
              "Review zipp Path.iterdir behavior after commit 84be2a5.",
              "Path.iterdir still raises ValueError when called on a file.", "UNSUPPORTED",
              "The updated implementation raises NotADirectoryError, not ValueError.",
              "behavior_inversion"),
        _case(3, "zipp", "d860de467a5887a6f09e5b66e4ef51f2e9c516fa", {"zipp/glob.py": "zipp/glob.py"},
              "Review zipp glob regex terminator after commit d860de4.",
              "Translator.extend appends \\z to the generated regex.", "SUPPORTED",
              "Translator.extend returns rf'(?s:{pattern})\\z'.", "incorrect_call_relationship"),
        _case(4, "zipp", "d860de467a5887a6f09e5b66e4ef51f2e9c516fa", {"zipp/glob.py": "zipp/glob.py"},
              "Review zipp glob regex terminator after commit d860de4.",
              "Translator.extend still appends \\Z to the generated regex.", "UNSUPPORTED",
              "The updated implementation and docstring use \\z, not \\Z.", "incorrect_call_relationship"),
        _case(5, "markupsafe", "0b6bee071fbd8d3171fb1ac4fb669baace808438", {"src/markupsafe/__init__.py": "markupsafe/__init__.py"},
              "Review MarkupSafe striptags whitespace handling after commit 0b6bee0.",
              "Markup.striptags collapses whitespace after removing comments and tags.", "SUPPORTED",
              "The commit moves value = ' '.join(value.split()) to after the comment and tag removal loops.",
              "stale_evidence"),
        _case(6, "markupsafe", "0b6bee071fbd8d3171fb1ac4fb669baace808438", {"src/markupsafe/__init__.py": "markupsafe/__init__.py"},
              "Review MarkupSafe striptags whitespace handling after commit 0b6bee0.",
              "Markup.striptags collapses whitespace before removing comments and tags.", "UNSUPPORTED",
              "The updated implementation converts to str first, removes comments and tags, then collapses whitespace.",
              "stale_evidence"),
        _case(7, "zipp", "3503c8b2e47f28eb49aad9ddb4f5c002146404ad", _zipp_init_files(),
              "Review zipp Path._base after commit 3503c8b.",
              "Path._base uses pathlib.PurePath for the zipfile filename when self.at is empty.", "SUPPORTED",
              "The updated _base returns pathlib.PurePath(self.root.filename) in the else branch.",
              "causal_mislocalization"),
        _case(8, "zipp", "3503c8b2e47f28eb49aad9ddb4f5c002146404ad", _zipp_init_files(),
              "Review zipp Path._base after commit 3503c8b.",
              "Path._base always wraps self.root.filename with pathlib.PurePosixPath.", "UNSUPPORTED",
              "The updated _base only uses PurePosixPath for self.at; otherwise it uses PurePath.",
              "causal_mislocalization"),
        _case(9, "zipp", "f89b93f0370dd85d23d243e25dfc1f99f4d8de48", _zipp_init_files(),
              "Review zipp malformed path ancestry after commit f89b93f.",
              "_ancestry treats multiple separators like a single path separator.", "SUPPORTED",
              "The updated docstring states multiple separators are treated like a single and the loop stops on path.endswith(posixpath.sep).",
              "missing_guard"),
        _case(10, "zipp", "f89b93f0370dd85d23d243e25dfc1f99f4d8de48", _zipp_init_files(),
              "Review zipp malformed path ancestry after commit f89b93f.",
              "_ancestry still loops until path equals exactly posixpath.sep.", "UNSUPPORTED",
              "The updated loop condition is while path and not path.endswith(posixpath.sep).",
              "missing_guard"),
        _case(11, "zipp", "71ddd8d4f4ab200af870f0060d9ee8c6b7056681", _zipp_init_files(),
              "Review zipp Path.open missing-file check after commit 71ddd8d.",
              "Path.open checks zip_mode == 'r' before calling self.exists().", "SUPPORTED",
              "The updated condition is if zip_mode == 'r' and not self.exists().", "missing_guard"),
        _case(12, "zipp", "71ddd8d4f4ab200af870f0060d9ee8c6b7056681", _zipp_init_files(),
              "Review zipp Path.open missing-file check after commit 71ddd8d.",
              "Path.open calls self.exists() before checking whether the zip mode is read mode.", "UNSUPPORTED",
              "The updated condition short-circuits on zip_mode == 'r' before self.exists().", "missing_guard"),
        _case(13, "zipp", "5d89a1cf540894ef28c0b6485daf01c860bd59d0", _zipp_init_files(),
              "Review zipp directory glob matching after commit 5d89a1c.",
              "Translator.translate wraps translate_core with match_dirs.", "SUPPORTED",
              "translate returns self.extend(self.match_dirs(self.translate_core(pattern))).",
              "incorrect_call_relationship"),
        _case(14, "zipp", "5d89a1cf540894ef28c0b6485daf01c860bd59d0", _zipp_init_files(),
              "Review zipp directory glob matching after commit 5d89a1c.",
              "Translator.translate returns self.extend(self.translate_core(pattern)) without match_dirs.", "UNSUPPORTED",
              "The updated translate call includes match_dirs around translate_core.",
              "incorrect_call_relationship"),
        _case(15, "zipp", "dc5fe8f4dd31e551f9bf76b5403e64f06f72a0c7", _zipp_init_files(),
              "Review zipp Path.is_symlink after commit dc5fe8f.",
              "Path.is_symlink uses stat.S_ISLNK on mode derived from external_attr.", "SUPPORTED",
              "is_symlink reads info.external_attr >> 16 and returns stat.S_ISLNK(mode).",
              "behavior_inversion"),
        _case(16, "zipp", "dc5fe8f4dd31e551f9bf76b5403e64f06f72a0c7", _zipp_init_files(),
              "Review zipp Path.is_symlink after commit dc5fe8f.",
              "Path.is_symlink always returns False.", "UNSUPPORTED",
              "The updated implementation computes mode and calls stat.S_ISLNK(mode).",
              "behavior_inversion"),
        _case(17, "markupsafe", "e49d257126d09937b1bf5e2b2173238df729fb13", {"src/markupsafe/__init__.py": "markupsafe/__init__.py"},
              "Review MarkupSafe striptags regex flags after commit e49d257.",
              "MarkupSafe compiles the strip-tags regexes with re.DOTALL.", "SUPPORTED",
              "_strip_comments_re and _strip_tags_re are compiled with re.DOTALL.",
              "stale_evidence"),
        _case(18, "markupsafe", "e49d257126d09937b1bf5e2b2173238df729fb13", {"src/markupsafe/__init__.py": "markupsafe/__init__.py"},
              "Review MarkupSafe striptags regex flags after commit e49d257.",
              "MarkupSafe strip-tags regexes do not match newlines.", "UNSUPPORTED",
              "The regexes use re.DOTALL so dot matches newlines.",
              "stale_evidence"),
        _case(19, "markupsafe", "3d809aed7b7b6af5c371bab68666857087335af9", {"src/markupsafe/__init__.py": "markupsafe/__init__.py"},
              "Review MarkupSafe percent-format single placeholder behavior after commit 3d809ae.",
              "Markup.__mod__ wraps a single non-mapping argument in a one-element tuple.", "SUPPORTED",
              "The else branch assigns arg = (_MarkupEscapeHelper(arg, self.escape),).",
              "causal_mislocalization"),
        _case(20, "markupsafe", "3d809aed7b7b6af5c371bab68666857087335af9", {"src/markupsafe/__init__.py": "markupsafe/__init__.py"},
              "Review MarkupSafe percent-format single placeholder behavior after commit 3d809ae.",
              "Markup.__mod__ passes a single non-mapping argument directly to _MarkupEscapeHelper without tuple wrapping.", "UNSUPPORTED",
              "The updated else branch wraps the helper in a one-element tuple.",
              "causal_mislocalization"),
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
    repo_name: str,
    commit: str,
    files: dict[str, str],
    task: str,
    claim: str,
    ground_truth: str,
    ground_truth_evidence: str,
    claim_family: str,
) -> dict[str, object]:
    case_id = f"externalpr20_{number:03d}_{claim_family}_{ground_truth.lower()}"
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


def _zipp_init_files() -> dict[str, str]:
    return {
        "zipp/__init__.py": "zipp/__init__.py",
        "zipp/_functools.py": "zipp/_functools.py",
        "zipp/glob.py": "zipp/glob.py",
        "zipp/compat/py310.py": "zipp/compat/py310.py",
    }


def _write_git_file(repo_name: str, commit: str, source: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            ["git", "-C", str(SOURCES[repo_name]), "show", f"{commit}:{source}"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        if source in {"zipp/_functools.py", "zipp/glob.py", "zipp/compat/py310.py"}:
            return
        raise
    target.write_text(completed.stdout, encoding="utf-8")


if __name__ == "__main__":
    main()
