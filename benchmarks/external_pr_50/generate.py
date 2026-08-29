from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
SOURCE_CACHE = ROOT / "sources"
REPOS = ROOT / "repos"
CASES = ROOT / "cases.jsonl"


SOURCES = {
    "click": SOURCE_CACHE / "click",
    "pluggy": SOURCE_CACHE / "pluggy",
    "attrs": SOURCE_CACHE / "attrs",
    "more-itertools": SOURCE_CACHE / "more-itertools",
    "requests": SOURCE_CACHE / "requests",
}


@dataclass(frozen=True)
class Feature:
    repo: str
    commit: str
    files: dict[str, str]
    family: str
    task: str
    supported_claim: str
    supported_evidence: str
    unsupported_claim: str
    unsupported_evidence: str


FEATURES = (
    Feature(
        "click", "a1d87858abd77fa8e3ffc204670ccd75b96c4781",
        {"src/click/termui.py": "click/termui.py"}, "behavior_inversion",
        "Review Click edit filename handling after commit a1d8785.",
        "click.edit treats a single pathlib.Path filename as one file path.",
        "edit checks for both str and os.PathLike before deciding whether to wrap filename in a one-item tuple.",
        "click.edit treats a pathlib.Path filename as a generic iterable of path components.",
        "The updated type check recognizes os.PathLike and wraps the Path object as a single filename.",
    ),
    Feature(
        "click", "a6256bfb5971d5e58585fe7b6c656134e1ade5a4",
        {"src/click/_termui_impl.py": "click/_termui_impl.py"}, "incorrect_call_relationship",
        "Review Click temporary pager invocation after commit a6256bf.",
        "_tempfilepager forwards parsed PAGER command parameters to subprocess.call.",
        "The subprocess argument list is [str(cmd_path), *cmd_params, f.name].",
        "_tempfilepager invokes the pager executable with only the temporary filename.",
        "The updated subprocess call inserts cmd_params before the temporary filename.",
    ),
    Feature(
        "click", "1f9cd54f686eb343cec714230ad825ce972739ab",
        {"src/click/_termui_impl.py": "click/_termui_impl.py"}, "causal_mislocalization",
        "Review Click temporary pager cleanup after commit 1f9cd54.",
        "_tempfilepager closes the temporary file before unlinking it.",
        "The finally block calls f.close() and then os.unlink(f.name).",
        "_tempfilepager unlinks the temporary file while it is still open.",
        "The updated cleanup explicitly closes f before calling os.unlink.",
    ),
    Feature(
        "click", "047adef258fc25566163ffc3efd14effc0ef7352",
        {"src/click/core.py": "click/core.py"}, "stale_evidence",
        "Review Click help-option selection after commit 047adef.",
        "get_help_option_names preserves the declaration order of help option names.",
        "The implementation uses dict.fromkeys and pop, whose iteration order follows declaration order.",
        "get_help_option_names still converts help option names to an unordered set.",
        "The set-based implementation was replaced by an insertion-ordered dict.",
    ),
    Feature(
        "click", "71f2bafa541e7f798834e74076786ff4281ac83e",
        {"src/click/_compat.py": "click/_compat.py"}, "missing_guard",
        "Review Click ANSI stripping after commit 71f2baf.",
        "Click's ANSI matcher accepts parameter bytes, intermediate bytes, and a final byte in the ECMA-48 ranges.",
        "_ansi_re is compiled from the pattern \\033\\[[0-?]*[ -/]*[@-~].",
        "Click's ANSI matcher only recognizes numeric parameters separated by semicolons.",
        "The updated regex uses the broader ECMA-48 byte ranges rather than the older numeric-only form.",
    ),
    Feature(
        "pluggy", "20d8143f127a4d7526dbbea441857b4b80ec8bdd",
        {"src/pluggy/_hooks.py": "pluggy/_hooks.py"}, "behavior_inversion",
        "Review pluggy hook implementation removal after commit 20d8143.",
        "HookCaller._remove_plugin removes every hook implementation registered by the plugin.",
        "It filters _hookimpls and replaces the list with all entries whose plugin differs.",
        "HookCaller._remove_plugin returns after deleting the first matching hook implementation.",
        "The updated implementation performs a full list filter and has no early return after one match.",
    ),
    Feature(
        "pluggy", "dd20a85e38af556e1c818b03391eab1480438e0c",
        {"src/pluggy/_hooks.py": "pluggy/_hooks.py"}, "missing_guard",
        "Review pluggy legacy hookspec method handling after commit dd20a85.",
        "varnames emits a FutureWarning for a class-like method missing self when legacy_noself is enabled.",
        "The legacy_noself branch calls warnings.warn with FutureWarning when the first argument is not an implicit name.",
        "varnames silently accepts a legacy hookspec method missing self.",
        "The updated legacy_noself branch warns instead of silently accepting that shape.",
    ),
    Feature(
        "pluggy", "53eeddf56e09fede281ac5f3cd6a6b5a83e1799a",
        {"src/pluggy/_manager.py": "pluggy/_manager.py", "src/pluggy/_compat.py": "pluggy/_compat.py"},
        "incorrect_call_relationship", "Review pluggy distribution listing after commit 53eeddf.",
        "list_plugin_distinfo wraps stored distributions with DistFacade before returning them.",
        "The method returns a comprehension containing DistFacade(dist) for each stored distribution.",
        "list_plugin_distinfo returns the raw importlib.metadata distributions stored by the manager.",
        "Raw distributions are returned by list_plugin_distributions; list_plugin_distinfo applies DistFacade.",
    ),
    Feature(
        "pluggy", "0b7790eb2adf436c6df39c9a2256aa8a31ba3893",
        {"src/pluggy/_hooks.py": "pluggy/_hooks.py"}, "causal_mislocalization",
        "Review pluggy bound-method argument discovery after commit 0b7790e.",
        "varnames can strip an implicit self argument from a bound method even when its qualname has no dot.",
        "It records inspect.ismethod(func) in is_bound before unwrapping and uses is_bound in the stripping condition.",
        "varnames relies only on a dot in __qualname__ to strip a bound method's self argument.",
        "The updated condition also uses the separately captured is_bound flag.",
    ),
    Feature(
        "pluggy", "c4e254ca53d02f969c81586dc50c83cc8bb3dea9",
        {"src/pluggy/_hooks.py": "pluggy/_hooks.py"}, "stale_evidence",
        "Review pluggy parameter discovery after commit c4e254c.",
        "varnames derives positional parameter names directly from the callable's code object.",
        "It reads func.__code__.co_varnames up to co_argcount and partitions defaults.",
        "varnames still calls inspect.signature to discover positional parameters.",
        "The updated implementation reads __code__ and __defaults__ instead of inspect.signature.",
    ),
    Feature(
        "attrs", "48b8611c27779811d161200e17de8da24aae7feb",
        {"src/attr/_make.py": "attr/_make.py"}, "behavior_inversion",
        "Review attrs.fields input handling after commit 48b8611.",
        "attrs.fields accepts an attrs instance and introspects its type.",
        "For a non-type whose type has __attrs_attrs__, fields returns fields(type_).",
        "attrs.fields rejects every non-class input with TypeError.",
        "The updated implementation accepts non-class inputs when their type is an attrs class.",
    ),
    Feature(
        "attrs", "4b5b295bb815bf845fa3570bf63781a88212db40",
        {"src/attr/_make.py": "attr/_make.py"}, "missing_guard",
        "Review attrs generator on_setattr hooks after commit 4b5b295.",
        "attrs raises RuntimeError when a generator on_setattr hook yields more than once.",
        "After assigning the first yielded value, __setattr__ advances again, closes the generator, and raises RuntimeError if it yields.",
        "attrs accepts every value yielded by a generator on_setattr hook without limiting the number of yields.",
        "The updated implementation explicitly rejects a second yield.",
    ),
    Feature(
        "attrs", "5aa76a4450c311d87eda43946ec0ecd743572649",
        {"src/attr/validators.py": "attr/validators.py"}, "incorrect_call_relationship",
        "Review the attrs ne validator after commit 5aa76a4.",
        "attrs.validators.ne constructs _NumberValidator with operator.ne.",
        "ne returns _NumberValidator(val, '!=', operator.ne).",
        "attrs.validators.ne delegates comparison to operator.eq.",
        "The new validator passes operator.ne, not operator.eq.",
    ),
    Feature(
        "attrs", "f53fc5440d7f86aac4328aec7a563eb48634177f",
        {"src/attr/_make.py": "attr/_make.py"}, "causal_mislocalization",
        "Review attrs __replace__ generation after commit f53fc54.",
        "_ClassBuilder.add_replace attaches generated method dunders to a local __replace__ proxy.",
        "add_replace defines a local proxy around evolve and passes that proxy to _add_method_dunders.",
        "_ClassBuilder.add_replace attaches generated method dunders directly to the global evolve function.",
        "The updated implementation passes the local __replace__ proxy rather than evolve itself.",
    ),
    Feature(
        "attrs", "97f8d175656bc03c373a1c9038048a4d312c307c",
        {"src/attr/_make.py": "attr/_make.py"}, "stale_evidence",
        "Review attrs ClassVar forward-reference detection after commit 97f8d17.",
        "_is_class_var unwraps an annotation's __forward_arg__ before converting it to text.",
        "The first assignment replaces annot with getattr(annot, '__forward_arg__', annot).",
        "_is_class_var immediately converts the annotation object itself to text.",
        "The updated code first extracts __forward_arg__ when present.",
    ),
    Feature(
        "more-itertools", "069b30002a985c02f1ab18409290a699fd649376",
        {"more_itertools/more.py": "more_itertools/more.py"}, "behavior_inversion",
        "Review numeric_range equality after commit 069b300.",
        "Two one-element numeric_range objects can be equal even when their step values differ.",
        "After confirming equal length and start, __eq__ returns True immediately when length is one.",
        "numeric_range equality always requires equal step values for nonempty ranges.",
        "The updated length-one branch returns True without comparing steps.",
    ),
    Feature(
        "more-itertools", "0e6acdf9b60765ecf9634d6f5c132ac1bebc616b",
        {"more_itertools/more.py": "more_itertools/more.py"}, "missing_guard",
        "Review more-itertools chunked validation after commit 0e6acdf.",
        "chunked raises ValueError when n is a negative integer.",
        "The function begins with a guard for n is not None and n < 0.",
        "chunked has no explicit guard against a negative n.",
        "The updated implementation checks for negative n before creating its iterator.",
    ),
    Feature(
        "more-itertools", "237388cc3220bdc7cfacc6f766304a49b42fb8e7",
        {"more_itertools/more.py": "more_itertools/more.py"}, "incorrect_call_relationship",
        "Review nth_permutation index calculation after commit 237388c.",
        "nth_permutation computes its index digits without calling math.factorial.",
        "The factorial import and factorial-based q expression were removed; q starts as index.",
        "nth_permutation still calls factorial(n) when r is smaller than n.",
        "The updated code no longer imports or calls factorial.",
    ),
    Feature(
        "more-itertools", "d992be0de9383ddcaae3a24866a2d96b52132b07",
        {"more_itertools/recipes.py": "more_itertools/recipes.py"}, "causal_mislocalization",
        "Review running_min stability after commit d992be0.",
        "_windowed_running_min keeps an earlier value when a later value compares equal.",
        "Its pruning loop retains the prior tail while tail_value <= value, preserving the earlier equal value.",
        "_windowed_running_min discards the earlier value whenever a later value compares equal.",
        "The updated <= condition stops pruning on equality.",
    ),
    Feature(
        "more-itertools", "958990e22c4ab6daf434d89cf2b86d7a4a7a9e3c",
        {"more_itertools/more.py": "more_itertools/more.py"}, "stale_evidence",
        "Review more-itertools sliced validation after commit 958990e.",
        "sliced raises ValueError for a negative slice size.",
        "The function now starts with if n < 0: raise ValueError.",
        "sliced still passes a negative slice size directly into count.",
        "The new negative-size guard runs before the count-based iterator is created.",
    ),
    Feature(
        "requests", "fd628095d7b9ddbf3e987d8a4bf0e6062768916f",
        {"src/requests/adapters.py": "requests/adapters.py"}, "behavior_inversion",
        "Review Requests adapter path handling after commit fd62809.",
        "HTTPAdapter.request_url preserves multiple leading slashes in request.path_url for a direct request.",
        "request_url initializes url from request.path_url and no longer collapses a leading double slash.",
        "HTTPAdapter.request_url collapses multiple leading slashes in request.path_url to one slash.",
        "The slash-collapsing block was removed from the updated implementation.",
    ),
    Feature(
        "requests", "f0198e6dfc431a2293dc16e1b1e8fcddc910a7f3",
        {"src/requests/utils.py": "requests/utils.py"}, "missing_guard",
        "Review Requests Content-Type parsing after commit f0198e6.",
        "_parse_content_type_header ignores a nonempty parameter token that contains no equals sign.",
        "The loop only adds a parameter when param is nonempty and param.find('=') is not -1.",
        "_parse_content_type_header stores a parameter without an equals sign with the value True.",
        "The updated condition excludes malformed tokens instead of assigning True.",
    ),
    Feature(
        "requests", "6f205ff422bccd5e4c4fc0b64c5f3e7df5181db6",
        {"src/requests/models.py": "requests/models.py"}, "incorrect_call_relationship",
        "Review Requests multipart file-wrapper handling after commit 6f205ff.",
        "_encode_files calls read on a file wrapper when hasattr(wrapper, 'read') is true.",
        "The read branch accepts either _SupportsRead instances or objects for which hasattr(fp, 'read') succeeds.",
        "_encode_files calls read only when the wrapper passes the _SupportsRead isinstance check.",
        "The updated branch includes an alternative hasattr(fp, 'read') check.",
    ),
    Feature(
        "requests", "ef439eb779c1eba7cbdeeeb302b11e1e061b4b7d",
        {"src/requests/sessions.py": "requests/sessions.py"}, "causal_mislocalization",
        "Review Requests redirect history construction after commit ef439eb.",
        "resolve_redirects copies prior history into resp.history before appending resp to the local history list.",
        "Inside the loop, resp.history = hist[:] occurs immediately before hist.append(resp).",
        "resolve_redirects appends resp before copying history into resp.history.",
        "The updated order assigns the copy first, preventing resp from appearing in its own history.",
    ),
    Feature(
        "requests", "6404f345e562d962abe6700a1c357ec1e7e18232",
        {"src/requests/models.py": "requests/models.py"}, "stale_evidence",
        "Review Requests request-body stream detection after commit 6404f34.",
        "prepare_body treats data as iterable when isinstance(data, Iterable) or hasattr(data, '__iter__') succeeds.",
        "The is_iterable variable combines the protocol isinstance check with an __iter__ attribute check.",
        "prepare_body still relies exclusively on isinstance(data, Iterable) to detect streams.",
        "The updated implementation adds hasattr(data, '__iter__') as an alternative.",
    ),
)


