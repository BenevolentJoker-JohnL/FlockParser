#!/usr/bin/env python3
"""
Script to replace print() statements with proper logging calls
"""
import re
from pathlib import Path


def replace_prints_in_file(filepath: Path) -> int:
    """
    Replace print statements with appropriate logging calls
    Returns number of replacements made
    """
    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content
    replacements = 0

    # Patterns for different types of print statements
    patterns = [
        # Error messages (❌, ⚠️, Error, Failed, etc.)
        (r'print\(f?"(❌[^"]*)"', r'logger.error(\1', 'error'),
        (r'print\(f?"(⚠️[^"]*)"', r'logger.warning(\1', 'warning'),
        (r'print\(f?"([^"]*(?:Error|ERROR|Failed|FAILED)[^"]*)"', r'logger.error(\1', 'error'),

        # Success messages (✅, ✓, Success, etc.)
        (r'print\(f?"(✅[^"]*)"', r'logger.info(\1', 'info'),
        (r'print\(f?"(✓[^"]*)"', r'logger.info(\1', 'info'),
        (r'print\(f?"([^"]*(?:Success|SUCCESS|Complete|COMPLETE)[^"]*)"', r'logger.info(\1', 'info'),

        # Info messages (ℹ️, 📊, 📄, etc.)
        (r'print\(f?"(ℹ️[^"]*)"', r'logger.info(\1', 'info'),
        (r'print\(f?"(💡[^"]*)"', r'logger.info(\1', 'info'),
        (r'print\(f?"(📊[^"]*)"', r'logger.info(\1', 'info'),
        (r'print\(f?"(📄[^"]*)"', r'logger.info(\1', 'info'),

        # Debug/verbose messages (Starting, Processing, etc.)
        (r'print\(f?"([^"]*(?:Starting|Processing|Analyzing|Checking)[^"]*)"', r'logger.debug(\1', 'debug'),
    ]

    # Apply patterns
    for pattern, replacement, level in patterns:
        before = content
        content = re.sub(pattern, replacement, content)
        if content != before:
            replacements += 1

    # Generic print statements -> logger.info
    # This handles remaining prints
    content = re.sub(r'\bprint\(', 'logger.info(', content)

    # Write back if changes were made
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)

    return replacements


def main():
    """Replace print statements in main files"""
    files_to_process = [
        'flockparsecli.py',
    ]

    total = 0
    for filename in files_to_process:
        filepath = Path(filename)
        if not filepath.exists():
            print(f"⚠️  Skipping {filename} (not found)")
            continue

        print(f"🔧 Processing {filename}...")
        count = replace_prints_in_file(filepath)
        print(f"   ✅ Made {count} pattern replacements")
        total += count

    print(f"\n✨ Total replacements: {total}")


if __name__ == '__main__':
    main()
