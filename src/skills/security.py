"""SecurityAuditor - 6步安全审计管道"""
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class AuditIssue:
    """审计问题"""
    level: str  # critical, error, warning, info
    category: str
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    recommendation: Optional[str] = None


@dataclass
class AuditReport:
    """审计报告"""
    skill_id: str
    issues: List[AuditIssue]
    passed: bool
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "skill_id": self.skill_id,
            "passed": self.passed,
            "timestamp": self.timestamp.isoformat(),
            "issue_count": len(self.issues),
            "issues": [
                {
                    "level": issue.level,
                    "category": issue.category,
                    "message": issue.message,
                    "file": issue.file,
                    "line": issue.line,
                    "recommendation": issue.recommendation
                }
                for issue in self.issues
            ]
        }

    def print_summary(self):
        """打印摘要"""
        print(f"\n安全审计报告: {self.skill_id}")
        print(f"状态: {'✅ 通过' if self.passed else '❌ 未通过'}")
        print(f"问题总数: {len(self.issues)}")

        # 按级别分组
        by_level = {}
        for issue in self.issues:
            if issue.level not in by_level:
                by_level[issue.level] = []
            by_level[issue.level].append(issue)

        for level in ["critical", "error", "warning", "info"]:
            if level in by_level:
                print(f"\n{level.upper()}: {len(by_level[level])}")
                for issue in by_level[level][:5]:  # 最多显示5个
                    print(f"  - {issue.message}")
                    if issue.file:
                        print(f"    文件: {issue.file}:{issue.line or '?'}")
                    if issue.recommendation:
                        print(f"    建议: {issue.recommendation}")


class SymlinkChecker:
    """Symlink 安全检查器"""

    async def check(self, skill_path: Path) -> List[AuditIssue]:
        """检查 symlink 安全性"""
        issues = []

        # 检查是否为 symlink
        if skill_path.is_symlink():
            target = skill_path.resolve()

            # 检查目标是否在允许的目录内
            if not self._is_in_allowed_directory(target):
                issues.append(AuditIssue(
                    level="critical",
                    category="symlink",
                    message=f"Symlink 目标 {target} 超出允许范围"
                ))

            # 检查目标是否存在
            if not target.exists():
                issues.append(AuditIssue(
                    level="error",
                    category="symlink",
                    message=f"Symlink 目标 {target} 不存在"
                ))

            # 检查是否为循环链接
            if self._is_circular(skill_path):
                issues.append(AuditIssue(
                    level="critical",
                    category="symlink",
                    message="检测到循环 symlink"
                ))

        return issues

    def _is_in_allowed_directory(self, path: Path) -> bool:
        """检查路径是否在允许的目录内"""
        allowed_dirs = [
            Path.home() / ".meowai" / "skills",
            Path.cwd() / "skills"
        ]
        return any(str(path).startswith(str(allowed)) for allowed in allowed_dirs)

    def _is_circular(self, path: Path) -> bool:
        """检查是否存在循环 symlink"""
        try:
                path.resolve()
                return False
        except OSError:
            return True


class VulnerabilityScanner:
    """漏洞扫描器"""

    # 危险模式列表
    DANGEROUS_PATTERNS = [
        r"eval\s*\(",
        r"exec\s*\(",
        r"compile\s*\(",
        r"__import__\s*\(",
        r"subprocess\.(call|run|Popen)",
        r"os\.system\s*\(",
        r"pickle\.loads?\s*\(",
        r"yaml\.load\s*\([^)]*\)",  # 不安全的 YAML 加载
    ]

    async def scan(self, skill_path: Path) -> List[AuditIssue]:
        """扫描技能文件中的潜在漏洞"""
        issues = []

        # 扫描所有 Python 文件
        for py_file in skill_path.rglob("*.py"):
            content = py_file.read_text()

            for pattern in self.DANGEROUS_PATTERNS:
                if re.search(pattern, content):
                    issues.append(AuditIssue(
                        level="warning",
                        category="vulnerability",
                        message=f"检测到潜在危险模式: {pattern}",
                        file=str(py_file),
                        line=self._find_line(content, pattern)
                    ))

        return issues

    def _find_line(self, content: str, pattern: str) -> int:
        """找到匹配模式的行号"""
        for i, line in enumerate(content.split('\n'), 1):
            if re.search(pattern, line):
                return i
        return -1


