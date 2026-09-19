"""
MinusCorrect SuperQode Harness Adapter.
Exposes MinusCorrect as an interoperable execution harness and exports
a standardized SuperQode HarnessSpec.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Literal, Optional


def get_superqode_harness_spec() -> Dict[str, Any]:
    """
    Generate the authoritative SuperQode HarnessSpec data structure.
    # verifies: tests/unit/test_harness.py
    """
    return {
        "schema_version": "1.0",
        "harness": {
            "name": "minuscorrect",
            "version": "1.0.0",
            "description": "MinusCorrect Supervised Corrective Runtime & Execution Containment Harness",
            "author": "MinusCorrect Core",
            "runtime": {
                "type": "supervisor",
                "entrypoint": "minuscorrect.supervisor:AgentSupervisor",
                "isolation": {
                    "ephemeral_worktree": True,
                    "isolate_env": True,
                    "circuit_breaker": {
                        "max_iterations": 4,
                        "default_timeout_seconds": 300.0,
                        "error_hashing": "volatile_strip",
                    },
                },
            },
            "policies": {
                "immutable_contracts": [
                    "tests/golden/**",
                ],
                "denied_mutation_targets": [
                    "Makefile",
                    "makefile",
                    "Dockerfile",
                    "Containerfile",
                    "tox.ini",
                    "noxfile.py",
                    "docker-compose.yml",
                    "docker-compose.yaml",
                    ".gitlab-ci.yml",
                    ".gitlab-ci.yaml",
                    ".circleci/**",
                ],
                "pre_commit_verifier": "python scripts/verify_integrity.py --fix --strict",
            },
            "decision_service": {
                "supported_engines": ["local", "jev", "mock"],
                "default_engine": "local",
                "primitives": ["Choice", "Score", "Noul"],
                "jev_systemone": {
                    "endpoint": "https://api.typesafe.ai/v1/systemone",
                    "timeout_seconds": 2.0,
                    "fallback_to_local": True,
                },
            },
        },
    }


def export_superqode_harness_spec(format_type: Literal["json", "yaml"] = "json") -> str:
    """
    Serialize the SuperQode HarnessSpec into JSON or clean YAML format.
    # verifies: tests/unit/test_harness.py
    """
    spec = get_superqode_harness_spec()
    if format_type == "json":
        return json.dumps(spec, indent=2)

    # Clean YAML formatting without forcing a PyYAML dependency
    try:
        import yaml  # type: ignore
        return yaml.dump(spec, sort_keys=False)
    except ImportError:
        return _dump_simple_yaml(spec)


def _dump_simple_yaml(data: Any, indent_level: int = 0) -> str:
    """Zero-dependency fallback YAML serializer for basic dictionary structures."""
    lines: list[str] = []
    prefix = "  " * indent_level

    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{prefix}{k}:")
                lines.append(_dump_simple_yaml(v, indent_level + 1))
            elif isinstance(v, bool):
                lines.append(f"{prefix}{k}: {'true' if v else 'false'}")
            elif isinstance(v, (int, float)):
                lines.append(f"{prefix}{k}: {v}")
            else:
                lines.append(f"{prefix}{k}: \"{v}\"")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.append(_dump_simple_yaml(item, indent_level + 1))
            elif isinstance(item, bool):
                lines.append(f"{prefix}- {'true' if item else 'false'}")
            elif isinstance(item, (int, float)):
                lines.append(f"{prefix}- {item}")
            else:
                lines.append(f"{prefix}- \"{item}\"")

    return "\n".join(lines)
