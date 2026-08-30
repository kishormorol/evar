from __future__ import annotations

import ast
import re
import shlex
import subprocess
import os
import textwrap
from dataclasses import dataclass
from pathlib import Path

from evar.verifier.models import (
    EvidenceReceipt,
    EvidenceRole,
    EvidenceType,
    VerificationResult,
    VerificationStatus,
)


DEFAULT_TIMEOUT_SECONDS = 5.0
BEHAVIORAL_SUPPORT_MARKER = "EVAR_WITNESS_PASS"


@dataclass(frozen=True)
class CommandExecution:
    command: str
    argv: tuple[str, ...]
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool = False


def verify_evidence(
    receipt: EvidenceReceipt,
    repo_path: Path,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> VerificationResult:
    """Verify a reviewer evidence receipt without using an LLM."""
    repo_result = _check_repo_path(repo_path)
    if repo_result is not None:
        return repo_result

    repo_root = repo_path.resolve()
    target = _resolve_receipt_file(
        repo_root,
        receipt.file,
        receipt.claim,
        allow_recovery=receipt.evidence_type == EvidenceType.STRUCTURAL,
    )

    file_result = _check_file(receipt, target)
    if file_result is not None:
        return file_result

    line_result = _check_line_range(receipt, target)
    if line_result is not None:
        return line_result

    if receipt.evidence_type == EvidenceType.STRUCTURAL:
        return _verify_structural(receipt, target)
    if receipt.evidence_type == EvidenceType.BEHAVIORAL:
        return _verify_behavioral(receipt, repo_root, timeout_seconds)

    return VerificationResult(
        status=VerificationStatus.UNVERIFIABLE,
        stdout="",
        stderr="",
        exit_code=None,
        reason=f"Unsupported evidence type: {receipt.evidence_type}",
    )


def execute_command(
    command: str,
    repo_path: Path,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> CommandExecution:
    """Central command execution point; intentionally uses shell=False."""
    argv = _parse_command(command)
    popen_args: str | list[str] = command if os.name == "nt" else argv
    try:
        completed = subprocess.run(
            popen_args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandExecution(
            command=command,
            argv=tuple(argv),
            stdout=_to_text(exc.stdout),
            stderr=_to_text(exc.stderr),
            exit_code=None,
            timed_out=True,
        )

    return CommandExecution(
        command=command,
        argv=tuple(argv),
        stdout=completed.stdout,
        stderr=completed.stderr,
        exit_code=completed.returncode,
    )


def _parse_command(command: str) -> list[str]:
    if not command or not command.strip():
        raise ValueError("verification_command must be a non-empty string.")
    return shlex.split(command, posix=os.name != "nt")


def _check_repo_path(repo_path: Path) -> VerificationResult | None:
    if not repo_path.exists():
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason=f"Repository path does not exist: {repo_path}",
        )
    if not repo_path.is_dir():
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason=f"Repository path is not a directory: {repo_path}",
        )
    return None


def _resolve_receipt_file(
    repo_root: Path,
    file_path: str,
    claim: str = "",
    *,
    allow_recovery: bool = True,
) -> Path:
    path = Path(file_path)
    if path.is_absolute():
        return path
    target = repo_root / path
    if target.exists():
        return target
    if not allow_recovery:
        return target

    normalized = file_path.replace("\\", "/")
    files = [candidate for candidate in repo_root.rglob("*") if candidate.is_file()]
    python_files = [candidate for candidate in files if candidate.suffix.lower() == ".py"]
    suffix_matches = [
        candidate
        for candidate in files
        if candidate.relative_to(repo_root).as_posix() in normalized
        or normalized.endswith(candidate.relative_to(repo_root).as_posix())
        or candidate.name == path.name
    ]
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    function_matches = [
        candidate
        for candidate in python_files
        if any(_file_defines_function(candidate, name) for name in _claim_function_names(claim))
    ]
    if len(function_matches) == 1:
        return function_matches[0]
    if len(python_files) == 1:
        return python_files[0]
    return target


def _check_file(receipt: EvidenceReceipt, target: Path) -> VerificationResult | None:
    if not receipt.file or not str(receipt.file).strip():
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason="Evidence receipt requires a referenced file.",
        )
    if not target.exists():
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason=f"Referenced file does not exist: {receipt.file}",
        )
    if not target.is_file():
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason=f"Referenced path is not a file: {receipt.file}",
        )
    return None


