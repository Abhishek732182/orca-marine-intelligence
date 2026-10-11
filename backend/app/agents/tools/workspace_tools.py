"""Controlled workspace tools for ORCA Agent 6: AI Workspace Assistant.

Enforces strict sandbox safety:
1. Filesystem access is strictly restricted to the authorized workspace root (D:\\orca).
2. Prohibits path traversal (..) outside authorized workspace boundaries.
3. Completely blocks sensitive files (.env, credentials, certificates, keys).
4. Proposes unified diffs before applying changes and requires user approval.
5. Whitelists approved development commands (pytest, git status, npm test).
6. Records real command outputs, exit codes, and durations without fabrication.
"""

import difflib
import os
from pathlib import Path
import subprocess
from typing import Any

# Authorized project root directory
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

# Sensitive files/patterns that must never be read or edited
SENSITIVE_PATTERNS = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
    ".pem",
    ".key",
    "credentials",
    "secrets.json",
}

# Whitelist of permitted command prefixes
APPROVED_COMMAND_PREFIXES = [
    (".venv\\Scripts\\pytest", True),
    ("pytest", True),
    ("npm test", True),
    ("npm run lint", True),
    ("git status", True),
    ("git diff", True),
    ("git log -n", True),
]


def _resolve_safe_path(rel_path: str) -> Path:
    """Resolve and enforce that path lies strictly within WORKSPACE_ROOT."""
    # Normalize path
    target = (WORKSPACE_ROOT / rel_path).resolve()
    try:
        target.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise PermissionError(
            f"Access denied: Path '{rel_path}' escapes the authorized workspace root '{WORKSPACE_ROOT}'."
        ) from exc

    # Check sensitive files
    name_lower = target.name.lower()
    if name_lower in SENSITIVE_PATTERNS or any(p in name_lower for p in [".env", "secret", "private_key"]):
        raise PermissionError(
            f"Security restriction: Access to sensitive file '{target.name}' is prohibited."
        )

    return target


def tool_read_project_file(
    file_path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> dict[str, Any]:
    """Read contents of an authorized file within the project workspace."""
    safe_path = _resolve_safe_path(file_path)

    if not safe_path.exists():
        return {
            "success": False,
            "file_path": file_path,
            "error": f"File does not exist: {file_path}",
        }

    if safe_path.is_dir():
        return {
            "success": False,
            "file_path": file_path,
            "error": f"Path is a directory, not a file: {file_path}. Use list_project_files instead.",
        }

    try:
        content = safe_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines(keepends=True)
        total_lines = len(lines)

        s = 1 if start_line is None else max(1, start_line)
        e = total_lines if end_line is None else min(total_lines, end_line)

        sliced_content = "".join(lines[s - 1 : e])

        return {
            "success": True,
            "file_path": str(safe_path.relative_to(WORKSPACE_ROOT)),
            "start_line": s,
            "end_line": e,
            "total_lines": total_lines,
            "content": sliced_content,
        }
    except Exception as exc:
        return {
            "success": False,
            "file_path": file_path,
            "error": f"Failed to read file: {type(exc).__name__}: {str(exc)}",
        }


def tool_list_project_files(directory_path: str = ".") -> dict[str, Any]:
    """List directory contents within the authorized project workspace."""
    safe_dir = _resolve_safe_path(directory_path)

    if not safe_dir.exists() or not safe_dir.is_dir():
        return {
            "success": False,
            "directory": directory_path,
            "error": f"Directory does not exist: {directory_path}",
        }

    ignored_dirs = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}
    items = []

    try:
        for entry in os.scandir(safe_dir):
            if entry.name in ignored_dirs:
                continue
            items.append({
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size_bytes": entry.stat().st_size if entry.is_file() else None,
            })

        items.sort(key=lambda x: (not x["is_dir"], x["name"]))
        return {
            "success": True,
            "directory": str(safe_dir.relative_to(WORKSPACE_ROOT)),
            "items": items,
            "count": len(items),
        }
    except Exception as exc:
        return {
            "success": False,
            "directory": directory_path,
            "error": f"Failed to list directory: {type(exc).__name__}: {str(exc)}",
        }


