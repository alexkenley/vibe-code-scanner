"""Project language and framework detection."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

# Directories to always skip when walking the file tree
SKIP_DIRS = {
    "node_modules", ".venv", "venv", "env", "__pycache__", ".git",
    "dist", "build", ".next", ".nuxt", "vendor", "target",
    ".tox", ".mypy_cache", ".pytest_cache", "coverage",
}

# Map file extensions to language names
EXTENSION_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rb": "ruby",
    ".java": "java",
    ".rs": "rust",
    ".cs": "csharp",
    ".php": "php",
    ".kt": "kotlin",
    ".swift": "swift",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
}


@dataclass
class ProjectInfo:
    path: Path
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    has_dockerfile: bool = False
    has_git: bool = False


def detect_project(target: Path) -> ProjectInfo:
    """Analyze a project directory and return detected languages, frameworks, etc."""
    info = ProjectInfo(path=target.resolve())
    lang_counts: dict[str, int] = {}

    info.has_git = (target / ".git").is_dir()
    info.has_dockerfile = (target / "Dockerfile").is_file()

    # Walk the file tree once
    for root, dirs, files in os.walk(target):
        # Prune skipped directories in-place
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for f in files:
            ext = Path(f).suffix.lower()
            lang = EXTENSION_MAP.get(ext)
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

    # Languages with at least one file, sorted by count descending
    info.languages = sorted(lang_counts, key=lambda l: lang_counts[l], reverse=True)

    # Detect frameworks and package managers from config files
    _detect_frameworks(target, info)
    _detect_package_managers(target, info)

    return info


def _detect_frameworks(target: Path, info: ProjectInfo) -> None:
    """Detect frameworks from config files and dependency manifests."""
    # Next.js
    if (target / "next.config.js").is_file() or (target / "next.config.mjs").is_file():
        info.frameworks.append("nextjs")
    elif _package_json_has_dep(target, "next"):
        info.frameworks.append("nextjs")

    # React (without Next.js)
    if "nextjs" not in info.frameworks and _package_json_has_dep(target, "react"):
        info.frameworks.append("react")

    # Express
    if _package_json_has_dep(target, "express"):
        info.frameworks.append("express")

    # Supabase
    if _package_json_has_dep(target, "@supabase/supabase-js"):
        info.frameworks.append("supabase")
    elif _requirements_has_dep(target, "supabase"):
        info.frameworks.append("supabase")

    # Django
    if (target / "manage.py").is_file() or _requirements_has_dep(target, "django"):
        info.frameworks.append("django")

    # Flask
    if _requirements_has_dep(target, "flask"):
        info.frameworks.append("flask")

    # Rails
    if (target / "config" / "routes.rb").is_file():
        info.frameworks.append("rails")
    elif (target / "Gemfile").is_file():
        try:
            content = (target / "Gemfile").read_text(errors="ignore")
            if "rails" in content.lower():
                info.frameworks.append("rails")
        except OSError:
            pass


def _detect_package_managers(target: Path, info: ProjectInfo) -> None:
    """Detect which package managers are in use."""
    if (target / "package.json").is_file():
        if (target / "yarn.lock").is_file():
            info.package_managers.append("yarn")
        elif (target / "pnpm-lock.yaml").is_file():
            info.package_managers.append("pnpm")
        else:
            info.package_managers.append("npm")

    if (target / "requirements.txt").is_file() or (target / "Pipfile").is_file():
        info.package_managers.append("pip")

    if (target / "pyproject.toml").is_file():
        info.package_managers.append("pip")

    if (target / "Gemfile").is_file():
        info.package_managers.append("gem")

    if (target / "go.mod").is_file():
        info.package_managers.append("go")

    if (target / "Cargo.toml").is_file():
        info.package_managers.append("cargo")


def _package_json_has_dep(target: Path, package: str) -> bool:
    """Check if package.json contains a specific dependency."""
    pkg_path = target / "package.json"
    if not pkg_path.is_file():
        return False
    try:
        data = json.loads(pkg_path.read_text(errors="ignore"))
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        return package in deps
    except (json.JSONDecodeError, OSError):
        return False


def _requirements_has_dep(target: Path, package: str) -> bool:
    """Check if requirements.txt contains a specific dependency."""
    req_path = target / "requirements.txt"
    if not req_path.is_file():
        return False
    try:
        content = req_path.read_text(errors="ignore").lower()
        return package.lower() in content
    except OSError:
        return False