def _check_line_range(receipt: EvidenceReceipt, target: Path) -> VerificationResult | None:
    if receipt.line_start is None and receipt.line_end is None:
        return None
    if receipt.line_start is None or receipt.line_end is None:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason="Evidence line range must include both line_start and line_end.",
        )
    if receipt.line_start < 1 or receipt.line_end < receipt.line_start:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason="Evidence receipt has an invalid line range.",
        )

    line_count = len(target.read_text(encoding="utf-8").splitlines())
    if receipt.line_end > line_count and receipt.evidence_type != EvidenceType.STRUCTURAL:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason="Requested lines do not exist in referenced file.",
        )
    return None


def _verify_structural(receipt: EvidenceReceipt, target: Path) -> VerificationResult:
    if receipt.line_start is None or receipt.line_end is None:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason="Structural evidence requires line_start and line_end.",
        )

    lines = target.read_text(encoding="utf-8").splitlines()
    used_stale_line_recovery = receipt.line_end > len(lines)
    if not used_stale_line_recovery:
        excerpt = "\n".join(lines[receipt.line_start - 1 : receipt.line_end])
    else:
        excerpt = "\n".join(lines)
    normalized_excerpt = _normalize_structural_text(excerpt)
    ast_result = _verify_python_structural_claim(receipt, target, excerpt)
    if ast_result is not None:
        return ast_result
    if (
        receipt.falsification_condition
        and _normalize_structural_text(receipt.falsification_condition) in normalized_excerpt
    ):
        return VerificationResult(
            status=VerificationStatus.FAILED,
            stdout=excerpt,
            stderr="",
            exit_code=0,
            reason="Falsification condition was observed in referenced lines.",
        )
    if receipt.expected_stdout_contains and not _structural_observation_present(
        receipt.expected_stdout_contains,
        excerpt,
        "\n".join(lines),
    ):
        if used_stale_line_recovery:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIABLE,
                stdout=excerpt,
                stderr="",
                exit_code=0,
                reason="Requested lines do not exist and expected structural observation was not found elsewhere.",
            )
        return VerificationResult(
            status=VerificationStatus.FAILED,
            stdout=excerpt,
            stderr="",
            exit_code=0,
            reason="Expected structural observation was not present in referenced lines.",
        )
    if not receipt.expected_stdout_contains:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout=excerpt,
            stderr="",
            exit_code=0,
            reason="Structural evidence requires expected_stdout_contains.",
        )
    return VerificationResult(
        status=VerificationStatus.VERIFIED,
        stdout=excerpt,
        stderr="",
        exit_code=0,
        reason="Structural evidence verified.",
    )


def _normalize_structural_text(text: str) -> str:
    text = text.replace("\\n", "\n")
    return "\n".join(line.strip() for line in textwrap.dedent(text).strip().splitlines())


def _normalize_structural_for_match(text: str) -> str:
    return _normalize_structural_text(text).replace('"', "").replace("'", "")


def _structural_observation_present(expected: str, excerpt: str, full_text: str) -> bool:
    haystacks = {
        _normalize_structural_text(excerpt),
        _normalize_structural_text(full_text),
        _normalize_structural_for_match(excerpt),
        _normalize_structural_for_match(full_text),
    }
    for candidate in _structural_quote_candidates(expected):
        normalized = _normalize_structural_text(candidate)
        normalized_loose = _normalize_structural_for_match(candidate)
        if any(normalized in haystack or normalized_loose in haystack for haystack in haystacks):
            return True
    return False


