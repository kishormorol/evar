from __future__ import annotations

import argparse
import base64
import difflib
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


GITHUB_API = "https://api.github.com"
ALLOWED_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".md",
    ".py",
    ".rb",
    ".rs",
    ".rst",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}
BOT_SUFFIXES = ("[bot]", "-bot", "_bot")
LOW_INFORMATION = re.compile(
    r"^\s*(?:nit(?::|\b)|lgtm[.!]?|thanks?[.!]?|\+1|👍|ship it[.!]?)\s*$",
    re.IGNORECASE,
)
SUGGESTION = re.compile(r"```suggestion(?:\s*\r?\n|\r?\n)", re.IGNORECASE)


@dataclass(frozen=True)
class RepositorySpec:
    repository: str
    language: str

    @property
    def owner(self) -> str:
        return self.repository.split("/", 1)[0]

    @property
    def name(self) -> str:
        return self.repository.split("/", 1)[1]


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        self._pull_cache: dict[str, dict[str, Any]] = {}

    def get_json(self, url: str) -> object:
        return json.loads(self._get(url).decode("utf-8"))

    def get_pull(self, url: str) -> dict[str, Any]:
        if url not in self._pull_cache:
            value = self.get_json(url)
            if not isinstance(value, dict):
                raise RuntimeError(f"Unexpected pull response from {url}")
            self._pull_cache[url] = value
        return self._pull_cache[url]

    def get_file(self, repository: str, commit: str, path: str) -> bytes:
        encoded_path = urllib.parse.quote(path, safe="/")
        url = f"{GITHUB_API}/repos/{repository}/contents/{encoded_path}?ref={commit}"
        value = self.get_json(url)
        if not isinstance(value, dict) or value.get("type") != "file":
            raise RuntimeError(f"Unexpected content response for {repository}@{commit}:{path}")
        content = value.get("content")
        if not isinstance(content, str):
            raise RuntimeError(f"Missing content for {repository}@{commit}:{path}")
        return base64.b64decode(content)

    def _get(self, url: str) -> bytes:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "evar-human-pr-candidate-acquisition",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()


def load_repository_specs(path: Path) -> list[RepositorySpec]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("repositories"), list):
        raise ValueError("Repository registry must contain a repositories list.")
    specs: list[RepositorySpec] = []
    seen: set[str] = set()
    for item in raw["repositories"]:
        if not isinstance(item, dict):
            raise ValueError("Each repository registry entry must be an object.")
        repository = str(item.get("repository", "")).strip()
        language = str(item.get("language", "")).strip()
        if repository.count("/") != 1 or not language:
            raise ValueError(f"Invalid repository registry entry: {item!r}")
        if repository in seen:
            raise ValueError(f"Duplicate repository: {repository}")
        seen.add(repository)
        specs.append(RepositorySpec(repository, language))
    return specs


def load_excluded_comment_ids(paths: Iterable[Path]) -> set[int]:
    excluded: set[int] = set()
    for path in paths:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            value = row.get("source_comment_id")
            if isinstance(value, int):
                excluded.add(value)
    return excluded


def is_candidate_comment(comment: object, *, excluded_ids: set[int]) -> bool:
    if not isinstance(comment, dict):
        return False
    comment_id = comment.get("id")
    if not isinstance(comment_id, int) or comment_id in excluded_ids:
        return False
    user = comment.get("user")
    if not isinstance(user, dict):
        return False
    login = str(user.get("login", "")).strip()
    if not login or str(user.get("type", "")).lower() == "bot":
        return False
    lowered = login.lower()
    if lowered.endswith(BOT_SUFFIXES):
        return False
    body = str(comment.get("body", "")).strip()
    if len(body) < 20 or len(body) > 4_000 or LOW_INFORMATION.fullmatch(body):
        return False
    path = str(comment.get("path", ""))
    if Path(path).suffix.lower() not in ALLOWED_SUFFIXES:
        return False
    line = comment.get("original_line") or comment.get("line")
    return isinstance(line, int) and line > 0 and bool(comment.get("pull_request_url"))


def map_line(before: list[str], after: list[str], one_based_line: int) -> int:
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


def render_excerpt(path: str, commit: str, text: str, line: int, *, radius: int = 35) -> str:
    lines = text.splitlines()
    center = max(0, min(len(lines) - 1, line - 1)) if lines else 0
    start = max(0, center - radius)
    end = min(len(lines), center + radius + 1)
    excerpt = "\n".join(lines[start:end]).rstrip()
    return f"Original path: {path}\nSnapshot commit: {commit}\nOriginal lines: {start + 1}-{end}\n\n{excerpt}\n"


