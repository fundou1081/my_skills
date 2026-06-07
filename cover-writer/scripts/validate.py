#!/usr/bin/env python3
"""
Simple validator for AgentSkills spec.
(Same as better-act-skill/scripts/validate.py, copied for self-containment)
"""
import sys
import re
import yaml
from pathlib import Path


def validate_skill(skill_dir: Path) -> tuple[bool, list[str]]:
    """Returns (is_valid, errors)."""
    errors = []

    # 1. SKILL.md exists
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        errors.append(f"❌ SKILL.md not found in {skill_dir}")
        return False, errors

    content = skill_md.read_text()

    # 2. YAML frontmatter
    fm_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not fm_match:
        errors.append("❌ YAML frontmatter not found")
        return False, errors

    try:
        fm = yaml.safe_load(fm_match.group(1))
    except yaml.YAMLError as e:
        errors.append(f"❌ YAML parse error: {e}")
        return False, errors

    # 3. Required fields
    if "name" not in fm:
        errors.append("❌ Missing required field: name")
    if "description" not in fm:
        errors.append("❌ Missing required field: description")

    if errors:
        return False, errors

    name = fm["name"]
    description = fm["description"]

    # 4. Name validation
    if not re.match(r"^[a-z0-9-]+$", name):
        errors.append(f"❌ name '{name}' invalid: must be lowercase letters, digits, hyphens only")
    if len(name) > 64:
        errors.append(f"❌ name '{name}' too long: max 64 chars (got {len(name)})")

    # 5. Description validation
    if len(description) < 20:
        errors.append(f"❌ description too short: min 20 chars (got {len(description)})")
    if "Use when" not in description and "use when" not in description:
        errors.append("⚠️  description should include 'Use when ...' triggers")
    if "Triggers" not in description and "triggers" not in description:
        errors.append("⚠️  description should include trigger keywords")

    # 6. SKILL.md line count
    line_count = content.count("\n") + 1
    if line_count > 500:
        errors.append(f"⚠️  SKILL.md has {line_count} lines (recommended < 500)")

    # 7. Forbidden files
    forbidden = ["README.md", "INSTALLATION.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md", "QUICK_REFERENCE.md"]
    for f in forbidden:
        if (skill_dir / f).exists():
            errors.append(f"❌ Forbidden file found: {f}")

    # 8. Forbidden extra fields in frontmatter
    allowed_fields = {"name", "description"}
    extra = set(fm.keys()) - allowed_fields
    if extra:
        errors.append(f"⚠️  Extra frontmatter fields: {extra}")

    # 9. Resource references
    refs_dir = skill_dir / "references"
    if refs_dir.exists():
        for ref in refs_dir.rglob("*.md"):
            if ref.name not in content:
                errors.append(f"⚠️  references/{ref.relative_to(skill_dir)} not referenced in SKILL.md")

    assets_dir = skill_dir / "assets"
    if assets_dir.exists():
        for asset in assets_dir.rglob("*.md"):
            if asset.name not in content:
                errors.append(f"⚠️  assets/{asset.relative_to(skill_dir)} not referenced in SKILL.md")

    return len(errors) == 0, errors


def main():
    if len(sys.argv) < 2:
        print("Usage: validate.py <skill_dir>")
        sys.exit(1)

    skill_dir = Path(sys.argv[1]).resolve()
    print(f"Validating skill at: {skill_dir}\n")

    is_valid, errors = validate_skill(skill_dir)

    if errors:
        print("❌ Validation FAILED:\n")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    else:
        print("✅ Validation PASSED\n")
        print(f"  📁 {skill_dir.name}/")
        for p in sorted(skill_dir.rglob("*")):
            if p.is_file():
                size = p.stat().st_size
                print(f"     └── {p.relative_to(skill_dir)} ({size} bytes)")
        sys.exit(0)


if __name__ == "__main__":
    main()