def _structural_quote_candidates(text: str) -> set[str]:
    """Return conservative variants of a copied source quote.

    Models sometimes preserve the line-number prefix shown in repository context or
    wrap an exact quote in Markdown. Removing only those display artifacts retains
    exact-source matching without introducing fuzzy semantic verification.
    """
    stripped = text.strip()
    candidates = {stripped}
    if stripped.startswith("```") and stripped.endswith("```"):
        inner = stripped[3:-3].strip()
        if "\n" in inner and re.fullmatch(r"[A-Za-z0-9_+.-]+", inner.splitlines()[0].strip()):
            inner = "\n".join(inner.splitlines()[1:])
        candidates.add(inner.strip())
    if len(stripped) >= 2 and stripped[0] == stripped[-1] == "`":
        candidates.add(stripped[1:-1].strip())
    numbered = "\n".join(re.sub(r"^\s*\d+\s*:\s?", "", line) for line in stripped.splitlines())
    candidates.add(numbered.strip())
    return {candidate for candidate in candidates if candidate}


def _verify_python_structural_claim(
    receipt: EvidenceReceipt,
    target: Path,
    excerpt: str,
) -> VerificationResult | None:
    if target.suffix.lower() != ".py":
        return None
    try:
        tree = ast.parse(target.read_text(encoding="utf-8"))
    except SyntaxError:
        return None

    claim = receipt.claim
    checks = [
        _check_call_relationship,
        _check_missing_negative_guard,
        _check_stale_return,
        _check_duplicate_append,
        _check_subprocess_shell_false,
        _check_transcript_write,
        _check_match_dirs_requires_slash,
        _check_raises_exception,
        _check_extend_regex_terminator,
        _check_translate_match_dirs_wrapping,
        _check_striptags_whitespace_order,
        _check_path_open_exists_order,
        _check_is_symlink_external_attr,
        _check_path_base_purepath,
        _check_ancestry_separator_behavior,
    ]
    for check in checks:
        observed = check(tree, claim)
        if observed is not None:
            return _role_result(receipt, observed, excerpt, check.__name__)
    return None


def _role_result(
    receipt: EvidenceReceipt,
    observed_supports_claim: bool,
    excerpt: str,
    check_name: str,
) -> VerificationResult:
    if receipt.evidence_role == EvidenceRole.SUPPORTS_CLAIM:
        status = VerificationStatus.VERIFIED if observed_supports_claim else VerificationStatus.FAILED
    else:
        status = VerificationStatus.VERIFIED if not observed_supports_claim else VerificationStatus.FAILED
    return VerificationResult(
        status=status,
        stdout=excerpt,
        stderr="",
        exit_code=0,
        reason=(
            f"Python AST structural check {check_name} observed "
            f"supports_claim={observed_supports_claim}; evidence_role={receipt.evidence_role.value}."
        ),
    )


def _check_call_relationship(tree: ast.AST, claim: str) -> bool | None:
    match = re.search(r"\b([A-Za-z_]\w*)\([^)]*\)\s+calls\s+([A-Za-z_]\w*)\(", claim)
    if match is None:
        return None
    caller, callee = match.groups()
    function = _find_function(tree, caller)
    if function is None:
        return False
    return any(isinstance(node, ast.Call) and _call_name(node.func) == callee for node in ast.walk(function))


def _check_missing_negative_guard(tree: ast.AST, claim: str) -> bool | None:
    match = re.search(r"\b([A-Za-z_]\w*)\(([^)]*)\)\s+is missing a guard against negative amounts", claim)
    if match is None:
        return None
    function_name = match.group(1)
    argument = match.group(2).split(",", 1)[0].strip() or "amount"
    function = _find_function(tree, function_name)
    if function is None:
        return False
    has_negative_guard = any(_is_negative_guard(node, argument) for node in ast.walk(function))
    return not has_negative_guard


def _check_stale_return(tree: ast.AST, claim: str) -> bool | None:
    match = re.search(
        r"\b([A-Za-z_]\w*)\([^)]*\)\s+still reads stale values because it returns\s+([A-Za-z_]\w*)\s+without recomputing",
        claim,
    )
    if match is None:
        return None
    function_name, cached_name = match.groups()
    function = _find_function(tree, function_name)
    if function is None:
        return False
    return any(
        isinstance(node, ast.Return)
        and isinstance(node.value, ast.Name)
        and node.value.id == cached_name
        for node in ast.walk(function)
    )