def main() -> None:
    _require_sources()
    rows: list[dict[str, object]] = []
    number = 1
    for feature in FEATURES:
        rows.append(_case(number, feature, "SUPPORTED"))
        number += 1
        rows.append(_case(number, feature, "UNSUPPORTED"))
        number += 1

    CASES.parent.mkdir(parents=True, exist_ok=True)
    with CASES.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _require_sources() -> None:
    missing = [str(path) for path in SOURCES.values() if not (path / ".git").exists()]
    if missing:
        raise FileNotFoundError(
            "Missing source repositories. Follow the clone commands in "
            f"{ROOT / 'README.md'}. Missing: {missing}"
        )


def _case(number: int, feature: Feature, label: str) -> dict[str, object]:
    case_repo = REPOS / f"case_{number:03d}"
    _write_git_diff(feature.repo, feature.commit, tuple(feature.files), case_repo / "upstream.patch")

    supported = label == "SUPPORTED"
    return {
        "case_id": f"externalpr50_{number:03d}_{feature.family}_{label.lower()}",
        "repo_path": str(case_repo.relative_to(PROJECT)).replace("\\", "/"),
        "task_description": feature.task,
        "claim": feature.supported_claim if supported else feature.unsupported_claim,
        "ground_truth": label,
        "ground_truth_evidence": (
            feature.supported_evidence if supported else feature.unsupported_evidence
        ),
        "validation_command": ["python", "-m", "unittest", "discover"],
        "claim_family": feature.family,
        "source_repository": feature.repo,
        "source_commit": feature.commit,
    }


def _write_git_diff(repo: str, commit: str, sources: tuple[str, ...], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["git", "-C", str(SOURCES[repo]), "diff", f"{commit}^", commit, "--", *sources],
        check=True,
        capture_output=True,
        text=True,
    )
    if not completed.stdout.strip():
        raise RuntimeError(f"No source diff for {repo}@{commit}: {', '.join(sources)}")
    target.write_text(completed.stdout, encoding="utf-8")


if __name__ == "__main__":
    main()
