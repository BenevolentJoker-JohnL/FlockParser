#!/usr/bin/env python3
"""
Script to automatically fix common code quality issues in FlockParser
"""

import re
from pathlib import Path


def fix_file(filepath: Path) -> tuple[int, list[str]]:
    """
    Fix common code quality issues in a Python file

    Returns:
        (number_of_fixes, list_of_fix_descriptions)
    """
    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content
    fixes = []

    # Fix 1: Remove trailing whitespace
    lines = content.split('\n')
    cleaned_lines = [line.rstrip() for line in lines]
    if lines != cleaned_lines:
        content = '\n'.join(cleaned_lines)
        fixes.append("Removed trailing whitespace")

    # Fix 2: Remove whitespace from blank lines
    content = re.sub(r'^\s+$', '', content, flags=re.MULTILINE)
    if content != original_content:
        fixes.append("Cleaned blank lines")

    # Fix 3: Fix f-strings without placeholders
    # Change f"string" to "string" when no {} present
    def fix_fstring(match):
        string_content = match.group(1)
        if '{' not in string_content:
            return f'"{string_content}"'
        return match.group(0)

    original = content
    content = re.sub(r'f"([^"]*)"', fix_fstring, content)
    content = re.sub(r"f'([^']*)'", lambda m: f"'{m.group(1)}'" if '{' not in m.group(1) else m.group(0), content)
    if content != original:
        fixes.append("Fixed f-strings without placeholders")

    # Fix 4: Replace == True/False with proper comparisons
    content = re.sub(r'\s+==\s+True\b', ' is True', content)
    content = re.sub(r'\s+==\s+False\b', ' is False', content)
    if content != original:
        fixes.append("Fixed boolean comparisons")

    # Fix 5: Add blank lines before function definitions
    # This is complex, so we'll do a simple version
    lines = content.split('\n')
    fixed_lines = []
    prev_line_empty = False

    for i, line in enumerate(lines):
        # Check if this is a top-level function definition
        if line.startswith('def ') and i > 0:
            # Count blank lines before
            blanks_before = 0
            for j in range(i - 1, max(-1, i - 3), -1):
                if lines[j].strip() == '':
                    blanks_before += 1
                else:
                    break

            # Ensure 2 blank lines before top-level functions
            if blanks_before < 2 and not (i > 0 and lines[i-1].strip().startswith('class ')):
                while blanks_before < 2:
                    fixed_lines.append('')
                    blanks_before += 1
                fixes.append(f"Added blank lines before function at line {i}")

        fixed_lines.append(line)

    if len(fixes) > 0:
        content = '\n'.join(fixed_lines)

    # Write back if changes were made
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return (len(fixes), fixes)

    return (0, [])


def main():
    """Fix code quality issues in main Python files"""
    files_to_fix = [
        'flockparsecli.py',
        'flock_ai_api.py',
        'flock_webui.py',
        'flock_mcp_server.py'
    ]

    total_fixes = 0

    for filename in files_to_fix:
        filepath = Path(filename)
        if not filepath.exists():
            print(f"⚠️  Skipping {filename} (not found)")
            continue

        print(f"\n🔧 Fixing {filename}...")
        num_fixes, fix_list = fix_file(filepath)

        if num_fixes > 0:
            print(f"✅ Applied {num_fixes} types of fixes:")
            for fix in fix_list:
                print(f"   - {fix}")
            total_fixes += num_fixes
        else:
            print(f"   No fixes needed")

    print(f"\n✨ Total fix types applied: {total_fixes}")


if __name__ == '__main__':
    main()
