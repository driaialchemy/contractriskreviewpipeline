import ast
import importlib.util
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional

from governance.models import DomainValidationResult, GovernanceFinding, GovernanceLevel


def _load_module_from_path(module_path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _has_docstring(node: ast.AST) -> bool:
    return bool(getattr(node, "docstring", None) or ast.get_docstring(node))


def validate_agents(
    repo_root: Path,
    agent_spec: Dict[str, Any],
    agent_policy: Dict[str, Any],
) -> DomainValidationResult:
    findings: List[GovernanceFinding] = []
    remediation = agent_policy.get("remediation", {})
    expected_agents = agent_policy.get("required_agents", [])

    spec_agents = {item["name"]: item for item in agent_spec.get("agents", [])}

    for agent_name in expected_agents:
        agent_entry = spec_agents.get(agent_name)
        if agent_entry is None:
            findings.append(
                GovernanceFinding(
                    rule_id="agent-spec-missing",
                    message=f"No governance spec entry for agent: {agent_name}",
                    level=GovernanceLevel.CRITICAL,
                    remediation=remediation.get("agent-class-exists"),
                    path=f"governance/specs/agent-governance.spec.yaml",
                )
            )
            continue

        module_rel = agent_entry.get("module", "")
        module_path = repo_root / module_rel
        if not module_path.is_file():
            findings.append(
                GovernanceFinding(
                    rule_id="agent-module-exists",
                    message=f"Agent module missing for {agent_name}: {module_rel}",
                    level=GovernanceLevel.CRITICAL,
                    remediation=remediation.get("agent-module-exists"),
                    path=module_rel,
                )
            )
            continue

        try:
            source = module_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            module = _load_module_from_path(module_path)
        except Exception as exc:
            findings.append(
                GovernanceFinding(
                    rule_id="agent-module-load",
                    message=f"Failed to inspect {agent_name}: {exc}",
                    level=GovernanceLevel.CRITICAL,
                    remediation=remediation.get("agent-class-exists"),
                    path=module_rel,
                )
            )
            continue

        agent_class = getattr(module, agent_name, None)
        if agent_class is None:
            findings.append(
                GovernanceFinding(
                    rule_id="agent-class-exists",
                    message=f"Class {agent_name} not found in {module_rel}",
                    level=GovernanceLevel.CRITICAL,
                    remediation=remediation.get("agent-class-exists"),
                    path=module_rel,
                )
            )
            continue

        declared_name = getattr(agent_class, "name", None)
        if declared_name != agent_name:
            findings.append(
                GovernanceFinding(
                    rule_id="agent-name-attribute",
                    message=f"{agent_name}.name is {declared_name!r}, expected {agent_name!r}",
                    level=GovernanceLevel.CRITICAL,
                    remediation=remediation.get("agent-name-attribute"),
                    path=module_rel,
                )
            )

        if not _inherits_base_agent(tree, agent_name):
            findings.append(
                GovernanceFinding(
                    rule_id="agent-extends-base",
                    message=f"{agent_name} must inherit from BaseAgent",
                    level=GovernanceLevel.CRITICAL,
                    remediation=remediation.get("agent-extends-base"),
                    path=module_rel,
                )
            )

        process_method = getattr(agent_class, "process", None)
        if process_method is None:
            findings.append(
                GovernanceFinding(
                    rule_id="agent-async-process",
                    message=f"{agent_name} missing process method",
                    level=GovernanceLevel.CRITICAL,
                    remediation=remediation.get("agent-async-process"),
                    path=module_rel,
                )
            )
        elif not _is_async_function(process_method):
            findings.append(
                GovernanceFinding(
                    rule_id="agent-async-process",
                    message=f"{agent_name}.process must be async",
                    level=GovernanceLevel.CRITICAL,
                    remediation=remediation.get("agent-async-process"),
                    path=module_rel,
                )
            )

        class_node = _find_class_node(tree, agent_name)
        module_has_doc = bool(ast.get_docstring(tree))
        class_has_doc = class_node is not None and _has_docstring(class_node)
        if not module_has_doc and not class_has_doc:
            findings.append(
                GovernanceFinding(
                    rule_id="agent-documented",
                    message=f"{agent_name} has no module or class docstring",
                    level=GovernanceLevel.WARNING,
                    remediation=remediation.get("agent-documented"),
                    path=module_rel,
                )
            )

    passed = not any(item.level == GovernanceLevel.CRITICAL for item in findings)
    return DomainValidationResult(domain="agent", passed=passed, findings=findings)


def _is_async_function(method: Any) -> bool:
    return inspect.iscoroutinefunction(method)


def _inherits_base_agent(tree: ast.Module, class_name: str) -> bool:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "BaseAgent":
                    return True
                if isinstance(base, ast.Attribute) and base.attr == "BaseAgent":
                    return True
    return False


def _find_class_node(tree: ast.Module, class_name: str) -> Optional[ast.ClassDef]:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None
