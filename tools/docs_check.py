#!/usr/bin/env python3
"""
docs_check.py - Check Markdown files for SPEC-06 compliance

Checks that every Markdown file under docs/**/*.md and README.md has:
  - <a id="english"> and <a id="japanese"> anchors
  - Jump line with [English](#english) and [日本語](#japanese)
  - Version / 版 line in header
  - No relative links to non-existent files

Exit code 0 if all checks pass, 1 if any fail.
"""

import sys
import os
import re
from pathlib import Path


def find_md_files(docs_dir: str) -> list[Path]:
    """Find all Markdown files under docs/ and root README.md"""
    files = []
    
    # All .md files under docs/
    docs_path = Path(docs_dir)
    if docs_path.exists():
        for md_file in docs_path.rglob("*.md"):
            # Every document under docs/ is checked, except legacy guide text kept
            # verbatim for history: *.legacy.md and sub-documents inside docs/guides/<x>/
            # other than that guide's README.md (SPEC-06 applies to new documents).
            parts = md_file.parts
            if md_file.name.endswith(".legacy.md"):
                continue
            if "guides" in parts and len(parts) > parts.index("guides") + 2 and md_file.name != "README.md":
                continue
            files.append(md_file)
    
    # Root README.md (but not docs/README.md)
    root_readme = Path("README.md")
    if root_readme.exists() and str(root_readme) != "docs/README.md":
        files.append(root_readme)
    
    return sorted(files)


def check_anchors(content: str, filepath: str) -> list[str]:
    """Check for required HTML anchors"""
    errors = []
    
    if '<a id="english">' not in content:
        errors.append(f"{filepath}: Missing <a id=\"english\"> anchor")
    if '<a id="japanese">' not in content:
        errors.append(f"{filepath}: Missing <a id=\"japanese\"> anchor")
    
    return errors


def check_jump_line(content: str, filepath: str) -> list[str]:
    """Check for Jump line with English and Japanese links"""
    errors = []
    
    # Look for Jump line pattern
    jump_pattern = r'\*\*Jump:?\*\*:?.*\[English\]\(#english\).*\[日本語\]\(#japanese\)'
    if not re.search(jump_pattern, content, re.IGNORECASE):
        errors.append(f"{filepath}: Missing Jump line with [English](#english) and [日本語](#japanese)")
    
    return errors


def check_version_line(content: str, filepath: str) -> list[str]:
    """Check for Version / 版 line"""
    errors = []
    
    # Look for Version line (can be in header or after ---)
    version_pattern = r'Version\s*/\s*版.*—'
    if not re.search(version_pattern, content, re.IGNORECASE):
        errors.append(f"{filepath}: Missing Version / 版 line")
    
    return errors


def check_relative_links(content: str, filepath: str) -> list[str]:
    """Check for relative links to non-existent files"""
    errors = []
    
    # Find all relative links (not starting with http, #, or /)
    # Pattern: [text](relative_path) or [text]: relative_path
    link_pattern = r'\[.*?\]\(([^)]+)\)'
    
    file_dir = Path(filepath).parent
    
    for match in re.finditer(link_pattern, content):
        link = match.group(1)
        
        # Skip if it has a fragment (#), starts with http, or is absolute
        if '#' in link or link.startswith('http://') or link.startswith('https://'):
            continue
        if link.startswith('/') or link.startswith('#'):
            continue
        
        # Resolve the relative path
        target_path = file_dir / link
        
        # Check if it exists (try with and without .md extension)
        if not target_path.exists() and not target_path.with_suffix('.md').exists():
            errors.append(f"{filepath}: Relative link to non-existent file: {link}")
    
    return errors


def check_file(filepath: Path) -> list[str]:
    """Run all checks on a single file"""
    errors = []
    
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return [f"{filepath}: Could not read file: {e}"]
    
    errors.extend(check_anchors(content, str(filepath)))
    errors.extend(check_jump_line(content, str(filepath)))
    errors.extend(check_version_line(content, str(filepath)))
    errors.extend(check_relative_links(content, str(filepath)))
    
    return errors


def main():
    """Main entry point"""
    # Check if we're in the right directory
    if not Path("docs").is_dir():
        print("Error: This script must be run from the repository root (where docs/ exists)", file=sys.stderr)
        sys.exit(1)
    
    md_files = find_md_files("docs")
    
    if not md_files:
        print("No Markdown files found to check.")
        sys.exit(0)
    
    all_errors = []
    
    for md_file in md_files:
        errors = check_file(md_file)
        all_errors.extend(errors)
    
    # Print report
    print("=" * 70)
    print("docs_check.py - SPEC-06 Documentation Compliance Check")
    print("=" * 70)
    
    if all_errors:
        print(f"\nFound {len(all_errors)} error(s) in {len(md_files)} file(s):\n")
        for error in all_errors:
            print(f"  • {error}")
        
        print("\n" + "=" * 70)
        print(f"FAILED: {len(all_errors)} error(s) found")
        print("=" * 70)
        sys.exit(1)
    else:
        print(f"\nAll {len(md_files)} file(s) passed SPEC-06 checks.")
        print("=" * 70)
        sys.exit(0)


if __name__ == "__main__":
    main()
