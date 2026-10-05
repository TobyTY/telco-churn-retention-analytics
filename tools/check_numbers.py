"""Fail the build if a published number cannot be traced to a facts.json value.

Every number in the generated READMEs, summaries, dashboards and resume must be a
rounding of some value in one of the facts files (optionally scaled by 100, 1e-3,
1e-6 for %, k and M). Years, dates, small structural integers (0-10) and an
explicit per-project allowlist are exempt.

Usage:
    python tools/check_numbers.py --facts reports/facts.json --files README.md reports/*.md
    python tools/check_numbers.py --facts a.json b.json --allow tools/number_allowlist.txt --files x.md y.pdf
"""
from __future__ import annotations

import argparse
import glob
import html
import json
import math
import re
import subprocess
import sys
from pathlib import Path

NUM_RE = re.compile(r"(?<![\w.])[-−]?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![\w])|(?<![\w.])[-−]?\d+(?:\.\d+)?")
SCALES = (1.0, 100.0, 1e-3, 1e-6, 1e-9)


def flatten_numbers(obj) -> list[float]:
    out: list[float] = []
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        if math.isfinite(obj):
            out.append(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(flatten_numbers(v))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out.extend(flatten_numbers(v))
    return out


def strip_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)          # fenced code
    text = re.sub(r"`[^`\n]*`", " ", text)                       # inline code
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)            # images
    text = re.sub(r"\]\([^)]*\)", "] ", text)                    # link targets
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    return text


def strip_html(text: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(text)


def strip_noise(text: str) -> str:
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\b[\w.-]+\.(?:com|io|org|edu|in|md|html|png|csv|json|xlsx|py|sql|dax|ipynb|pdf|tex|txt)\S*", " ", text)
    text = re.sub(r"\b[\w.+-]+@[\w-]+\.[\w.]+", " ", text)            # emails
    text = re.sub(r"\b\d{4}-\d{2}(?:-\d{2})?(?:[ T]\d{2}:\d{2}(?::\d{2})?)?\b", " ", text)  # ISO dates
    text = re.sub(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", " ", text)
    text = re.sub(r"(?m)^\s*\d+[.)]\s", " ", text)                  # list ordinals
    text = re.sub(r"(?m)^#+\s*\d+[.)]?", " ", text)                  # numbered headings
    text = re.sub(r"\b(?:Q[1-4]|H[12]|P[0-9]|L[1-9]|R[12]|F1|PR-AUC|ROC-AUC|80/20|24/7|B2B|B2C|E2E|3D|2D|M[1-9])\b", " ", text)
    text = re.sub(r"\b[A-Za-z]+\d+[A-Za-z0-9]*\b", " ", text)     # identifiers like py312, k8s
    return text


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        res = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, encoding="utf-8")
        if res.returncode != 0:
            raise RuntimeError(f"pdftotext failed on {path}: {res.stderr}")
        return res.stdout
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".html", ".htm"}:
        return strip_html(raw)
    return strip_markdown(raw)


def is_traceable(token: str, values: list[float], allow: set[float]) -> bool:
    clean = token.replace(",", "").replace("−", "-")
    t = float(clean)
    decimals = len(clean.split(".")[1]) if "." in clean else 0
    if t in allow or abs(t) in allow:
        return True
    if t.is_integer() and abs(t) <= 10:   # counts and ordinals such as '3 actions', 'CC BY 4.0'
        return True
    if decimals == 0 and 1990 <= t <= 2035:
        return True
    tol = 0.5 * 10 ** (-decimals) + 1e-9
    for v in values:
        for s in SCALES:
            c = v * s
            if abs(abs(c) - abs(t)) <= tol:
                return True
    return False


def check(files: list[Path], values: list[float], allow: set[float]) -> list[str]:
    problems: list[str] = []
    for f in files:
        text = strip_noise(extract_text(f))
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in NUM_RE.finditer(line):
                tok = m.group(0)
                if not is_traceable(tok, values, allow):
                    problems.append(f"{f}:{lineno}: untraceable number {tok!r} in: {line.strip()[:140]}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--facts", nargs="+", required=True)
    ap.add_argument("--files", nargs="+", required=True)
    ap.add_argument("--allow", nargs="*", default=[], help="text files with one allowed number per line")
    args = ap.parse_args(argv)

    values: list[float] = []
    for fp in args.facts:
        values.extend(flatten_numbers(json.loads(Path(fp).read_text(encoding="utf-8"))))
    allow: set[float] = set()
    for ap_ in args.allow:
        for line in Path(ap_).read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if line:
                allow.add(float(line))

    files: list[Path] = []
    for pattern in args.files:
        hits = sorted(glob.glob(pattern, recursive=True))
        files.extend(Path(h) for h in (hits or [pattern]))
    missing = [str(f) for f in files if not f.exists()]
    if missing:
        print("check_numbers: missing files:", ", ".join(missing))
        return 2

    problems = check(files, values, allow)
    if problems:
        print("\n".join(problems))
        print(f"check_numbers: FAIL - {len(problems)} untraceable number(s) across {len(files)} file(s)")
        return 1
    print(f"check_numbers: OK - {len(files)} file(s), every number traces to {len(args.facts)} facts file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