def anchor_changed(before: list[str], after: list[str], before_line: int, after_line: int) -> bool:
    def window(lines: list[str], line: int) -> str:
        index = max(0, line - 1)
        return "\n".join(lines[max(0, index - 2) : min(len(lines), index + 3)]).strip()

    return window(before, before_line) != window(after, after_line)


def priority_score(comment: dict[str, Any], *, changed_anchor: bool) -> int:
    body = str(comment.get("body", ""))
    association = str(comment.get("author_association", "")).upper()
    score = 0
    if changed_anchor:
        score += 4
    if SUGGESTION.search(body):
        score += 3
    if len(body) >= 80:
        score += 2
    if association in {"OWNER", "MEMBER", "COLLABORATOR"}:
        score += 1
    if re.search(r"\b(?:bug|incorrect|fails?|wrong|should|instead|missing|breaks?|error)\b", body, re.I):
        score += 1
    if re.search(r"\b(?:nit|typo|format(?:ting)?|style)\b", body, re.I):
        score -= 1
    return score


def build_candidate(
    spec: RepositorySpec,
    comment: dict[str, Any],
    pull: dict[str, Any],
    review_bytes: bytes,
    merge_bytes: bytes,
) -> dict[str, object] | None:
    try:
        review_text = review_bytes.decode("utf-8")
        merge_text = merge_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if review_text == merge_text:
        return None

    review_line = int(comment.get("original_line") or comment.get("line") or 0)
    review_lines = review_text.splitlines()
    merge_lines = merge_text.splitlines()
    if review_line <= 0 or review_line > len(review_lines):
        return None
    merge_line = map_line(review_lines, merge_lines, review_line)
    changed = anchor_changed(review_lines, merge_lines, review_line, merge_line)
    if not changed:
        return None

    comment_id = int(comment["id"])
    reviewed_commit = str(comment.get("original_commit_id") or comment.get("commit_id") or "")
    merge_commit = str(pull.get("merge_commit_sha") or "")
    path = str(comment["path"])
    if len(reviewed_commit) != 40 or len(merge_commit) != 40:
        return None

    return {
        "schema_version": 1,
        "candidate_id": f"hpr-{hashlib.sha256(f'{spec.repository}:{comment_id}'.encode()).hexdigest()[:16]}",
        "selection_status": "pending_annotation",
        "priority_score": priority_score(comment, changed_anchor=changed),
        "language": spec.language,
        "source_repository": f"https://github.com/{spec.repository}",
        "source_pull_request": str(pull.get("html_url") or ""),
        "source_pull_number": int(pull.get("number") or 0),
        "source_pull_title": str(pull.get("title") or ""),
        "source_pull_merged_at": str(pull.get("merged_at") or ""),
        "source_comment_id": comment_id,
        "source_comment_url": str(comment.get("html_url") or ""),
        "source_comment_author": str((comment.get("user") or {}).get("login") or ""),
        "source_comment_author_association": str(comment.get("author_association") or ""),
        "source_comment_created_at": str(comment.get("created_at") or ""),
        "source_comment_body": str(comment.get("body") or ""),
        "source_comment_diff_hunk": str(comment.get("diff_hunk") or ""),
        "source_comment_path": path,
        "source_comment_line": review_line,
        "review_commit": reviewed_commit,
        "merge_commit": merge_commit,
        "merge_line": merge_line,
        "review_file_sha256": hashlib.sha256(review_bytes).hexdigest(),
        "merge_file_sha256": hashlib.sha256(merge_bytes).hexdigest(),
        "review_excerpt": render_excerpt(path, reviewed_commit, review_text, review_line),
        "merge_excerpt": render_excerpt(path, merge_commit, merge_text, merge_line),
        "annotation": {
            "eligible": None,
            "normalized_claim": None,
            "claim_family": None,
            "exclusion_reason": None,
            "annotator_1": None,
            "annotator_2": None,
            "adjudicator": None,
        },
    }


