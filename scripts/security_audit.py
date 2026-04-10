#!/usr/bin/env python3
"""Security audit script for MeowAI Home"""
import ast
import sys
from pathlib import Path
from typing import List, Dict, Any


class SecurityIssue:
    """Represents a security issue."""

    def __init__(self, file: str, line: int, severity: str, message: str):
        self.file = file
        self.line = line
        self.severity = severity
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "severity": self.severity,
            "message": self.message,
        }


class SecurityAuditor:
    """Audits Python code for security issues."""

    DANGEROUS_FUNCTIONS = {
        "eval": "Use of eval() is dangerous",
        "exec": "Use of exec() is dangerous",
        "os.system": "Use of os.system() can lead to command injection",
        "subprocess.call": "Use subprocess.run() with shell=False instead",
        "subprocess.Popen": "Verify shell=False and args are sanitized",
        "pickle.loads": "Pickle can execute arbitrary code",
        "yaml.load": "Use yaml.safe_load() instead",
    }

    def __init__(self, src_path: str):
        self.src_path = Path(src_path)
        self.issues: List[SecurityIssue] = []

    def audit_all(self) -> List[SecurityIssue]:
        """Audit all Python files."""
        for py_file in self.src_path.rglob("*.py"):
            if "cankao" in str(py_file):
                continue
            self.audit_file(py_file)
        return self.issues

    def audit_file(self, file_path: Path):
        """Audit a single Python file."""
        try:
            with open(file_path, "r") as f:
                content = f.read()

            tree = ast.parse(content)
            for node in ast.walk(tree):
                self._check_node(node, file_path, content)
        except SyntaxError:
            pass

    def _check_node(self, node: ast.AST, file_path: Path, content: str):
        """Check AST node for security issues."""
        # Check for dangerous function calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in self.DANGEROUS_FUNCTIONS:
                    self.issues.append(
                        SecurityIssue(
                            file=str(file_path),
                            line=getattr(node, "lineno", 0),
                            severity="HIGH",
                            message=self.DANGEROUS_FUNCTIONS[func_name],
                        )
                    )

        # Check for hardcoded secrets
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value.lower()
            if any(
                keyword in value
                for keyword in ["password", "secret", "api_key", "token"]
            ):
                if len(value) > 10 and not value.startswith(("os.", "env.")):
                    self.issues.append(
                        SecurityIssue(
                            file=str(file_path),
                            line=getattr(node, "lineno", 0),
                            severity="MEDIUM",
                            message="Possible hardcoded secret",
                        )
                    )

    def generate_report(self) -> Dict[str, Any]:
        """Generate audit report."""
        return {
            "summary": {
                "total_issues": len(self.issues),
                "high_severity": len([i for i in self.issues if i.severity == "HIGH"]),
                "medium_severity": len(
                    [i for i in self.issues if i.severity == "MEDIUM"]
                ),
                "low_severity": len([i for i in self.issues if i.severity == "LOW"]),
            },
            "issues": [i.to_dict() for i in self.issues],
        }


def main():
    """Run security audit."""
    print("🔒 Running security audit...")

    auditor = SecurityAuditor("src")
    issues = auditor.audit_all()
    report = auditor.generate_report()

    print(f"\n📊 Summary:")
    print(f"  Total issues: {report['summary']['total_issues']}")
    print(f"  High severity: {report['summary']['high_severity']}")
    print(f"  Medium severity: {report['summary']['medium_severity']}")

    if issues:
        print(f"\n⚠️  Issues found:")
        for issue in issues:
            print(f"  [{issue.severity}] {issue.file}:{issue.line} - {issue.message}")
        sys.exit(1)
    else:
        print("\n✅ No security issues found!")
        sys.exit(0)


if __name__ == "__main__":
    main()