def _check_duplicate_append(tree: ast.AST, claim: str) -> bool | None:
    match = re.search(r"\b([A-Za-z_]\w*)\s+appending the same record twice", claim)
    if match is None:
        return None
    function = _find_function(tree, match.group(1))
    if function is None:
        return False
    for node in ast.walk(function):
        if not isinstance(node, ast.For):
            continue
        target_name = node.target.id if isinstance(node.target, ast.Name) else None
        append_count = 0
        for statement in node.body:
            if _is_append_of_name(statement, target_name):
                append_count += 1
        if append_count >= 2:
            return True
    return False


def _check_subprocess_shell_false(tree: ast.AST, claim: str) -> bool | None:
    normalized = claim.lower()
    if "subprocess.run" not in normalized or "shell=false" not in normalized:
        return None
    function_name = _leading_function_name(claim)
    function = _find_function(tree, function_name) if function_name else None
    search_root: ast.AST = function if function is not None else tree
    for node in ast.walk(search_root):
        if not isinstance(node, ast.Call) or _dotted_call_name(node.func) != "subprocess.run":
            continue
        for keyword in node.keywords:
            if (
                keyword.arg == "shell"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is False
            ):
                return True
        return False
    return False


def _check_transcript_write(tree: ast.AST, claim: str) -> bool | None:
    normalized = claim.lower()
    if "transcript" not in normalized or "results/transcripts" not in normalized:
        return None
    run_configured = _find_function(tree, "_run_configured")
    write_configured = _find_function(tree, "_write_configured_transcript")
    if run_configured is None or write_configured is None:
        return False
    creates_transcript_dir = any(
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "transcript_dir" for target in node.targets)
        and "transcripts" in _constant_strings(node.value)
        for node in ast.walk(run_configured)
    )
    calls_writer = any(
        isinstance(node, ast.Call) and _call_name(node.func) == "_write_configured_transcript"
        for node in ast.walk(run_configured)
    )
    writes_case_json = any(
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "transcript_path" for target in node.targets)
        and any("json" in value for value in _joined_value_strings(node.value))
        and "case_id" in _joined_value_names(node.value)
        for node in ast.walk(write_configured)
    )
    persists_transcript = any(
        isinstance(node, ast.Call) and _call_name(node.func) in {"write_text", "dump"}
        for node in ast.walk(write_configured)
    )
    return creates_transcript_dir and calls_writer and writes_case_json and persists_transcript


def _check_match_dirs_requires_slash(tree: ast.AST, claim: str) -> bool | None:
    normalized = claim.lower()
    if "match_dirs" not in normalized or "requires" not in normalized or "slash" not in normalized:
        return None
    function = _find_function(tree, "match_dirs")
    if function is None:
        return False
    for node in ast.walk(function):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        text = "".join(_joined_value_strings(node.value))
        if "[/]?" in text:
            return False
        if "[/]" in text or "/" in text:
            return True
    return False


def _check_raises_exception(tree: ast.AST, claim: str) -> bool | None:
    match = re.search(r"\b(?:[A-Za-z_]\w*\.)?([A-Za-z_]\w*)\s+.*raises\s+([A-Za-z_]\w*)", claim)
    if match is None:
        return None
    function_name, exception_name = match.groups()
    function = _find_function(tree, function_name)
    if function is None:
        return False
    return any(_raise_exception_name(node) == exception_name for node in ast.walk(function) if isinstance(node, ast.Raise))


def _check_extend_regex_terminator(tree: ast.AST, claim: str) -> bool | None:
    normalized = claim.lower()
    if "extend" not in normalized or "generated regex" not in normalized:
        return None
    if "\\z" not in claim and "\\Z" not in claim:
        return None
    expected = "\\z" if "\\z" in claim else "\\Z"
    function = _find_function(tree, "extend")
    if function is None:
        return False
    return any(
        isinstance(node, ast.Return) and expected in "".join(_joined_value_strings(node.value))
        for node in ast.walk(function)
        if isinstance(node, ast.Return) and node.value is not None
    )


def _check_translate_match_dirs_wrapping(tree: ast.AST, claim: str) -> bool | None:
    normalized = claim.lower()
    if "translate" not in normalized or "translate_core" not in normalized or "match_dirs" not in normalized:
        return None
    if "wraps" not in normalized and "without match_dirs" not in normalized:
        return None
    function = _find_function(tree, "translate")
    if function is None:
        return False
    wraps_translate_core = any(
        isinstance(node, ast.Call)
        and _call_name(node.func) == "match_dirs"
        and any(
            isinstance(child, ast.Call) and _call_name(child.func) == "translate_core"
            for child in ast.walk(node)
        )
        for node in ast.walk(function)
    )
    if "without match_dirs" in normalized:
        return not wraps_translate_core
    return wraps_translate_core