def acquire_candidates(
    specs: list[RepositorySpec],
    *,
    client: GitHubClient,
    excluded_ids: set[int],
    cutoff: datetime,
    pages: int,
    per_repo: int,
) -> tuple[list[dict[str, object]], dict[str, dict[str, int]]]:
    candidates: list[dict[str, object]] = []
    audit: dict[str, dict[str, int]] = {}
    for spec in specs:
        counts = {"comments_seen": 0, "eligible_shape": 0, "reconstructed": 0, "selected": 0}
        repository_candidates: list[dict[str, object]] = []
        used_pulls: set[int] = set()
        stop_repo = False
        for page in range(1, pages + 1):
            url = (
                f"{GITHUB_API}/repos/{spec.repository}/pulls/comments"
                f"?sort=created&direction=desc&per_page=100&page={page}"
            )
            comments = client.get_json(url)
            if not isinstance(comments, list):
                raise RuntimeError(f"Unexpected comments response for {spec.repository}")
            if not comments:
                break
            for item in comments:
                counts["comments_seen"] += 1
                if not is_candidate_comment(item, excluded_ids=excluded_ids):
                    continue
                assert isinstance(item, dict)
                created_at = parse_github_time(str(item.get("created_at") or ""))
                if created_at > cutoff:
                    continue
                counts["eligible_shape"] += 1
                pull_url = str(item["pull_request_url"])
                pull_number = int(pull_url.rstrip("/").rsplit("/", 1)[-1])
                if pull_number in used_pulls:
                    continue
                try:
                    pull = client.get_pull(pull_url)
                except (urllib.error.HTTPError, RuntimeError, ValueError):
                    continue
                merged_at_raw = str(pull.get("merged_at") or "")
                if not merged_at_raw or parse_github_time(merged_at_raw) > cutoff:
                    continue
                reviewed_commit = str(item.get("original_commit_id") or item.get("commit_id") or "")
                merge_commit = str(pull.get("merge_commit_sha") or "")
                path = str(item["path"])
                try:
                    review_bytes = client.get_file(spec.repository, reviewed_commit, path)
                    merge_bytes = client.get_file(spec.repository, merge_commit, path)
                except (urllib.error.HTTPError, RuntimeError, ValueError):
                    continue
                candidate = build_candidate(spec, item, pull, review_bytes, merge_bytes)
                if candidate is None:
                    continue
                counts["reconstructed"] += 1
                used_pulls.add(pull_number)
                repository_candidates.append(candidate)
                if len(repository_candidates) >= per_repo:
                    stop_repo = True
                    break
            if stop_repo:
                break
        repository_candidates.sort(key=lambda row: (-int(row["priority_score"]), str(row["candidate_id"])))
        counts["selected"] = len(repository_candidates)
        candidates.extend(repository_candidates)
        audit[spec.repository] = counts
        print(
            f"{spec.repository}: selected {counts['selected']} "
            f"from {counts['comments_seen']} comments",
            flush=True,
        )
    candidates.sort(key=lambda row: (str(row["language"]), -int(row["priority_score"]), str(row["candidate_id"])))
    return candidates, audit


def parse_github_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def write_jsonl(path: Path, rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Acquire provenance-complete human PR review candidates.")
    parser.add_argument("--repositories", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--cutoff", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--pages", type=int, default=3)
    parser.add_argument("--per-repo", type=int, default=12)
    args = parser.parse_args(argv)
    if args.pages < 1 or args.per_repo < 1:
        parser.error("--pages and --per-repo must be positive")

    specs = load_repository_specs(args.repositories)
    root = Path(__file__).resolve().parents[2]
    excluded_ids = load_excluded_comment_ids((root / "benchmarks").glob("*/cases.jsonl"))
    cutoff = parse_github_time(args.cutoff)
    candidates, repositories = acquire_candidates(
        specs,
        client=GitHubClient(),
        excluded_ids=excluded_ids,
        cutoff=cutoff,
        pages=args.pages,
        per_repo=args.per_repo,
    )
    write_jsonl(args.output, candidates)
    languages: dict[str, int] = {}
    for row in candidates:
        language = str(row["language"])
        languages[language] = languages.get(language, 0) + 1
    audit = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cutoff": cutoff.isoformat(),
        "candidate_count": len(candidates),
        "repository_count": sum(1 for value in repositories.values() if value["selected"]),
        "language_counts": dict(sorted(languages.items())),
        "excluded_existing_comment_ids": len(excluded_ids),
        "repositories": repositories,
        "output_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
    }
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {len(candidates)} candidates to {args.output}")


if __name__ == "__main__":
    main()
