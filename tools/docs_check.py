#!/usr/bin/env python3
"""
docs_check.py - SPEC-06 §8 documentation checks for every tracked Markdown file.

Standard library only, Python 3.11+. Run from the repository root:

    python3 tools/docs_check.py [--all-warnings] [--root DIR]

Scope: every `*.md` that `git ls-files` reports, anywhere in the repository
(docs/, README.md, manifest/, installer/, docs/assets/, ...), except `site/`
(generated output). Each file is classified:

  full     SPEC-06 applies in full (new bilingual documents).
  pointer  the seven old-path pointer files kept for inbound links
           (Environment.md, SetupOsfOnEC2.md, Skelton/README.md, StorageAddon/README.md,
           ScreenExpansion/README.md, APIGuide/README.md, AdminRDMAddonGuide/README.md).
           They are short redirects, not bilingual documents, so only their relative
           links are checked and one of them must lead into docs/guides/.
  legacy   `*.legacy.md`: 2020-era guide text kept verbatim for history (SPEC-06 applies
           to new documents only). Skipped, listed in the summary.
  sample   Markdown inside docs/guides/<guide>/ other than that guide's README.md:
           sample code documentation copied with the legacy guides. Skipped, listed.

Checks on `full` files (failure => exit 1):
  - <a id="english"> and <a id="japanese"> anchors, and the Jump line
  - a Version / 版 line in the header
  - every relative link resolves; for `file.md#frag` the file must exist AND the
    fragment must be an <a id>/<a name> or a heading in that file; for `#frag` the
    anchor must exist in the same file
  - a ```toon block that declares its canonical JSON (a preceding line
    `<!-- canonical: path/to.json -->` or text like canonical: `path/to.json`)
    must point to an existing JSON file and every 40-hex SHA in the block must
    appear in that JSON

Warnings (printed, never fail; SPEC-06 says warning until M2):
  - a REF-01 glossary term used in the English half without a parenthetical note
    on its first occurrence. Files under docs/reviews/ are exempt from this
    warning: review records are kept verbatim (SPEC-06 §8).

Exit codes: 0 pass (warnings allowed); 1 any failure; 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2

GLOSSARY_PATH = Path("docs/reference/REF-01_Glossary.md")
GLOSSARY_EXEMPT_PREFIXES = ("docs/reviews/",)  # review records are kept verbatim (SPEC-06 §8)

POINTER_FILES: dict[str, str] = {
    "Environment.md": "old path of the environment guide; redirect to docs/guides/environment/",
    "SetupOsfOnEC2.md": "old path of the EC2 guide; redirect to docs/guides/ec2/",
    "Skelton/README.md": "old path of the skeleton add-on guide; redirect to docs/guides/skeleton/",
    "StorageAddon/README.md": "old path of the storage add-on guide; redirect to docs/guides/storage-addon/",
    "ScreenExpansion/README.md": "old path of the screen expansion guide; redirect to docs/guides/screen-expansion/",
    "APIGuide/README.md": "old path of the API guide; redirect to docs/guides/api/",
    "AdminRDMAddonGuide/README.md": "old path of the admin add-on guide; redirect to docs/guides/admin-addon/",
}

RE_FENCE = re.compile(r"^(\s*)(```+|~~~+)(.*)$")
RE_LINK = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
RE_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
RE_A_ID = re.compile(r"<a\s+(?:id|name)=\"([^\"]+)\"")
RE_ATTR_ID = re.compile(r"\{#([^}\s]+)\}")
RE_SHA40 = re.compile(r"\b[0-9a-f]{40}\b")
RE_CANONICAL = re.compile(r"canonical:\s*`?([A-Za-z0-9_./-]+\.json)`?")
RE_JUMP = re.compile(r"\*\*Jump:?\*\*:?.*\[English\]\(#english\).*\[日本語\]\(#japanese\)", re.IGNORECASE)
RE_VERSION = re.compile(r"Version\s*/\s*版.*—", re.IGNORECASE)


@dataclass
class FileResult:
    path: str
    category: str
    reason: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- scope

def git_tracked_markdown(root: Path) -> list[str]:
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--", "*.md", "**/*.md"], cwd=root,
                             check=True, capture_output=True).stdout
        files = sorted({p.decode("utf-8") for p in out.split(b"\0") if p})
    except (subprocess.CalledProcessError, FileNotFoundError):
        files = sorted(str(p.relative_to(root)) for p in root.rglob("*.md") if ".git" not in p.parts)
    return [f for f in files if not f.startswith("site/")]


def classify(rel_path: str) -> tuple[str, str]:
    """Return (category, reason) for a tracked Markdown path."""
    if rel_path in POINTER_FILES:
        return "pointer", POINTER_FILES[rel_path]
    if rel_path.endswith(".legacy.md"):
        return "legacy", "legacy guide text kept verbatim for history (SPEC-06 applies to new documents)"
    parts = rel_path.split("/")
    if len(parts) >= 4 and parts[:2] == ["docs", "guides"] and parts[-1] != "README.md":
        return "sample", "sample code documentation inside docs/guides/<guide>/ copied with the legacy guide"
    if len(parts) == 4 and parts[:2] == ["docs", "guides"] and parts[-1] == "README.md":
        return "full", ""
    if len(parts) >= 5 and parts[:2] == ["docs", "guides"]:
        return "sample", "sample code documentation inside docs/guides/<guide>/ copied with the legacy guide"
    return "full", ""


# --------------------------------------------------------------------------- markdown helpers

def strip_code(content: str) -> str:
    """Blank out fenced code blocks and inline code so their text is not scanned for links/terms."""
    out: list[str] = []
    fence: str | None = None
    for line in content.splitlines():
        m = RE_FENCE.match(line)
        if fence is None and m:
            fence = m.group(2)[0]
            out.append("")
            continue
        if fence is not None:
            if m and m.group(2)[0] == fence and not m.group(3).strip():
                fence = None
            out.append("")
            continue
        out.append(re.sub(r"`[^`]*`", "``", line))
    return "\n".join(out)


def github_slug(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors_in(content: str) -> set[str]:
    """All ids a `#fragment` may legally point to inside a Markdown file."""
    ids: set[str] = set(RE_A_ID.findall(content))
    ids.update(RE_ATTR_ID.findall(content))
    counts: dict[str, int] = {}
    for line in strip_code(content).splitlines():
        m = RE_HEADING.match(line)
        if not m:
            continue
        heading = re.sub(r"\{#[^}]+\}\s*$", "", m.group(1))
        slug = github_slug(heading)
        n = counts.get(slug, 0)
        counts[slug] = n + 1
        ids.add(slug if n == 0 else f"{slug}-{n}")
        ids.add(heading.strip())
    return ids


def fenced_blocks(content: str, lang: str) -> list[tuple[int, str, list[str]]]:
    """Return (start_line_no, block_text, up_to_5_preceding_lines) for ```<lang> blocks."""
    blocks: list[tuple[int, str, list[str]]] = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        m = RE_FENCE.match(lines[i])
        if m:
            fence_char = m.group(2)[0]
            info = m.group(3).strip().split()[0].lower() if m.group(3).strip() else ""
            start = i
            j = i + 1
            while j < len(lines):
                mm = RE_FENCE.match(lines[j])
                if mm and mm.group(2)[0] == fence_char and not mm.group(3).strip():
                    break
                j += 1
            if info == lang:
                blocks.append((start + 1, "\n".join(lines[i + 1:j]), lines[max(0, i - 5):i]))
            i = j + 1
            continue
        i += 1
    return blocks


# --------------------------------------------------------------------------- checks

def check_anchors(content: str, rel: str) -> list[str]:
    errors = []
    if '<a id="english">' not in content:
        errors.append(f"{rel}: missing <a id=\"english\"> anchor")
    if '<a id="japanese">' not in content:
        errors.append(f"{rel}: missing <a id=\"japanese\"> anchor")
    return errors


def check_jump_line(content: str, rel: str) -> list[str]:
    if not RE_JUMP.search(content):
        return [f"{rel}: missing Jump line with [English](#english) and [日本語](#japanese)"]
    return []


def check_version_line(content: str, rel: str) -> list[str]:
    if not RE_VERSION.search(content):
        return [f"{rel}: missing Version / 版 line"]
    return []


def check_links(content: str, rel: str, root: Path) -> list[str]:
    """Every relative link resolves; fragments must exist in the target (or same) file."""
    errors: list[str] = []
    file_path = root / rel
    file_dir = file_path.parent
    own_anchors: set[str] | None = None
    for m in RE_LINK.finditer(strip_code(content)):
        link = m.group(1)
        if re.match(r"^[a-z][a-z0-9+.-]*:", link):  # http:, https:, mailto:, ...
            continue
        if link.startswith("/"):
            errors.append(f"{rel}: absolute link is not allowed (use a relative link): {link}")
            continue
        file_part, _, fragment = link.partition("#")
        if file_part == "":
            if own_anchors is None:
                own_anchors = anchors_in(content)
            if fragment and fragment not in own_anchors:
                errors.append(f"{rel}: same-file anchor not found: #{fragment}")
            continue
        target = (file_dir / file_part)
        if not target.exists() and not target.with_suffix(".md").exists():
            errors.append(f"{rel}: relative link to non-existent file: {link}")
            continue
        if not target.exists():
            target = target.with_suffix(".md")
        if fragment and target.is_file() and target.suffix.lower() == ".md":
            try:
                target_content = target.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                errors.append(f"{rel}: cannot read link target {file_part}")
                continue
            if fragment not in anchors_in(target_content):
                errors.append(f"{rel}: anchor #{fragment} not found in {file_part}")
    return errors


def check_toon_parity(content: str, rel: str, root: Path) -> list[str]:
    """A ```toon block with a declared canonical JSON: the JSON exists and contains every SHA."""
    errors: list[str] = []
    file_dir = (root / rel).parent
    for start, block, preceding in fenced_blocks(content, "toon"):
        decl = None
        for line in reversed(preceding):
            mm = RE_CANONICAL.search(line)
            if mm:
                decl = mm.group(1)
                break
        if decl is None:
            continue
        candidates = [file_dir / decl, root / decl]
        json_path = next((c for c in candidates if c.is_file()), None)
        if json_path is None:
            errors.append(f"{rel}:{start}: toon block declares canonical JSON {decl} which does not exist")
            continue
        try:
            json_text = json_path.read_text(encoding="utf-8")
            json.loads(json_text)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
            errors.append(f"{rel}:{start}: canonical JSON {decl} is unreadable or invalid: {e}")
            continue
        for sha in sorted(set(RE_SHA40.findall(block))):
            if sha not in json_text:
                errors.append(f"{rel}:{start}: toon block SHA {sha} is not in canonical JSON {decl} (stale excerpt)")
    return errors


def load_glossary_terms(root: Path) -> list[str]:
    """Term column of the English table in REF-01 (first table cell of each row)."""
    path = root / GLOSSARY_PATH
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    start = text.find('<a id="english">')
    end = text.find('<a id="japanese">')
    english = text[start:end] if start != -1 and end != -1 else text
    terms: list[str] = []
    for line in english.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or cells[0] in ("Term", "") or set(cells[0]) <= {"-", ":"}:
            continue
        cell = re.sub(r"`", "", cells[0])
        for piece in re.split(r"\s*/\s*|\(|\)", cell):
            piece = piece.strip()
            if len(piece) >= 2 and re.search(r"[A-Za-z]", piece) and piece not in terms:
                terms.append(piece)
    return terms


def check_glossary_terms(content: str, rel: str, terms: list[str]) -> list[str]:
    """WARNING: a glossary term whose first use in the English half has no parenthetical note."""
    warnings: list[str] = []
    if not terms:
        return warnings
    start = content.find('<a id="english">')
    end = content.find('<a id="japanese">')
    if start == -1:
        return warnings
    english = strip_code(content[start:end if end != -1 else len(content)])
    for term in terms:
        pattern = re.compile(r"(?<![\w-])" + re.escape(term) + r"(?![\w-])")
        m = pattern.search(english)
        if not m:
            continue
        line_start = english.rfind("\n", 0, m.start()) + 1
        line_end = english.find("\n", m.end())
        line = english[line_start:line_end if line_end != -1 else len(english)]
        after = english[m.end():m.end() + 200]
        before = english[max(0, m.start() - 2):m.start()]
        has_note = (
            re.match(r"\s*\(", after) is not None
            or re.match(r"[*_]*\s*\(", after) is not None
            or "(" in before
            or re.search(r"\((?:[^()]|\([^()]*\))*\b" + re.escape(term) + r"\b", line) is not None
            or "[" in before
            or "|" in line[:10]  # inside a table row (glossary-style tables explain in place)
        )
        if not has_note:
            lineno = content[:start].count("\n") + english[:m.start()].count("\n") + 1
            warnings.append(f"{rel}:{lineno}: glossary term '{term}' first used without a parenthetical note (REF-01)")
    return warnings


def glossary_check_applies(rel: str) -> bool:
    """The glossary-note warning skips REF-01 itself and review records (docs/reviews/, kept verbatim)."""
    if rel == str(GLOSSARY_PATH):
        return False
    return not rel.startswith(GLOSSARY_EXEMPT_PREFIXES)


def check_pointer_file(content: str, rel: str, root: Path) -> list[str]:
    errors = check_links(content, rel, root)
    if not re.search(r"\]\(\s*<?[^)\s>]*docs/guides/", content):
        errors.append(f"{rel}: pointer file must link to its new location under docs/guides/")
    return errors


# --------------------------------------------------------------------------- driver

def check_file(rel: str, root: Path, terms: list[str]) -> FileResult:
    category, reason = classify(rel)
    result = FileResult(path=rel, category=category, reason=reason)
    if category in ("legacy", "sample"):
        return result
    try:
        content = (root / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        result.errors.append(f"{rel}: could not read file: {e}")
        return result
    if category == "pointer":
        result.errors.extend(check_pointer_file(content, rel, root))
        return result
    result.errors.extend(check_anchors(content, rel))
    result.errors.extend(check_jump_line(content, rel))
    result.errors.extend(check_version_line(content, rel))
    result.errors.extend(check_links(content, rel, root))
    result.errors.extend(check_toon_parity(content, rel, root))
    if glossary_check_applies(rel):
        result.warnings.extend(check_glossary_terms(content, rel, terms))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="docs_check.py",
        description="SPEC-06 §8 checks over every tracked Markdown file.",
        epilog="Exit codes: 0 pass (warnings allowed); 1 failure; 2 usage error.",
    )
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    parser.add_argument("--all-warnings", action="store_true", help="print every glossary warning (default: first 40)")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if not (root / "docs").is_dir():
        print("Error: run from the repository root (where docs/ exists)", file=sys.stderr)
        return EXIT_USAGE

    files = git_tracked_markdown(root)
    terms = load_glossary_terms(root)
    results = [check_file(rel, root, terms) for rel in files]

    print("=" * 70)
    print("docs_check.py - SPEC-06 §8 documentation checks")
    print("=" * 70)
    by_cat: dict[str, list[FileResult]] = {}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)
    print(f"\nTracked Markdown files: {len(results)} "
          f"(full {len(by_cat.get('full', []))}, pointer {len(by_cat.get('pointer', []))}, "
          f"legacy {len(by_cat.get('legacy', []))}, sample {len(by_cat.get('sample', []))})")
    skipped = by_cat.get("legacy", []) + by_cat.get("sample", [])
    if skipped:
        print("\nExempt from SPEC-06 (documented exceptions):")
        for r in sorted(skipped, key=lambda r: r.path):
            print(f"  ~ {r.path}: {r.reason}")
    pointers = by_cat.get("pointer", [])
    if pointers:
        print("\nPointer files (links to new location checked only):")
        for r in pointers:
            print(f"  > {r.path}: {r.reason}")
    print(f"\nGlossary terms loaded from {GLOSSARY_PATH}: {len(terms)}")

    errors = [e for r in results for e in r.errors]
    warnings = [w for r in results for w in r.warnings]
    if warnings:
        print(f"\n{len(warnings)} WARNING(s) (glossary first-use notes; not failing until M2):")
        shown = warnings if args.all_warnings else warnings[:40]
        for w in shown:
            print(f"  WARNING: {w}")
        if len(shown) < len(warnings):
            print(f"  ... and {len(warnings) - len(shown)} more (use --all-warnings)")
    print("\n" + "=" * 70)
    if errors:
        print(f"Found {len(errors)} error(s):\n")
        for e in errors:
            print(f"  - {e}")
        print("\n" + "=" * 70)
        print(f"FAILED: {len(errors)} error(s) in {len(results)} file(s)")
        print("=" * 70)
        return EXIT_FAIL
    checked = len(by_cat.get("full", [])) + len(pointers)
    print(f"PASSED: {checked} file(s) checked, {len(skipped)} exempt, {len(warnings)} warning(s)")
    print("=" * 70)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
