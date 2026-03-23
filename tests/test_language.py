"""Tests for language and framework detection."""

from pathlib import Path

from vibe_scan.language import detect_project


def test_detect_python_project(python_test_app):
    info = detect_project(python_test_app)
    assert "python" in info.languages


def test_detect_js_project(js_test_app):
    info = detect_project(js_test_app)
    assert any(
        lang in info.languages for lang in ("javascript", "typescript")
    )


def test_detect_typescript_project(typescript_test_app):
    info = detect_project(typescript_test_app)
    assert "typescript" in info.languages


def test_detect_supabase_framework(supabase_test_app):
    if not supabase_test_app.exists():
        return
    info = detect_project(supabase_test_app)
    assert "supabase" in info.frameworks


def test_detect_empty_dir(tmp_path):
    info = detect_project(tmp_path)
    assert info.languages == []
    assert info.frameworks == []


def test_detect_package_managers(js_test_app):
    info = detect_project(js_test_app)
    assert any(pm in info.package_managers for pm in ("npm", "yarn", "pnpm"))


def test_detect_has_git(test_apps_dir):
    # The repo root has .git, test-apps subdirs do not
    repo_root = test_apps_dir.parent
    info = detect_project(repo_root)
    assert info.has_git is True
