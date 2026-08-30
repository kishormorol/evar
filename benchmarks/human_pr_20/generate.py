from __future__ import annotations

import difflib
import json
import os
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_DIR = Path(__file__).resolve().parent
REPOS_DIR = BENCHMARK_DIR / "repos"
CASES_PATH = BENCHMARK_DIR / "cases.jsonl"


@dataclass(frozen=True)
class ReviewSpec:
    owner: str
    repo: str
    pull_number: int
    comment_id: int
    review_commit: str
    merge_commit: str
    claim: str
    claim_family: str


SPECS = (
    ReviewSpec(
        "psf",
        "black",
        5272,
        3678519973,
        "7e2e327d67ceba006e2b7b2cf62373441f8ab8e4",
        "006b2a74d4deac01fa16e85ccc9f5810b53a7391",
        "The CHANGES entry for pull request 5272 includes internal hug_power_op and cloned-leaf details instead of a concise user-facing summary.",
        "causal_mislocalization",
    ),
    ReviewSpec(
        "psf",
        "black",
        5300,
        3813438763,
        "6ca34c38c7706bf74bf408bb8ba12f086dc1fe45",
        "5ee554164c10218e4d176d045ef235e74173a12d",
        "The CHANGES entry for pull request 5300 includes internal prefix and verbatim-block details instead of a concise user-facing summary.",
        "causal_mislocalization",
    ),
    ReviewSpec(
        "pytest-dev",
        "pytest",
        14865,
        3774173657,
        "e25d981ec0ca25a6bda1f5513d6df61e5240e69e",
        "d6f66d42df86624ed128b84ce57df3d173fe1b95",
        "src/_pytest/pathlib.py puts a samefile_nofollow implementation detail in the docstring instead of a code comment.",
        "causal_mislocalization",
    ),
    ReviewSpec(
        "pytest-dev",
        "pytest",
        14865,
        3789351958,
        "e25d981ec0ca25a6bda1f5513d6df61e5240e69e",
        "d6f66d42df86624ed128b84ce57df3d173fe1b95",
        "The pytest changelog exposes the samefile_nofollow implementation detail instead of only describing the user-visible Windows collection fix.",
        "causal_mislocalization",
    ),
    ReviewSpec(
        "psf",
        "black",
        5288,
        3723956142,
        "83da43a3bd43fc832fc41c5aa448338c25c7d7cb",
        "928f50354512b3857ca07c1085076286035e4a56",
        "docs/integrations/editors.md redundantly links vim-plug in an example even though the section already links it.",
        "stale_evidence",
    ),
    ReviewSpec(
        "Textualize",
        "rich",
        4070,
        3067345022,
        "63d3200199f6d4a01268d71f98f27dbe416ee268",
        "7f40063da781f4990d21423f23f7ccb3165ce0bd",
        "rich/console.py uses the private sys._getframe API, which is not portable across Python implementations.",
        "incorrect_call_relationship",
    ),
    ReviewSpec(
        "pydantic",
        "pydantic",
        13717,
        3870567067,
        "f2cb3992433c6c81179c2dd688fccfe4fa486cdd",
        "22b6bcecdd2be748ff2567e4e83a853be84554e2",
        "pydantic/json_schema.py checks validate_by_alias with 'is False' instead of the simpler 'not validate_by_alias' condition.",
        "behavior_inversion",
    ),
    ReviewSpec(
        "pydantic",
        "pydantic",
        13690,
        3842248596,
        "43b2e383b229219cb15606f17991562f5ada553f",
        "dc403980c7c1b43dc04d19d52fb9164ad7b1e516",
        "The MutableSequence test docstring does not identify the test as a regression for pull request 13573.",
        "stale_evidence",
    ),
    ReviewSpec(
        "python-poetry",
        "poetry",
        10973,
        3621508821,
        "6208f6e1f5a6eb945c8d8c101b89def75a111d24",
        "3a95c37c5d5ec600556f519e60e4340f35bbcac1",
        "On Windows, editable GUI scripts use the console-script wrapper and python.exe instead of the windowed launcher.",
        "behavior_inversion",
    ),
    ReviewSpec(
        "python-poetry",
        "poetry",
        10987,
        3615603172,
        "5ec337f4b16189427eea2862843345cd8174b5d2",
        "62ffee2c98f36c065bc45f482837229ee142db06",
        "setdefault drops duplicate same-name extra dependencies that have different markers or constraints.",
        "causal_mislocalization",
    ),
)


