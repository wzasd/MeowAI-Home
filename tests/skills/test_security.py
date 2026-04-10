"""SecurityAuditor tests"""
import pytest
from pathlib import Path
import os

from src.skills.security import (
    SecurityAuditor,
    SymlinkChecker,
    VulnerabilityScanner,
    ContentValidator,
    PermissionVerifier,
    AuditReport,
    AuditIssue,
)


@pytest.fixture
def valid_skill(tmp_path):
    """创建有效的技能"""
    skill_dir = tmp_path / "valid-skill"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: Valid Skill
description: A valid skill
---

# Valid Skill Content
""")

    return skill_dir


@pytest.fixture
def dangerous_skill(tmp_path):
    """创建包含危险模式的技能"""
    skill_dir = tmp_path / "dangerous-skill"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: Dangerous Skill
description: Contains dangerous patterns
---

# Dangerous Code
""")

    # 创建包含危险代码的 Python 文件
    dangerous_py = skill_dir / "dangerous.py"
    dangerous_py.write_text("""
# Dangerous code
eval("print('hello')")
exec("print('world')")
""")

    return skill_dir


# ========== SymlinkChecker Tests ==========

@pytest.mark.asyncio
async def test_symlink_checker_regular_dir(valid_skill):
    """测试普通目录（非 symlink）"""
    checker = SymlinkChecker()
    issues = await checker.check(valid_skill)

    # 普通目录应该没有问题
    assert len(issues) == 0


@pytest.mark.asyncio
async def test_symlink_checker_valid_symlink(valid_skill, tmp_path):
    """测试有效的 symlink"""
    checker = SymlinkChecker()

    # 创建 symlink
    link_path = tmp_path / "link-to-valid"
    link_path.symlink_to(valid_skill)

    issues = await checker.check(link_path)
    # 由于测试目录不在允许列表中，会有一个 critical 问题
    # 但这不是 symlink 本身的问题，而是路径检查
    assert len(issues) == 1
    assert issues[0].category == "symlink"
    assert "超出允许范围" in issues[0].message


# ========== VulnerabilityScanner Tests ==========

@pytest.mark.asyncio
async def test_vulnerability_scanner_safe_skill(valid_skill):
    """测试安全的技能"""
    scanner = VulnerabilityScanner()
    issues = await scanner.scan(valid_skill)

    # 安全技能应该没有漏洞问题
    vuln_issues = [i for i in issues if i.category == "vulnerability"]
    assert len(vuln_issues) == 0


@pytest.mark.asyncio
async def test_vulnerability_scanner_dangerous_skill(dangerous_skill):
    """测试包含危险模式的技能"""
    scanner = VulnerabilityScanner()
    issues = await scanner.scan(dangerous_skill)

    # 应该检测到 eval 和 exec
    vuln_issues = [i for i in issues if i.category == "vulnerability"]
    assert len(vuln_issues) >= 2  # 至少检测到 eval 和 exec

    messages = [i.message for i in vuln_issues]
    assert any("eval" in msg for msg in messages)
    assert any("exec" in msg for msg in messages)


# ========== ContentValidator Tests ==========

@pytest.mark.asyncio
async def test_content_validator_valid_skill(valid_skill):
    """测试有效的 SKILL.md"""
    validator = ContentValidator()
    issues = await validator.validate(valid_skill)

    # 有效技能应该没有 critical 问题
    critical_issues = [i for i in issues if i.level == "critical"]
    assert len(critical_issues) == 0


@pytest.mark.asyncio
async def test_content_validator_missing_skill_md(tmp_path):
    """测试缺少 SKILL.md"""
    validator = ContentValidator()

    skill_dir = tmp_path / "no-skill-md"
    skill_dir.mkdir()

    issues = await validator.validate(skill_dir)

    # 应该有 critical 问题
    critical_issues = [i for i in issues if i.level == "critical"]
    assert len(critical_issues) == 1
    assert "SKILL.md" in critical_issues[0].message


# ========== PermissionVerifier Tests ==========

@pytest.mark.asyncio
async def test_permission_verifier(valid_skill):
    """测试权限验证"""
    verifier = PermissionVerifier()
    issues = await verifier.verify(valid_skill)

    # 权限问题通常是 info 级别
    assert isinstance(issues, list)


# ========== SecurityAuditor Tests ==========

@pytest.mark.asyncio
async def test_full_audit_valid_skill(valid_skill):
    """测试完整审计 - 有效技能"""
    auditor = SecurityAuditor()
    report = await auditor.audit_skill(valid_skill)

    # skill_path.name 应该是目录名
    assert report.skill_id == "valid-skill"
    assert isinstance(report.issues, list)
    assert isinstance(report.passed, bool)
    from datetime import datetime
    assert isinstance(report.timestamp, datetime)


@pytest.mark.asyncio
async def test_full_audit_dangerous_skill(dangerous_skill):
    """测试完整审计 - 危险技能"""
    auditor = SecurityAuditor()
    report = await auditor.audit_skill(dangerous_skill)

    assert report.skill_id == "dangerous-skill"
    # 危险技能应该有问题
    assert len(report.issues) > 0


# ========== AuditReport Tests ==========

def test_audit_report_to_dict():
    """测试审计报告转换为字典"""
    report = AuditReport(
        skill_id="test-skill",
        issues=[
            AuditIssue(
                level="warning",
                category="test",
                message="Test issue"
            )
        ],
        passed=True
    )

    report_dict = report.to_dict()

    assert report_dict["skill_id"] == "test-skill"
    assert report_dict["passed"] is True
    assert report_dict["issue_count"] == 1
    assert len(report_dict["issues"]) == 1


def test_audit_report_print_summary(capsys):
    """测试打印审计报告摘要"""
    report = AuditReport(
        skill_id="test-skill",
        issues=[
            AuditIssue(
                level="critical",
                category="security",
                message="Critical issue"
            ),
            AuditIssue(
                level="warning",
                category="content",
                message="Warning issue"
            )
        ],
        passed=False
    )

    report.print_summary()
    captured = capsys.readouterr()

    assert "test-skill" in captured.out
    assert "未通过" in captured.out
    assert "CRITICAL" in captured.out
    assert "WARNING" in captured.out