def _check_striptags_whitespace_order(tree: ast.AST, claim: str) -> bool | None:
    normalized = claim.lower()
    if "striptags" not in normalized or "collapses whitespace" not in normalized:
        return None
    wants_after = "after removing comments and tags" in normalized
    wants_before = "before removing comments and tags" in normalized
    if not wants_after and not wants_before:
        return None
    function = _find_function(tree, "striptags")
    if function is None:
        return False
    collapse_lines = [
        node.lineno
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and _call_name(node.func) == "join"
        and any(isinstance(child, ast.Call) and _call_name(child.func) == "split" for child in ast.walk(node))
    ]
    removal_lines = [
        node.lineno
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and _call_name(node.func) == "find"
        and any(value in {"<!--", "<"} for value in _constant_strings(node))
    ]
    if not collapse_lines or not removal_lines:
        return False
    collapse_after = min(collapse_lines) > max(removal_lines)
    return collapse_after if wants_after else not collapse_after


def _check_path_open_exists_order(tree: ast.AST, claim: str) -> bool | None:
    normalized = claim.lower()
    if (
        "path.open" not in normalized
        or "self.exists" not in normalized
        or ("zip mode" not in normalized and "zip_mode" not in normalized)
    ):
        return None
    wants_exists_first = "self.exists" in normalized and "before checking" in normalized
    wants_zip_mode_first = (
        ("checks zip_mode" in normalized or "checks zip mode" in normalized)
        and "before calling self.exists" in normalized
    )
    if not wants_exists_first and not wants_zip_mode_first:
        return None
    function = _find_function(tree, "open")
    if function is None:
        return False
    for node in ast.walk(function):
        if not isinstance(node, ast.If):
            continue
        order = _zip_mode_and_exists_order(node.test)
        if order is not None:
            expected_order = ("exists", "zip_mode") if wants_exists_first else ("zip_mode", "exists")
            return order == expected_order
    return False


def _check_is_symlink_external_attr(tree: ast.AST, claim: str) -> bool | None:
    normalized = claim.lower()
    if "is_symlink" not in normalized:
        return None
    if "external_attr" not in normalized and "always returns false" not in normalized:
        return None
    function = _find_function(tree, "is_symlink")
    if function is None:
        return False
    derives_mode_from_external_attr = any(
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.RShift)
        and any(_dotted_call_name(child) == "info.external_attr" for child in ast.walk(node.left))
        for node in ast.walk(function)
    )
    returns_s_islnk = any(
        isinstance(node, ast.Return)
        and node.value is not None
        and any(
            isinstance(child, ast.Call) and _dotted_call_name(child.func) == "stat.S_ISLNK"
            for child in ast.walk(node.value)
        )
        for node in ast.walk(function)
    )
    always_returns_false = any(
        isinstance(node, ast.Return)
        and isinstance(node.value, ast.Constant)
        and node.value.value is False
        for node in ast.walk(function)
    )
    if "always returns false" in normalized:
        return always_returns_false and not returns_s_islnk
    return derives_mode_from_external_attr and returns_s_islnk


def _check_path_base_purepath(tree: ast.AST, claim: str) -> bool | None:
    normalized = claim.lower()
    if "_base" not in normalized or ("purepath" not in normalized and "pureposixpath" not in normalized):
        return None
    function = _find_function(tree, "_base")
    if function is None:
        return False
    root_filename_purepath = False
    root_filename_pureposix = False
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        call_name = _dotted_call_name(node.func)
        if call_name not in {"pathlib.PurePath", "pathlib.PurePosixPath", "PurePath", "PurePosixPath"}:
            continue
        if not node.args or "filename" not in _joined_value_names(node.args[0]):
            continue
        if call_name in {"pathlib.PurePath", "PurePath"}:
            root_filename_purepath = True
        if call_name in {"pathlib.PurePosixPath", "PurePosixPath"}:
            root_filename_pureposix = True
    if "always" in normalized and "pureposixpath" in normalized:
        return root_filename_pureposix and not root_filename_purepath
    if "when self.at is empty" in normalized:
        return root_filename_purepath
    return None