def main() -> None:
    if REPOS_DIR.exists():
        shutil.rmtree(REPOS_DIR)
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for pair_index, spec in enumerate(SPECS, start=1):
        comment = _get_json(
            f"https://api.github.com/repos/{spec.owner}/{spec.repo}/pulls/comments/{spec.comment_id}"
        )
        _validate_comment(spec, comment)
        changed_files = _get_json(
            f"https://api.github.com/repos/{spec.owner}/{spec.repo}/pulls/{spec.pull_number}/files?per_page=100"
        )
        if not isinstance(changed_files, list):
            raise RuntimeError(f"Unexpected files response for {spec.owner}/{spec.repo}#{spec.pull_number}")
        target_path = str(comment["path"])
        review_text = _get_raw(spec, spec.review_commit, target_path)
        merge_text = _get_raw(spec, spec.merge_commit, target_path)
        review_line = int(comment.get("original_line") or comment.get("line") or 1)
        merge_line = _map_line(review_text.splitlines(), merge_text.splitlines(), review_line)
        companion = _select_companion(changed_files, target_path)

        snapshots = (
            ("SUPPORTED", spec.review_commit, review_text, review_line, "reviewed"),
            ("UNSUPPORTED", spec.merge_commit, merge_text, merge_line, "merged"),
        )
        for offset, (label, commit, target_text, target_line, snapshot_kind) in enumerate(snapshots):
            case_number = (pair_index - 1) * 2 + offset + 1
            case_id = f"humanpr20_{case_number:03d}"
            repo_dir = REPOS_DIR / f"case_{case_number:03d}"
            context_dir = repo_dir / "context"
            context_dir.mkdir(parents=True, exist_ok=True)
            target_suffix = Path(target_path).suffix or ".txt"
            target_context = Path("context") / f"target{target_suffix}"
            (repo_dir / target_context).write_text(
                _render_excerpt(target_path, commit, target_text, target_line, radius=55),
                encoding="utf-8",
            )
            companion_context = _write_companion(
                spec,
                commit,
                changed_files,
                companion,
                repo_dir,
                snapshot_kind,
            )
            source_url = str(comment["html_url"])
            row = {
                "case_id": case_id,
                "repo_path": repo_dir.relative_to(ROOT).as_posix(),
                "task_description": (
                    "Evaluate a candidate finding derived from a public pull-request review comment. "
                    "The context files are focused excerpts from one exact repository snapshot and "
                    "include a second changed file when available."
                ),
                "claim": spec.claim,
                "ground_truth": label,
                "ground_truth_evidence": (
                    f"Human review thread {source_url}; exact {snapshot_kind} snapshot {commit}."
                ),
                "validation_command": ["python", "-c", "print('context-only benchmark')"],
                "claim_family": spec.claim_family,
                "source_repository": f"https://github.com/{spec.owner}/{spec.repo}",
                "source_commit": commit,
                "source_pull_request": f"https://github.com/{spec.owner}/{spec.repo}/pull/{spec.pull_number}",
                "source_comment_url": source_url,
                "source_comment_id": spec.comment_id,
                "source_comment_author": str(comment["user"]["login"]),
                "source_comment_body": str(comment["body"]),
                "source_comment_path": target_path,
                "source_comment_line": review_line,
                "snapshot_kind": snapshot_kind,
                "paired_case_id": f"humanpr20_{((pair_index - 1) * 2 + (2 if offset == 0 else 1)):03d}",
                "target_context_file": target_context.as_posix(),
                "companion_context_file": companion_context.as_posix() if companion_context else None,
            }
            rows.append(row)
    CASES_PATH.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    print(CASES_PATH)


