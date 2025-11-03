#!/usr/bin/env python3
"""
Properly replace print() with logger calls while preserving f-strings and formatting
"""
import re
from pathlib import Path


def replace_prints(filepath: Path) -> tuple[int, int, int]:
    """
    Replace print statements with logging
    Returns: (total_replaced, errors, warnings)
    """
    with open(filepath, "r") as f:
        lines = f.readlines()

    errors = 0
    warnings = 0
    total = 0

    new_lines = []
    for line in lines:
        original = line

        # Check if line contains print(
        if "print(" in line and not line.strip().startswith("#"):
            total += 1

            # Determine log level based on content
            if "❌" in line or "Error" in line or "Failed" in line or "ERROR" in line:
                line = line.replace("print(", "logger.error(")
                errors += 1
            elif "⚠️" in line or "Warning" in line or "WARN" in line:
                line = line.replace("print(", "logger.warning(")
                warnings += 1
            else:
                # Default to info
                line = line.replace("print(", "logger.info(")

        new_lines.append(line)

    # Add logging imports at the top if not present
    if total > 0:
        # Find where to insert imports
        insert_idx = 0
        has_logging = False
        has_logger_setup = False

        for i, line in enumerate(new_lines):
            if "import logging" in line:
                has_logging = True
            if "from logging_config import" in line:
                has_logger_setup = True
            if line.startswith("import ") or line.startswith("from "):
                insert_idx = i + 1

        # Insert imports if needed
        if not has_logging:
            new_lines.insert(0, "import logging\n")
            insert_idx += 1

        if not has_logger_setup:
            # Find end of imports
            for i in range(len(new_lines)):
                if new_lines[i].strip() and not (
                    new_lines[i].startswith("import") or new_lines[i].startswith("from") or new_lines[i].startswith("#")
                ):
                    new_lines.insert(i, "\n")
                    new_lines.insert(i + 1, "from logging_config import setup_logging\n")
                    new_lines.insert(i + 2, "\n")
                    new_lines.insert(i + 3, "# Initialize logging\n")
                    new_lines.insert(i + 4, "logger = setup_logging()\n")
                    break

    with open(filepath, "w") as f:
        f.writelines(new_lines)

    return total, errors, warnings


def main():
    filepath = Path("flockparsecli.py")

    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        return

    print(f"🔧 Replacing print() with logger calls in {filepath}...")
    total, errors, warnings = replace_prints(filepath)

    print(f"✅ Replaced {total} print() statements:")
    print(f"   - {errors} → logger.error()")
    print(f"   - {warnings} → logger.warning()")
    print(f"   - {total - errors - warnings} → logger.info()")


if __name__ == "__main__":
    main()
