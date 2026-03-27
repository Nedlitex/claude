#!/usr/bin/env python3
"""
Plan validation script for agent team tracking system.
Validates plan files have correct structure, frontmatter, and step markers.

Usage:
    python validate-plan.py <plan-file> [--strict]

Exit codes:
    0 = valid
    1 = errors found
    2 = warnings only (with --strict, treated as errors)
"""

import sys
import re
import json
from pathlib import Path


def validate_plan(filepath: str, strict: bool = False) -> dict:
    path = Path(filepath)
    errors = []
    warnings = []
    stats = {"total_steps": 0, "completed": 0, "pending": 0, "in_progress": 0}

    if not path.exists():
        return {"valid": False, "errors": [f"File not found: {filepath}"], "warnings": [], "stats": stats}

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Check for title
    has_title = any(line.startswith("# ") for line in lines[:10])
    if not has_title:
        errors.append("Missing plan title (no '# ' heading in first 10 lines)")

    # Check for overview/description section
    has_overview = any(
        re.match(r"^##\s+(Overview|Description|Summary)", line, re.IGNORECASE)
        for line in lines
    )
    if not has_overview:
        warnings.append("Missing Overview/Description section")

    # Parse checkboxes as steps
    checkbox_pattern = re.compile(r"^(\s*)-\s+\[([ xX])\]\s+(.+)")
    for i, line in enumerate(lines):
        m = checkbox_pattern.match(line)
        if m:
            stats["total_steps"] += 1
            marker = m.group(2).strip().lower()
            task_text = m.group(3).strip()

            if marker == "x":
                stats["completed"] += 1
            else:
                # Check for in-progress markers
                if "IN PROGRESS" in task_text.upper() or "🔄" in task_text:
                    stats["in_progress"] += 1
                else:
                    stats["pending"] += 1

            # Warn on vague steps
            vague_words = ["do stuff", "fix things", "update code", "make changes"]
            if any(v in task_text.lower() for v in vague_words):
                warnings.append(f"Line {i+1}: Vague step description: '{task_text[:50]}'")

    if stats["total_steps"] == 0:
        errors.append("No task checkboxes found (expected '- [ ] task' or '- [x] task')")

    # Check for success criteria
    has_criteria = any(
        re.match(r"^##\s+(Success\s+Criteria|Acceptance\s+Criteria|Done\s+When|Verification)", line, re.IGNORECASE)
        for line in lines
    )
    if not has_criteria:
        warnings.append("Missing Success Criteria section")

    # Determine validity
    valid = len(errors) == 0
    if strict and len(warnings) > 0:
        valid = False

    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "stats": stats,
        "file": filepath,
    }


def get_current_step(filepath: str) -> dict:
    """Find the current in-progress or next pending step."""
    path = Path(filepath)
    if not path.exists():
        return {"found": False, "error": f"File not found: {filepath}"}

    content = path.read_text(encoding="utf-8")
    checkbox_pattern = re.compile(r"^(\s*)-\s+\[([ xX])\]\s+(.+)")

    step_id = 0
    for i, line in enumerate(content.splitlines()):
        m = checkbox_pattern.match(line)
        if m:
            step_id += 1
            marker = m.group(2).strip().lower()
            task_text = m.group(3).strip()

            if marker != "x":
                # Check for in-progress
                if "IN PROGRESS" in task_text.upper() or "🔄" in task_text:
                    return {
                        "found": True,
                        "step_id": step_id,
                        "line": i + 1,
                        "status": "in-progress",
                        "description": task_text,
                    }

    # No in-progress found, find first pending
    step_id = 0
    for i, line in enumerate(content.splitlines()):
        m = checkbox_pattern.match(line)
        if m:
            step_id += 1
            marker = m.group(2).strip().lower()
            task_text = m.group(3).strip()

            if marker != "x" and "IN PROGRESS" not in task_text.upper():
                return {
                    "found": False,
                    "next_pending": {
                        "step_id": step_id,
                        "line": i + 1,
                        "description": task_text,
                    },
                }

    return {"found": False, "next_pending": None, "message": "All steps completed"}


def update_step(filepath: str, step_num: int, new_status: str) -> dict:
    """Mark a step as done or in-progress by step number (1-indexed)."""
    path = Path(filepath)
    if not path.exists():
        return {"success": False, "error": f"File not found: {filepath}"}

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    checkbox_pattern = re.compile(r"^(\s*)-\s+\[([ xX])\]\s+(.+)")

    current_step = 0
    for i, line in enumerate(lines):
        m = checkbox_pattern.match(line)
        if m:
            current_step += 1
            if current_step == step_num:
                indent = m.group(1)
                task_text = m.group(3).strip()
                # Remove any existing status markers
                task_text = re.sub(r"\s*🔄\s*IN PROGRESS\s*", "", task_text)
                task_text = re.sub(r"\s*IN PROGRESS\s*", "", task_text).strip()

                if new_status == "done":
                    lines[i] = f"{indent}- [x] {task_text}"
                elif new_status == "in-progress":
                    lines[i] = f"{indent}- [ ] 🔄 {task_text}"
                elif new_status == "pending":
                    lines[i] = f"{indent}- [ ] {task_text}"
                else:
                    return {"success": False, "error": f"Unknown status: {new_status}"}

                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                return {
                    "success": True,
                    "step_id": step_num,
                    "new_status": new_status,
                    "description": task_text,
                }

    return {"success": False, "error": f"Step {step_num} not found (total steps: {current_step})"}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: validate-plan.py <plan-file> [--strict | --current-step | --update <step> <status>]")
        sys.exit(1)

    filepath = sys.argv[1]

    if "--current-step" in sys.argv:
        result = get_current_step(filepath)
        print(json.dumps(result, indent=2))
        sys.exit(0)

    if "--update" in sys.argv:
        idx = sys.argv.index("--update")
        if idx + 2 >= len(sys.argv):
            print("Usage: --update <step-number> <done|in-progress|pending>")
            sys.exit(1)
        step_num = int(sys.argv[idx + 1])
        status = sys.argv[idx + 2]
        result = update_step(filepath, step_num, status)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["success"] else 1)

    strict = "--strict" in sys.argv
    result = validate_plan(filepath, strict)
    print(json.dumps(result, indent=2))

    if not result["valid"]:
        sys.exit(1)
    elif result["warnings"]:
        sys.exit(2)
    else:
        sys.exit(0)