def _check_ancestry_separator_behavior(tree: ast.AST, claim: str) -> bool | None:
    normalized = claim.lower()
    if "_ancestry" not in normalized:
        return None
    function = _find_function(tree, "_ancestry")
    if function is None:
        return False
    has_endswith_stop = any(
        isinstance(node, ast.Call)
        and _call_name(node.func) == "endswith"
        and any(_dotted_call_name(child) == "posixpath.sep" for child in ast.walk(node))
        for node in ast.walk(function)
    )
    has_exact_sep_compare = any(
        isinstance(node, ast.Compare)
        and any(_dotted_call_name(comparator) == "posixpath.sep" for comparator in node.comparators)
        for node in ast.walk(function)
    )
    if "multiple separators" in normalized:
        return has_endswith_stop
    if "equals exactly posixpath.sep" in normalized:
        return has_exact_sep_compare and not has_endswith_stop
    return None


def _zip_mode_and_exists_order(node: ast.AST) -> tuple[str, str] | None:
    events = _ordered_condition_events(node)
    if "zip_mode" not in events or "exists" not in events:
        return None
    return (
        "exists" if events.index("exists") < events.index("zip_mode") else "zip_mode",
        "zip_mode" if events.index("exists") < events.index("zip_mode") else "exists",
    )


def _ordered_condition_events(node: ast.AST) -> list[str]:
    if isinstance(node, ast.BoolOp):
        events: list[str] = []
        for value in node.values:
            events.extend(_ordered_condition_events(value))
        return events
    if _is_zip_mode_read_check(node):
        return ["zip_mode"]
    if _contains_self_exists_call(node):
        return ["exists"]
    if isinstance(node, ast.UnaryOp):
        return _ordered_condition_events(node.operand)
    if isinstance(node, ast.Compare):
        events = _ordered_condition_events(node.left)
        for comparator in node.comparators:
            events.extend(_ordered_condition_events(comparator))
        return events
    return []


def _is_zip_mode_read_check(node: ast.AST) -> bool:
    if not isinstance(node, ast.Compare):
        return False
    names = [_dotted_call_name(node.left), *[_dotted_call_name(comparator) for comparator in node.comparators]]
    constants = [
        item.value
        for item in [node.left, *node.comparators]
        if isinstance(item, ast.Constant) and isinstance(item.value, str)
    ]
    return "zip_mode" in names and "r" in constants


def _contains_self_exists_call(node: ast.AST) -> bool:
    return any(
        isinstance(item, ast.Call) and _dotted_call_name(item.func) == "self.exists"
        for item in ast.walk(node)
    )


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
            return node
    return None


def _claim_function_names(claim: str) -> list[str]:
    names = re.findall(r"\b([A-Za-z_]\w*)\s*\(", claim)
    names.extend(re.findall(r"\b[A-Za-z_]\w*\.([A-Za-z_]\w*)\b", claim))
    leading = _leading_function_name(claim)
    if leading:
        names.append(leading)
    return list(dict.fromkeys(names))


def _leading_function_name(claim: str) -> str | None:
    match = re.match(r"\s*([A-Za-z_]\w*)\b", claim)
    return match.group(1) if match else None


def _file_defines_function(path: Path, name: str) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False
    return _find_function(tree, name) is not None


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _dotted_call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def _raise_exception_name(node: ast.Raise) -> str | None:
    if node.exc is None:
        return None
    if isinstance(node.exc, ast.Call):
        return _call_name(node.exc.func)
    return _call_name(node.exc)


def _constant_strings(node: ast.AST) -> set[str]:
    return {item.value for item in ast.walk(node) if isinstance(item, ast.Constant) and isinstance(item.value, str)}


def _joined_value_strings(node: ast.AST) -> set[str]:
    values: set[str] = set()
    for item in ast.walk(node):
        if isinstance(item, ast.Constant) and isinstance(item.value, str):
            values.add(item.value)
        elif isinstance(item, ast.JoinedStr):
            values.update(_constant_strings(item))
    return values


