#!/usr/bin/env python3
"""
Package a validated skill into a .skill file (zip with .skill extension).
Validates first, then packages.
"""
import sys
import zipfile
from pathlib import Path
from validate import validate_skill


def package_skill(skill_dir: Path, output_dir: Path = None):
    """Package skill into .skill zip file."""
    if output_dir is None:
        output_dir = skill_dir.parent

    # Validate first
    is_valid, errors = validate_skill(skill_dir)
    if not is_valid:
        print("❌ Validation FAILED, cannot package:\n")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)

    print("✅ Validation passed, packaging...\n")

    skill_name = skill_dir.name
    output_file = output_dir / f"{skill_name}.skill"

    # Create zip
    excluded = {"__pycache__", ".DS_Store", ".git", ".pyc"}
    with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(skill_dir.rglob("*")):
            if p.is_file():
                # Skip excluded patterns
                if any(part in excluded for part in p.parts):
                    continue
                # Check for symlinks
                if p.is_symlink():
                    print(f"❌ Symlink found: {p} (security restriction)")
                    sys.exit(1)
                # Archive name relative to skill_dir parent
                arcname = p.relative_to(skill_dir.parent)
                zf.write(p, arcname)
                print(f"  📦 {arcname}")

    size_kb = output_file.stat().st_size / 1024
    print(f"\n✅ Packaged: {output_file} ({size_kb:.1f} KB)")
    return output_file


def main():
    if len(sys.argv) < 2:
        print("Usage: package.py <skill_dir> [output_dir]")
        sys.exit(1)

    skill_dir = Path(sys.argv[1]).resolve()
    output_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None

    package_skill(skill_dir, output_dir)


if __name__ == "__main__":
    main()