class ContentValidator:
    """内容验证器"""

    # 必需的 SKILL.md 字段
    REQUIRED_FIELDS = ["name", "description"]

    # 禁止的内容模式
    FORBIDDEN_PATTERNS = [
        r"密码",
        r"password",
        r"api[_-]?key",
        r"secret[_-]?key",
        r"token",
    ]

    async def validate(self, skill_path: Path) -> List[AuditIssue]:
        """验证技能内容"""
        issues = []

        # 检查 SKILL.md 是否存在
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            issues.append(AuditIssue(
                level="critical",
                category="content",
                message="缺少 SKILL.md 文件"
            ))
            return issues

        # 解析 frontmatter
        try:
            import yaml
            with open(skill_md) as f:
                content = f.read()
                # 简单解析 frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 2:
                        frontmatter = yaml.safe_load(parts[1])

                        # 检查必需字段
                        for field in self.REQUIRED_FIELDS:
                            if field not in frontmatter:
                                issues.append(AuditIssue(
                                    level="error",
                                    category="content",
                                    message=f"SKILL.md 缺少必需字段: {field}"
                                ))

            # 检查禁止的内容
            for pattern in self.FORBIDDEN_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    issues.append(AuditIssue(
                        level="warning",
                        category="content",
                        message=f"检测到敏感内容模式: {pattern}"
                    ))

        except Exception as e:
            issues.append(AuditIssue(
                level="error",
                category="content",
                message=f"SKILL.md 解析失败: {str(e)}"
            ))

        return issues


class PermissionVerifier:
    """权限验证器"""

    async def verify(self, skill_path: Path) -> List[AuditIssue]:
        """验证技能权限"""
        issues = []

        # 检查文件权限
        for file in skill_path.rglob("*"):
            if file.is_file():
                # 检查是否可写（应该只读）
                if os.access(file, os.W_OK):
                    stat_info = file.stat()
                    if stat_info.st_mode & 0o777 != 0o644:
                        issues.append(AuditIssue(
                            level="info",
                            category="permission",
                            message=f"文件权限过宽松: {file}",
                            recommendation="建议设置为 644"
                        ))

        # 检查目录权限
        for dir in skill_path.rglob("*"):
            if dir.is_dir():
                if os.access(dir, os.W_OK):
                    stat_info = dir.stat()
                    if stat_info.st_mode & 0o777 != 0o755:
                        issues.append(AuditIssue(
                            level="info",
                            category="permission",
                            message=f"目录权限过宽松: {dir}",
                            recommendation="建议设置为 755"
                        ))

        return issues


class DependencyChecker:
    """依赖检查器"""

    async def check(self, skill_path: Path) -> List[AuditIssue]:
        """检查技能依赖"""
        issues = []

        # 检查 requires_mcp 依赖（如果有的话）
        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            try:
                import yaml
                with open(skill_md) as f:
                    content = f.read()
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 2:
                            frontmatter = yaml.safe_load(parts[1])
                            requires_mcp = frontmatter.get("requires_mcp", [])

                            # 这里只记录依赖，实际验证在运行时进行
                            if requires_mcp:
                                issues.append(AuditIssue(
                                    level="info",
                                    category="dependency",
                                    message=f"技能需要 MCP 工具: {', '.join(requires_mcp)}"
                                ))
            except Exception:
                pass  # 忽略解析错误（由 ContentValidator 处理）

        return issues


class SecurityAuditor:
    """技能安全审计器 - 6步审计管道"""

    def __init__(self):
        self.symlink_checker = SymlinkChecker()
        self.vulnerability_scanner = VulnerabilityScanner()
        self.content_validator = ContentValidator()
        self.permission_verifier = PermissionVerifier()
        self.dependency_checker = DependencyChecker()

    async def audit_skill(self, skill_path: Path) -> AuditReport:
        """
        执行完整的安全审计

        Args:
            skill_path: 技能目录路径

        Returns:
            AuditReport
        """
        issues = []

        # Step 1: Symlink 安全性检查
        print("Step 1/6: 检查 Symlink 安全性...")
        symlink_issues = await self.symlink_checker.check(skill_path)
        issues.extend(symlink_issues)

        # Step 2: 漏洞扫描
        print("Step 2/6: 扫描潜在漏洞...")
        vuln_issues = await self.vulnerability_scanner.scan(skill_path)
        issues.extend(vuln_issues)

        # Step 3: 内容验证
        print("Step 3/6: 验证技能内容...")
        content_issues = await self.content_validator.validate(skill_path)
        issues.extend(content_issues)

        # Step 4: 权限验证
        print("Step 4/6: 验证文件权限...")
        perm_issues = await self.permission_verifier.verify(skill_path)
        issues.extend(perm_issues)

        # Step 5: 依赖检查
        print("Step 5/6: 检查依赖安全性...")
        dep_issues = await self.dependency_checker.check(skill_path)
        issues.extend(dep_issues)

        # Step 6: 生成报告
        print("Step 6/6: 生成审计报告...")

        return AuditReport(
            skill_id=skill_path.name,
            issues=issues,
            passed=len([i for i in issues if i.level == "critical"]) == 0
        )
