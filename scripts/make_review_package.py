"""Build the anonymous replication package for double-anonymous review.

Takes the committed tree (not the working directory, so nothing uncommitted or
ignored can leak in), leaves out the files that name the authors or link to
their sites, rewrites the two lines that name them inside code and licence,
adds a reviewer README, and then refuses to finish if any identifying string
is still present anywhere in the package.

    python scripts/make_review_package.py --output evar-review-package.zip
"""

from __future__ import annotations

import argparse
import io
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Paths that identify the authors or exist only for the public project.
EXCLUDE = (
    "site/",
    ".github/",
    "CITATION.cff",
    ".zenodo.json",
    "PAPER.md",
    "paper/arxiv/README.md",
    "scripts/make_review_package.py",
    "tests/test_review_package.py",
)

# (path, pattern, replacement) for identifying lines that must stay in the package.
REWRITE = (
    ("LICENSE", r"Copyright \(c\) (\d{4}) .+", r"Copyright (c) \1 Anonymous Authors"),
    ("evar/model_backend.py", r"https://github\.com/kishormorol/evar", "https://anonymous.invalid/evar"),
)

IDENTIFYING = re.compile(r"[Kk]ishor|[Mm]orol|kishormorol|/Users/kishormorol|elitelab|chatgpt\.site|evar-research")

REVIEWER_README = """# Replication package (anonymous, for review)

Everything behind the paper's numbers: evaluator, prompts, configs, frozen
benchmark snapshots, canonical results and transcripts with their manifests,
judge-free audit reports, analysis scripts, and the preregistered expansion.

Requires Python 3.11 or later. No third-party packages are needed to run the
tests or regenerate the reported summaries.

## Tests

    python -m unittest discover -s tests

## Regenerate the reported summaries without any model call

The 1,200-attempt auditability summary (all four canonical run indices):

    PYTHONPATH=. python scripts/report_auditability.py \\
      --index benchmarks/external_pr_50/run_index.json \\
      --index benchmarks/human_pr_20/run_index.json \\
      --index benchmarks/human_pr_20/model_extension_run_index.json \\
      --index benchmarks/human_pr_20/cross_provider_run_index.json \\
      --output /tmp/auditability.json

Compare with `benchmarks/human_pr_20/auditability_summary.json`.

The same-row gate replay (388 completed EVAR-Hard decisions): pass every
EVAR-Hard result file listed in those four run indices as `--input`:

    PYTHONPATH=. python scripts/report_gate_ablation.py --input RESULT.jsonl [--input ...] --output /tmp/gate.json

Compare with `benchmarks/human_pr_20/gate_replay_ablation.json`.

The cross-provider report and its audit:

    PYTHONPATH=. python scripts/report_human_pr_20_cross_provider.py
    PYTHONPATH=. python scripts/audit_human_pr_20_cross_provider.py

## Model-backed reproduction

    python -m evar.preflight --config CONFIG --cases CASES
    python -m evar.run --protocol PROTOCOL --cases CASES --config CONFIG --output-dir RESULTS

This needs API credentials (see `.env.example`) and reproduces outcomes, not
bytes: provider inference is not guaranteed deterministic.
"""


def committed_tree(ref: str):
    """(path, bytes) for every file in `ref`, read with one `git archive` call."""
    tar = subprocess.run(["git", "archive", "--format=tar", ref], cwd=ROOT, check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        for member in t.getmembers():
            if member.isfile():
                yield member.name, t.extractfile(member).read()


def excluded(path: str) -> bool:
    return any(path == e or (e.endswith("/") and path.startswith(e)) for e in EXCLUDE)


def build(ref: str, output: Path, prefix: str = "evar-review-package") -> list[str]:
    """Write the package; return any identifying hits (empty when clean)."""
    hits: list[str] = []
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for path, data in committed_tree(ref):
            if excluded(path):
                continue
            for rpath, pattern, repl in REWRITE:
                if path == rpath:
                    text, n = re.subn(pattern, repl, data.decode("utf-8"))
                    if n == 0:
                        hits.append(f"{path}: expected an identifying line to rewrite and found none")
                    data = text.encode("utf-8")
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = data.decode("latin-1")
            for m in IDENTIFYING.finditer(text):
                hits.append(f"{path}: {text[max(0, m.start() - 30):m.end() + 30]!r}")
            z.writestr(f"{prefix}/{path}", data)
        z.writestr(f"{prefix}/README_REVIEWERS.md", REVIEWER_README)
    if not hits:
        output.write_bytes(buf.getvalue())
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ref", default="HEAD", help="the commit to package (default HEAD)")
    args = parser.parse_args(argv)
    hits = build(args.ref, args.output)
    if hits:
        print("Refusing to write the package; identifying strings remain:", file=sys.stderr)
        for h in hits:
            print(f"  {h}", file=sys.stderr)
        return 1
    print(f"{args.output} ({args.output.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
