"""
Unit Tests for MinusCorrect SuperQode Harness Adapter.
Verifies HarnessSpec generation, schema validity, and CLI export commands.
"""

import json
from minuscorrect.harness import get_superqode_harness_spec, export_superqode_harness_spec
from minuscorrect.cli import build_parser, handle_harness


def test_get_superqode_harness_spec_structure():
    spec = get_superqode_harness_spec()
    assert spec["schema_version"] == "1.0"
    harness = spec["harness"]
    assert harness["name"] == "minuscorrect"
    assert harness["runtime"]["type"] == "supervisor"
    assert harness["runtime"]["isolation"]["ephemeral_worktree"] is True
    assert harness["runtime"]["isolation"]["isolate_env"] is True
    assert harness["runtime"]["isolation"]["circuit_breaker"]["max_iterations"] == 4
    assert "tests/golden/**" in harness["policies"]["immutable_contracts"]
    assert "Dockerfile" in harness["policies"]["denied_mutation_targets"]
    assert "Choice" in harness["decision_service"]["primitives"]


def test_export_superqode_harness_spec_json_and_yaml():
    # JSON export
    json_out = export_superqode_harness_spec("json")
    parsed = json.loads(json_out)
    assert parsed["harness"]["name"] == "minuscorrect"

    # YAML export
    yaml_out = export_superqode_harness_spec("yaml")
    assert "minuscorrect" in yaml_out
    assert "schema_version:" in yaml_out
    assert "1.0" in yaml_out


def test_cli_harness_export(capsys):
    parser = build_parser()
    args_json = parser.parse_args(["harness", "export", "--format", "json"])
    assert args_json.command == "harness"
    assert args_json.harness_action == "export"
    assert args_json.format == "json"

    code = handle_harness(args_json)
    assert code == 0
    out = capsys.readouterr().out
    assert '"name": "minuscorrect"' in out

    args_yaml = parser.parse_args(["harness", "export", "--format", "yaml"])
    code_yaml = handle_harness(args_yaml)
    assert code_yaml == 0
    out_yaml = capsys.readouterr().out
    assert "minuscorrect" in out_yaml