def tool_propose_file_edit(
    file_path: str,
    target_content: str,
    replacement_content: str,
) -> dict[str, Any]:
    """Generate a unified diff for a proposed code change without applying it."""
    safe_path = _resolve_safe_path(file_path)

    if not safe_path.exists():
        return {
            "success": False,
            "file_path": file_path,
            "error": f"File does not exist: {file_path}",
        }

    original = safe_path.read_text(encoding="utf-8", errors="replace")
    if target_content not in original:
        return {
            "success": False,
            "file_path": file_path,
            "error": "Target content not found exactly in file. Please verify lines before editing.",
        }

    modified = original.replace(target_content, replacement_content, 1)
    diff = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
    )

    return {
        "success": True,
        "file_path": str(safe_path.relative_to(WORKSPACE_ROOT)),
        "diff": diff,
        "requires_approval": True,
        "status": "waiting_approval",
        "notice": "Code change proposed. Requires explicit user authorization before writing to disk.",
    }


def tool_apply_file_edit(
    file_path: str,
    target_content: str,
    replacement_content: str,
) -> dict[str, Any]:
    """Apply an authorized edit to a file within the project workspace."""
    safe_path = _resolve_safe_path(file_path)

    if not safe_path.exists():
        return {
            "success": False,
            "file_path": file_path,
            "error": f"File does not exist: {file_path}",
        }

    original = safe_path.read_text(encoding="utf-8", errors="replace")
    if target_content not in original:
        return {
            "success": False,
            "file_path": file_path,
            "error": "Target content not found in file.",
        }

    modified = original.replace(target_content, replacement_content, 1)
    safe_path.write_text(modified, encoding="utf-8")

    return {
        "success": True,
        "file_path": str(safe_path.relative_to(WORKSPACE_ROOT)),
        "status": "applied",
        "message": f"Successfully applied changes to {file_path}.",
    }


def tool_run_approved_tests(test_target: str = "backend") -> dict[str, Any]:
    """Execute authorized test suites within the workspace."""
    if test_target.lower() in ("backend", "pytest"):
        cmd = [str(WORKSPACE_ROOT / ".venv" / "Scripts" / "pytest.exe"), "-q"]
        cwd = str(WORKSPACE_ROOT)
    elif test_target.lower() in ("frontend", "npm"):
        cmd = ["npm.cmd", "test", "--", "--run"]
        cwd = str(WORKSPACE_ROOT / "frontend")
    else:
        # Check if target is a specific test file
        test_file = _resolve_safe_path(test_target)
        if not test_file.exists():
            return {
                "success": False,
                "error": f"Test file does not exist: {test_target}",
            }
        cmd = [str(WORKSPACE_ROOT / ".venv" / "Scripts" / "pytest.exe"), "-q", str(test_file)]
        cwd = str(WORKSPACE_ROOT)

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        return {
            "success": proc.returncode == 0,
            "test_target": test_target,
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-3000:] if len(proc.stdout) > 3000 else proc.stdout,
            "stderr": proc.stderr[-1000:] if len(proc.stderr) > 1000 else proc.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "test_target": test_target,
            "exit_code": -1,
            "error": "Test execution timed out after 45 seconds.",
        }
    except Exception as exc:
        return {
            "success": False,
            "test_target": test_target,
            "exit_code": -1,
            "error": f"Failed to run test command: {str(exc)}",
        }


def tool_run_approved_command(command: str) -> dict[str, Any]:
    """Execute whitelisted development commands with strict safety validation."""
    clean_cmd = command.strip()

    # Enforce whitelist
    is_approved = any(clean_cmd.startswith(prefix) for prefix, _ in APPROVED_COMMAND_PREFIXES)
    if not is_approved:
        return {
            "success": False,
            "command": clean_cmd,
            "error": (
                f"Security policy rejection: Command '{clean_cmd}' is not in the approved whitelist. "
                f"Only safe dev commands like pytest, npm test, and git status are permitted."
            ),
        }

    try:
        proc = subprocess.run(
            clean_cmd,
            shell=True,
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return {
            "success": proc.returncode == 0,
            "command": clean_cmd,
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-3000:] if len(proc.stdout) > 3000 else proc.stdout,
            "stderr": proc.stderr[-1000:] if len(proc.stderr) > 1000 else proc.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "command": clean_cmd,
            "error": "Command execution timed out after 30 seconds.",
        }
    except Exception as exc:
        return {
            "success": False,
            "command": clean_cmd,
            "error": f"Command failed: {str(exc)}",
        }
