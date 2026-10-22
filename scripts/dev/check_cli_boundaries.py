#!/usr/bin/env python3
"""Enforce domain -> no CLI and CLI children -> no main-entry backreferences.

This bounded AST check covers imports and known literal dynamic lookups, not
arbitrary Python dataflow. File length remains an observation, never a gate.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from importlib.util import resolve_name
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SUSPICIOUS_IMPORTS = {"http.server", "requests", "shapely", "socket", "subprocess", "psutil"}


@dataclass(frozen=True)
class BoundaryFinding:
    path: str
    status: str
    notes: str


def _cli_target(name: str) -> bool:
    return name == "netwatch.cli" or name.startswith(("netwatch.cli.", "netwatch.cli_modules"))


def inspect_file(path: Path, rel_path: str) -> list[str]:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [f"syntax error: {exc.msg}"]
    child = rel_path.startswith("netwatch/cli_modules/")
    domain = not child and rel_path not in {"netwatch/cli.py", "netwatch/__main__.py"}
    module = rel_path.removesuffix(".py").replace("/", ".")
    package = module.rpartition(".")[0]
    aliases: dict[str, str] = {}
    notes: list[str] = []

    def check(target: str) -> None:
        if (child and (target == "netwatch.cli" or target.startswith("netwatch.cli."))) or (domain and _cli_target(target)):
            notes.append(f"reverse CLI dependency: {target}")

    def qualified(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            return qualified(node.value) + "." + node.attr
        return ""

    def literal(node: ast.AST) -> str:
        return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else ""

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                check(alias.name)
                aliases[alias.asname or alias.name.split(".")[0]] = alias.name if alias.asname else alias.name.split(".")[0]
                if child and (alias.name in SUSPICIOUS_IMPORTS or alias.name.split(".")[0] in SUSPICIOUS_IMPORTS):
                    notes.append(f"suspicious low-level import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                try:
                    base = resolve_name("." * node.level + base, package)
                except (ImportError, ValueError):
                    notes.append("invalid relative import")
                    continue
            check(base)
            for alias in node.names:
                target = base + "." + alias.name
                aliases[alias.asname or alias.name] = target
                check(target)
            if child and (base in SUSPICIOUS_IMPORTS or base.split(".")[0] in SUSPICIOUS_IMPORTS):
                notes.append(f"suspicious low-level import: {base}")
        if child and isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in {"ConsoleProxy", "cli_override"}:
            notes.append(f"legacy entry bridge: {node.name}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            check(qualified(node))
        elif isinstance(node, ast.Subscript) and qualified(node.value) == "sys.modules":
            check(literal(node.slice))
        elif isinstance(node, ast.Call):
            func = qualified(node.func)
            if child and func.rsplit(".", 1)[-1] == "cli_override":
                notes.append("legacy entry bridge call: cli_override")
            if node.args and func in {"importlib.import_module", "__import__", "sys.modules.get"}:
                target = literal(node.args[0])
                if target.startswith(".") and func == "importlib.import_module" and len(node.args) > 1:
                    try:
                        target = resolve_name(target, literal(node.args[1]))
                    except (ImportError, ValueError):
                        pass
                check(target)
            if func == "getattr" and len(node.args) > 1:
                check(qualified(node.args[0]) + "." + literal(node.args[1]))
    if child and len(text.splitlines()) > 900:
        notes.append("large CLI module; periodically review presentation helpers")
    return sorted(set(notes))


def scan_cli_boundaries(repo_root: Path = REPO_ROOT) -> list[BoundaryFinding]:
    findings = []
    if not (repo_root / "netwatch").is_dir():
        return [BoundaryFinding("netwatch", "violation", "runtime package missing")]
    for path in sorted((repo_root / "netwatch").rglob("*.py")):
        relative = path.relative_to(repo_root).as_posix()
        notes = inspect_file(path, relative)
        blocking = any(not note.startswith("large CLI module") for note in notes)
        status = "violation" if blocking else "observe" if notes else "ok_adapter"
        findings.append(BoundaryFinding(relative, status, "; ".join(notes) or "dependency direction OK"))
    return findings


def print_findings(findings: list[BoundaryFinding]) -> None:
    for finding in findings:
        print(f"{finding.path} | {finding.status} | {finding.notes}")
    print(f"STRICT_BOUNDARY_VIOLATIONS={sum(f.status == 'violation' for f in findings)}")


def main(repo_root: Path = REPO_ROOT) -> int:
    findings = scan_cli_boundaries(repo_root)
    print_findings(findings)
    return int(any(f.status == "violation" for f in findings))


if __name__ == "__main__":
    raise SystemExit(main())