def _validate_comment(spec: ReviewSpec, comment: object) -> None:
    if not isinstance(comment, dict):
        raise RuntimeError(f"Unexpected comment response for {spec.comment_id}")
    if int(comment.get("id", 0)) != spec.comment_id:
        raise RuntimeError(f"Comment id mismatch for {spec.comment_id}")
    if str(comment.get("commit_id")) != spec.review_commit:
        raise RuntimeError(
            f"Review commit changed for {spec.comment_id}: {comment.get('commit_id')} != {spec.review_commit}"
        )
    author = str((comment.get("user") or {}).get("login", ""))
    if not author or author.endswith("[bot]"):
        raise RuntimeError(f"Comment {spec.comment_id} is not attributed to a human account")


def _select_companion(changed_files: list[object], target_path: str) -> dict[str, object] | None:
    candidates = [
        item
        for item in changed_files
        if isinstance(item, dict)
        and item.get("filename") != target_path
        and Path(str(item.get("filename", ""))).suffix.lower()
        in {".py", ".md", ".toml", ".yaml", ".yml"}
    ]
    if not candidates:
        return None
    target_is_test = "test" in Path(target_path).name.lower() or "/tests/" in f"/{target_path}"
    candidates.sort(
        key=lambda item: (
            0
            if target_is_test != ("test" in Path(str(item["filename"])).name.lower() or "/tests/" in f"/{item['filename']}")
            else 1,
            str(item["filename"]),
        )
    )
    return candidates[0]


def _write_companion(
    spec: ReviewSpec,
    commit: str,
    changed_files: list[object],
    companion: dict[str, object] | None,
    repo_dir: Path,
    snapshot_kind: str,
) -> Path | None:
    del changed_files, snapshot_kind
    if companion is None:
        return None
    path = str(companion["filename"])
    try:
        text = _get_raw(spec, commit, path)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    old_start, new_start = _patch_starts(str(companion.get("patch") or ""))
    line = old_start if commit == spec.review_commit else new_start
    suffix = Path(path).suffix or ".txt"
    relative = Path("context") / f"companion{suffix}"
    (repo_dir / relative).write_text(
        _render_excerpt(path, commit, text, line, radius=24),
        encoding="utf-8",
    )
    return relative


def _patch_starts(patch: str) -> tuple[int, int]:
    match = re.search(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", patch)
    if match is None:
        return 1, 1
    return int(match.group(1)), int(match.group(2))


def _map_line(before: list[str], after: list[str], one_based_line: int) -> int:
    index = max(0, min(len(before) - 1, one_based_line - 1)) if before else 0
    matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if i1 <= index < i2:
            if tag == "equal":
                return j1 + (index - i1) + 1
            if j1 < j2:
                return min(j2, j1 + max(0, index - i1)) + 1
            return min(len(after), j1 + 1)
    return min(len(after), index + 1) if after else 1


def _render_excerpt(path: str, commit: str, text: str, line: int, *, radius: int) -> str:
    lines = text.splitlines()
    center = max(0, min(len(lines) - 1, line - 1)) if lines else 0
    start = max(0, center - radius)
    end = min(len(lines), center + radius + 1)
    excerpt = "\n".join(lines[start:end]).rstrip()
    return f"Original path: {path}\nSnapshot commit: {commit}\nOriginal lines: {start + 1}-{end}\n\n{excerpt}\n"


def _get_raw(spec: ReviewSpec, commit: str, path: str) -> str:
    encoded_path = urllib.parse.quote(path, safe="/")
    url = f"https://raw.githubusercontent.com/{spec.owner}/{spec.repo}/{commit}/{encoded_path}"
    return _get(url).decode("utf-8")


def _get_json(url: str) -> object:
    return json.loads(_get(url).decode("utf-8"))


def _get(url: str) -> bytes:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "evar-human-pr-benchmark"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


if __name__ == "__main__":
    main()
