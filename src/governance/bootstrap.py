"""Governance bootstrap — real project activation and health checks."""
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config.nest_config import load_nest_config, save_nest_config, NestConfig
from src.config.nest_registry import NestRegistry
from src.capabilities.orchestrator import get_or_bootstrap as get_or_bootstrap_capabilities


@dataclass
class GovernanceFinding:
    rule: str
    severity: str  # error, warning, info
    message: str


@dataclass
class BootstrapResult:
    project_path: str
    status: str  # healthy, missing, error
    version: str = "1.0.0"
    findings: List[GovernanceFinding] = field(default_factory=list)
    confirmed: bool = True
    synced_at: float = field(default_factory=time.time)


class GovernanceBootstrapService:
    """Performs real project bootstrap: nest activation, capabilities sync, health checks."""

    def __init__(
        self,
        cat_registry: Optional[Any] = None,
        nest_registry: Optional[NestRegistry] = None,
    ):
        self.cat_registry = cat_registry
        self.nest_registry = nest_registry or NestRegistry()

    def _project_name(self, project_path: str) -> str:
        return Path(project_path).name or "project"

    def _valid_cats(self) -> Dict[str, Any]:
        if self.cat_registry is None:
            return {}
        try:
            return self.cat_registry.get_all_configs()
        except Exception:
            return {}

    def _ensure_nest_config(self, project_path: str, findings: List[GovernanceFinding]) -> Optional[NestConfig]:
        neowai_dir = Path(project_path) / ".neowai"
        config_path = neowai_dir / "config.json"
        project_name = self._project_name(project_path)
        valid_cats = self._valid_cats()

        default_cat = "orange"
        if valid_cats:
            default_cat = list(valid_cats.keys())[0]

        try:
            config, warnings = load_nest_config(
                path=config_path,
                project_name=project_name,
                valid_cats=valid_cats,
                interactive=True,
            )
            for w in warnings:
                findings.append(GovernanceFinding(
                    rule="nest-config",
                    severity="warning",
                    message=w,
                ))
            return config
        except Exception as exc:
            findings.append(GovernanceFinding(
                rule="nest-config",
                severity="error",
                message=f"Failed to load/create nest config: {exc}",
            ))
            # Fallback: write a minimal config
            try:
                fallback = NestConfig(project_name=project_name, cats=[default_cat])
                save_nest_config(config_path, fallback)
                return fallback
            except Exception as exc2:
                findings.append(GovernanceFinding(
                    rule="nest-config",
                    severity="error",
                    message=f"Failed to write fallback nest config: {exc2}",
                ))
                return None

    def _check_capabilities(self, project_path: str, findings: List[GovernanceFinding]) -> bool:
        cap_path = Path(project_path) / ".neowai" / "capabilities.json"
        try:
            if not cap_path.exists():
                findings.append(GovernanceFinding(
                    rule="capabilities",
                    severity="warning",
                    message="capabilities.json not found; will bootstrap.",
                ))
                return False
            data = json.loads(cap_path.read_text(encoding="utf-8"))
            caps = data.get("capabilities", [])
            findings.append(GovernanceFinding(
                rule="capabilities",
                severity="info",
                message=f"capabilities.json present with {len(caps)} entries.",
            ))
            return True
        except Exception as exc:
            findings.append(GovernanceFinding(
                rule="capabilities",
                severity="error",
                message=f"Failed to read capabilities.json: {exc}",
            ))
            return False

    def bootstrap(self, project_path: str) -> BootstrapResult:
        """Run full bootstrap for a project and return the result."""
        findings: List[GovernanceFinding] = []
        path = Path(project_path)

        # 1. Check project exists
        if not path.exists():
            return BootstrapResult(
                project_path=project_path,
                status="missing",
                version="1.0.0",
                findings=[GovernanceFinding(
                    rule="existence",
                    severity="error",
                    message=f"Project path does not exist: {project_path}",
                )],
                confirmed=False,
            )

        if not path.is_dir():
            findings.append(GovernanceFinding(
                rule="existence",
                severity="warning",
                message="Project path exists but is not a directory.",
            ))

        # 2. Ensure .neowai dir and nest config
        nest_config = self._ensure_nest_config(project_path, findings)

        # 3. Register in nest index
        try:
            self.nest_registry.register(project_path)
            findings.append(GovernanceFinding(
                rule="nest-registry",
                severity="info",
                message="Project registered in nest index.",
            ))
        except Exception as exc:
            findings.append(GovernanceFinding(
                rule="nest-registry",
                severity="warning",
                message=f"Failed to register in nest index: {exc}",
            ))

        # 4. Bootstrap / sync capabilities
        try:
            get_or_bootstrap_capabilities(project_path)
            findings.append(GovernanceFinding(
                rule="capabilities",
                severity="info",
                message="Capabilities bootstrapped/synced successfully.",
            ))
        except Exception as exc:
            findings.append(GovernanceFinding(
                rule="capabilities",
                severity="error",
                message=f"Capabilities bootstrap failed: {exc}",
            ))

        # 5. Health checks
        has_caps = self._check_capabilities(project_path, findings)

        # Determine overall status
        errors = [f for f in findings if f.severity == "error"]
        status = "healthy" if not errors and has_caps else ("error" if errors else "stale")

        return BootstrapResult(
            project_path=project_path,
            status=status,
            version="1.0.0",
            findings=findings,
            confirmed=True,
        )

    def health_check(self, project_path: str) -> BootstrapResult:
        """Run a lightweight health check without re-bootstrapping capabilities."""
        findings: List[GovernanceFinding] = []
        path = Path(project_path)

        if not path.exists():
            return BootstrapResult(
                project_path=project_path,
                status="missing",
                version="1.0.0",
                findings=[GovernanceFinding(
                    rule="existence",
                    severity="error",
                    message=f"Project path does not exist: {project_path}",
                )],
                confirmed=False,
            )

        has_caps = self._check_capabilities(project_path, findings)
        nest_config = self._ensure_nest_config(project_path, findings)
        if nest_config is None:
            findings.append(GovernanceFinding(
                rule="nest-config",
                severity="error",
                message="Nest config missing or unreadable.",
            ))

        errors = [f for f in findings if f.severity == "error"]
        status = "healthy" if not errors and has_caps else ("missing" if not path.exists() else ("error" if errors else "stale"))
        return BootstrapResult(
            project_path=project_path,
            status=status,
            version="1.0.0",
            findings=findings,
            confirmed=True,
        )