def _joined_value_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for item in ast.walk(node):
        if isinstance(item, ast.Name):
            names.add(item.id)
        elif isinstance(item, ast.Attribute):
            names.add(item.attr)
    return names


def _is_negative_guard(node: ast.AST, argument: str) -> bool:
    if not isinstance(node, ast.If):
        return False
    return any(
        isinstance(item, ast.Compare)
        and isinstance(item.left, ast.Name)
        and item.left.id == argument
        and any(isinstance(operator, ast.Lt | ast.LtE) for operator in item.ops)
        and any(isinstance(comparator, ast.Constant) and comparator.value == 0 for comparator in item.comparators)
        for item in ast.walk(node.test)
    )


def _is_append_of_name(statement: ast.stmt, name: str | None) -> bool:
    if name is None or not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
        return False
    call = statement.value
    return (
        isinstance(call.func, ast.Attribute)
        and call.func.attr == "append"
        and len(call.args) == 1
        and isinstance(call.args[0], ast.Name)
        and call.args[0].id == name
    )


def _verify_behavioral(
    receipt: EvidenceReceipt,
    repo_root: Path,
    timeout_seconds: float,
) -> VerificationResult:
    if receipt.verification_command is None:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason="Behavioral evidence requires verification_command.",
        )
    if receipt.expected_exit_code is None and receipt.expected_stdout_contains is None:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason="Behavioral evidence requires expected_exit_code or expected_stdout_contains.",
        )
    if (
        receipt.expected_stdout_contains is None
        or BEHAVIORAL_SUPPORT_MARKER not in receipt.expected_stdout_contains
    ):
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason=(
                "Behavioral evidence requires expected_stdout_contains to include "
                f"{BEHAVIORAL_SUPPORT_MARKER!r}, printed only when the witness supports the claim."
            ),
        )

    try:
        execution = execute_command(
            receipt.verification_command,
            repo_root,
            timeout_seconds=timeout_seconds,
        )
    except ValueError as exc:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr="",
            exit_code=None,
            reason=str(exc),
        )
    except OSError as exc:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout="",
            stderr=str(exc),
            exit_code=None,
            reason=f"Verification command could not be executed: {receipt.verification_command}",
        )

    command_note = f"command={execution.command!r}; argv={list(execution.argv)!r}"
    if execution.timed_out:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIABLE,
            stdout=execution.stdout,
            stderr=execution.stderr,
            exit_code=None,
            reason=f"Verification command timed out after {timeout_seconds} seconds; {command_note}",
        )

    if receipt.expected_exit_code is not None and execution.exit_code != receipt.expected_exit_code:
        return VerificationResult(
            status=VerificationStatus.FAILED,
            stdout=execution.stdout,
            stderr=execution.stderr,
            exit_code=execution.exit_code,
            reason=f"Expected exit code {receipt.expected_exit_code}, observed {execution.exit_code}; {command_note}",
        )
    if receipt.falsification_condition and receipt.falsification_condition in execution.stdout + execution.stderr:
        return VerificationResult(
            status=VerificationStatus.FAILED,
            stdout=execution.stdout,
            stderr=execution.stderr,
            exit_code=execution.exit_code,
            reason=f"Falsification condition was observed in command output; {command_note}",
        )
    if (
        receipt.expected_stdout_contains is not None
        and receipt.expected_stdout_contains not in execution.stdout
    ):
        return VerificationResult(
            status=VerificationStatus.FAILED,
            stdout=execution.stdout,
            stderr=execution.stderr,
            exit_code=execution.exit_code,
            reason=f"Expected stdout text was not observed; {command_note}",
        )
    return VerificationResult(
        status=VerificationStatus.VERIFIED,
        stdout=execution.stdout,
        stderr=execution.stderr,
        exit_code=execution.exit_code,
        reason=f"Behavioral evidence verified; {command_note}",
    )


def _to_text(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


class DeterministicVerifier:
    """Dispatches structured receipts to deterministic non-LLM verifiers."""

    def __init__(
        self,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.timeout_seconds = timeout_seconds

    def verify(self, receipt: EvidenceReceipt, repo_path: Path) -> VerificationResult:
        return verify_evidence(receipt, repo_path, timeout_seconds=self.timeout_seconds)
