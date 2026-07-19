"""Deterministic Python AST analysis and limited intra-file taint tracing.

The tracer reads source text only.  It never imports, executes, installs, or
otherwise evaluates repository code, and it makes no LLM calls.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse

from skill_passport_core.fetcher import FetchedFile


@dataclass(frozen=True)
class EvidenceLocation:
    file: str
    line: int
    description: str


@dataclass(frozen=True)
class Finding:
    category: str
    source: EvidenceLocation | None
    sink: EvidenceLocation
    assignment_chain: tuple[str, ...]
    external_domain: str | None = None


@dataclass(frozen=True)
class _Taint:
    source: EvidenceLocation
    chain: tuple[str, ...]


NETWORK_CALLS = {
    "requests.get",
    "requests.post",
    "requests.put",
    "requests.patch",
    "requests.delete",
    "httpx.get",
    "httpx.post",
    "httpx.put",
    "httpx.patch",
    "httpx.delete",
    "urllib.request.urlopen",
    "urlopen",
}
FILE_READ_CALLS = {"open", "Path.open", "Path.read_text", "Path.read_bytes", "PdfReader"}
FILE_WRITE_METHODS = {"write", "write_text", "write_bytes", "save"}
FILE_READ_METHODS = {"read", "read_text", "read_bytes"}


def trace_python_files(files: Iterable[FetchedFile]) -> list[Finding]:
    """Return structural findings from Python source files in input order."""
    findings: list[Finding] = []
    for file in files:
        if not file.path.endswith(".py"):
            continue
        try:
            tree = ast.parse(file.content, filename=file.path)
        except SyntaxError:
            continue
        findings.extend(_PythonTracer(file.path).trace(tree))
    return findings


class _PythonTracer(ast.NodeVisitor):
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.findings: list[Finding] = []
        self.taints: dict[str, _Taint] = {}

    def trace(self, tree: ast.AST) -> list[Finding]:
        self.visit(tree)
        return self.findings

    def visit_Assign(self, node: ast.Assign) -> None:
        self._record_assignment_taint(node.targets, node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self._record_assignment_taint([node.target], node.value)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = _call_name(node.func)
        if call_name in NETWORK_CALLS:
            self._record_network_call(node, call_name)
        self._record_filesystem_call(node, call_name)
        self.generic_visit(node)

    def _record_assignment_taint(self, targets: list[ast.expr], value: ast.expr) -> None:
        env_source = _environment_source(value)
        if env_source is not None:
            evidence = self._evidence(value, env_source)
            for target in targets:
                target_name = _target_name(target)
                if target_name is None:
                    continue
                self.taints[target_name] = _Taint(evidence, (target_name,))
                self.findings.append(
                    Finding("secrets", evidence, evidence, (target_name,))
                )
            return

        read_call = value if isinstance(value, ast.Call) and _is_file_read_call(value) else None
        if read_call is not None:
            evidence = self._evidence(read_call, "filesystem read")
            for target in targets:
                target_name = _target_name(target)
                if target_name is not None:
                    self.taints[target_name] = _Taint(evidence, (target_name,))
            return

        if isinstance(value, ast.Name) and value.id in self.taints:
            for target in targets:
                target_name = _target_name(target)
                if target_name is not None:
                    taint = self.taints[value.id]
                    self.taints[target_name] = _Taint(
                        taint.source, taint.chain + (target_name,)
                    )
            return

        if isinstance(value, ast.Dict):
            for target in targets:
                container = _target_name(target)
                if container is None:
                    continue
                for key, item in zip(value.keys, value.values, strict=True):
                    if key is None:
                        continue
                    taint = self._taint_for_expression(item)
                    if taint is None:
                        continue
                    key_label = _subscript_label(container, key)
                    self.taints[key_label] = _Taint(
                        taint.source, taint.chain + (key_label,)
                    )

    def _record_network_call(self, node: ast.Call, call_name: str) -> None:
        sink = self._evidence(node, f"{call_name}(...)")
        taints = self._call_taints(node)
        domain = _external_domain(node)
        if not taints:
            self.findings.append(
                Finding("network", None, sink, (sink.description,), domain)
            )
            return
        for taint in _unique_taints(taints):
            self.findings.append(
                Finding(
                    "network",
                    taint.source,
                    sink,
                    taint.chain + (sink.description,),
                    domain,
                )
            )

    def _record_filesystem_call(self, node: ast.Call, call_name: str) -> None:
        operation = _filesystem_operation(node, call_name)
        if operation is None:
            return
        sink = self._evidence(node, f"filesystem {operation}")
        self.findings.append(Finding("filesystem", None, sink, (sink.description,)))

    def _call_taints(self, node: ast.Call) -> list[_Taint]:
        taints: list[_Taint] = []
        for argument in (*node.args, *(keyword.value for keyword in node.keywords)):
            taints.extend(self._taints_for_expression(argument))
        return taints

    def _taint_for_expression(self, expression: ast.expr) -> _Taint | None:
        taints = self._taints_for_expression(expression)
        return taints[0] if taints else None

    def _taints_for_expression(self, expression: ast.expr) -> list[_Taint]:
        if isinstance(expression, ast.Name):
            direct_taint = self.taints.get(expression.id)
            if direct_taint is not None:
                return [direct_taint]
            prefix = f"{expression.id}["
            return [
                taint for label, taint in self.taints.items() if label.startswith(prefix)
            ]
        if isinstance(expression, ast.Subscript):
            label = _subscript_expression_label(expression)
            taint = self.taints.get(label) if label is not None else None
            return [taint] if taint is not None else []
        if isinstance(expression, ast.Dict):
            for value in expression.values:
                taints = self._taints_for_expression(value)
                if taints:
                    return taints
        return []

    def _evidence(self, node: ast.AST, description: str) -> EvidenceLocation:
        return EvidenceLocation(self.file_path, node.lineno, description)


def _call_name(function: ast.expr) -> str:
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        prefix = _call_name(function.value)
        return f"{prefix}.{function.attr}" if prefix else function.attr
    return ""


def _environment_source(value: ast.expr) -> str | None:
    if not isinstance(value, ast.Call):
        return None
    call_name = _call_name(value.func)
    if call_name not in {"os.environ.get", "os.getenv"}:
        return None
    if not value.args or not isinstance(value.args[0], ast.Constant):
        return None
    variable = value.args[0].value
    if not isinstance(variable, str):
        return None
    return f'{call_name}("{variable}")'


def _target_name(target: ast.expr) -> str | None:
    return target.id if isinstance(target, ast.Name) else None


def _subscript_label(container: str, key: ast.expr) -> str:
    if isinstance(key, ast.Constant) and isinstance(key.value, str):
        return f'{container}["{key.value}"]'
    return f"{container}[...]"


def _subscript_expression_label(expression: ast.Subscript) -> str | None:
    if not isinstance(expression.value, ast.Name):
        return None
    return _subscript_label(expression.value.id, expression.slice)


def _external_domain(node: ast.Call) -> str | None:
    if not node.args or not isinstance(node.args[0], ast.Constant):
        return None
    url = node.args[0].value
    return urlparse(url).netloc if isinstance(url, str) else None


def _is_file_read_call(node: ast.Call) -> bool:
    return _filesystem_operation(node, _call_name(node.func)) == "read"


def _filesystem_operation(node: ast.Call, call_name: str) -> str | None:
    if call_name == "open":
        mode = _open_mode(node)
        return "write" if any(flag in mode for flag in "wax+") else "read"
    if call_name in FILE_READ_CALLS or call_name.endswith(".PdfReader") or call_name.endswith(".open"):
        return "read"
    if call_name.endswith(".write") or call_name.endswith(".PdfWriter.write"):
        return "write"
    if isinstance(node.func, ast.Attribute) and node.func.attr in FILE_WRITE_METHODS:
        return "write"
    if isinstance(node.func, ast.Attribute) and node.func.attr in FILE_READ_METHODS:
        return "read"
    return None


def _open_mode(node: ast.Call) -> str:
    if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
        return str(node.args[1].value)
    for keyword in node.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
            return str(keyword.value.value)
    return "r"


def _unique_taints(taints: list[_Taint]) -> list[_Taint]:
    unique: list[_Taint] = []
    seen: set[tuple[EvidenceLocation, tuple[str, ...]]] = set()
    for taint in taints:
        key = (taint.source, taint.chain)
        if key not in seen:
            seen.add(key)
            unique.append(taint)
    return unique
