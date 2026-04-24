"""Helpers for keeping generated public artifacts free of local-only details."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable


def _as_resolved_path(value: str) -> Path | None:
    try:
        return Path(value).expanduser().resolve()
    except (OSError, RuntimeError):
        return None


def public_command_token(value: str, *, repo_root: Path) -> str:
    """Return a display-safe command token for generated reports."""
    text = str(value)
    candidate = _as_resolved_path(text)
    repo = repo_root.resolve()
    if candidate is not None:
        try:
            return str(candidate.relative_to(repo))
        except ValueError:
            pass
        if candidate.is_absolute() and candidate.name:
            return candidate.name

    repo_text = str(repo)
    if repo_text in text:
        text = text.replace(repo_text, ".")
    home = str(Path.home())
    if home and home in text:
        text = text.replace(home, "~")
    return text


def public_command(command: Iterable[str], *, repo_root: Path) -> list[str]:
    return [public_command_token(part, repo_root=repo_root) for part in command]


def public_environment_path(value: str, *, repo_root: Path) -> str:
    return public_command_token(value, repo_root=repo_root)


def sanitize_public_text(text: str, *, repo_root: Path) -> str:
    """Redact local workspace details from stdout/stderr captured in artifacts."""
    sanitized = str(text)
    repo = str(repo_root.resolve())
    if repo:
        sanitized = sanitized.replace(repo, ".")
    home = str(Path.home())
    if home:
        sanitized = sanitized.replace(home, "~")

    replacements = (
        (r"/Users/[^\s`'\")]+", "<local-home>"),
        (r"/home/(?!runner/)[^\s`'\")]+", "<local-home>"),
        (r"/private/var/folders/[^\s`'\")]+", "<local-temp>"),
        (r"/var/folders/[^\s`'\")]+", "<local-temp>"),
        (r"/tmp/[^\s`'\")]+", "<tmp>"),
        (r"/home/runner/work/_temp/[^\s`'\")]+", "<github-temp>"),
        (r"/home/runner/work/[^\s`'\")]+", "<github-workspace>"),
        (r"/opt/hostedtoolcache/[^\s`'\")]+", "<github-toolcache>"),
    )
    for pattern, replacement in replacements:
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized
