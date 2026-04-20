"""Lightweight CLI progress parsers for common commands."""

import re
from typing import Optional

# Regex patterns for high-value CLI commands
PARSER_PATTERNS = [
    {
        "name": "npm",
        "patterns": [
            re.compile(r"added\s+(\d+)\s+packages?", re.IGNORECASE),
            re.compile(r"removed\s+(\d+)\s+packages?", re.IGNORECASE),
            re.compile(r"(\d+)\s+packages?\s+are\s+looking\s+for\s+funding", re.IGNORECASE),
            re.compile(r"idealTree[:\s]", re.IGNORECASE),
            re.compile(r"(audit fix|found\s+\d+\s+vulnerabilities)", re.IGNORECASE),
        ],
    },
    {
        "name": "pytest",
        "patterns": [
            re.compile(r"collected\s+(\d+)\s+item[s]?"),
            re.compile(r"(\d+)\s+passed"),
            re.compile(r"(\d+)\s+failed"),
            re.compile(r"(\d+)\s+error[s]?"),
            re.compile(r"(\d+)%"),
        ],
    },
    {
        "name": "git",
        "patterns": [
            re.compile(r"Receiving objects:\s+(\d+)%\s+\((\d+)/(\d+)\)"),
            re.compile(r"Resolving deltas:\s+(\d+)%\s+\((\d+)/(\d+)\)"),
            re.compile(r"Updating files:\s+(\d+)%\s+\((\d+)/(\d+)\)"),
            re.compile(r"remote:\s+Enumerating objects:\s+(\d+)"),
        ],
    },
    {
        "name": "docker",
        "patterns": [
            re.compile(r"#\d+\s+\[(\d+)/(\d+)\s+.*\]"),
            re.compile(r"Step\s+(\d+)/(\d+)"),
            re.compile(r"(Pulling from|Digest:|Status:)"),
        ],
    },
]

# Detect interactive prompts
WAITING_INPUT_PATTERN = re.compile(
    r"(?i)(y/n|yes/no|password:\s*$|continue\?\s*$|enter to continue\s*$|press any key\s*$|input:\s*$)",
)


def parse_progress(line: str) -> Optional[dict]:
    """Try to extract progress information from a CLI output line.

    Returns a dict with keys: parser, stage, percent, detail
    or None if no pattern matches.
    """
    for parser in PARSER_PATTERNS:
        for pat in parser["patterns"]:
            match = pat.search(line)
            if match:
                groups = match.groups()
                result: dict = {
                    "parser": parser["name"],
                    "detail": line.strip(),
                }
                # Try to infer percent if 3 numeric groups (current/total)
                if len(groups) >= 3:
                    try:
                        current = int(groups[-2])
                        total = int(groups[-1])
                        if total > 0:
                            result["percent"] = min(100, int(current * 100 / total))
                            result["stage"] = f"{current}/{total}"
                    except ValueError:
                        pass
                # Try to infer percent if single numeric group
                elif len(groups) == 1:
                    try:
                        result["percent"] = min(100, int(groups[0]))
                    except ValueError:
                        pass
                return result
    return None


def detect_waiting_input(line: str) -> bool:
    """Detect whether the CLI is waiting for user input."""
    return bool(WAITING_INPUT_PATTERN.search(line))
