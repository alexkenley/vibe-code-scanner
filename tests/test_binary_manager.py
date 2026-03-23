"""Tests for binary manager."""

import platform
from pathlib import Path
from unittest.mock import patch

from vibe_scan.binary_manager import BinaryManager, TOOL_DEFS


def test_binary_name_linux():
    with patch("platform.system", return_value="Linux"):
        assert BinaryManager._binary_name("gitleaks") == "gitleaks"


def test_binary_name_windows():
    with patch("platform.system", return_value="Windows"):
        assert BinaryManager._binary_name("gitleaks") == "gitleaks.exe"


def test_cache_dir_default():
    bm = BinaryManager()
    assert "vibe-scan" in str(bm.cache_dir)
    assert "bin" in str(bm.cache_dir)


def test_cache_dir_custom(tmp_path):
    bm = BinaryManager(cache_dir=tmp_path / "custom-cache")
    assert bm.cache_dir == tmp_path / "custom-cache"


def test_tool_defs_have_required_keys():
    for name, tool_def in TOOL_DEFS.items():
        assert "version" in tool_def, f"{name} missing version"
        assert "env_path" in tool_def, f"{name} missing env_path"
        assert "url_template" in tool_def, f"{name} missing url_template"
        assert "platform_map" in tool_def, f"{name} missing platform_map"


def test_ensure_tool_env_override(tmp_path):
    # Create a fake binary
    fake_binary = tmp_path / "gitleaks"
    fake_binary.write_text("fake")

    bm = BinaryManager(cache_dir=tmp_path / "cache")
    with patch.dict("os.environ", {"VIBE_SCAN_GITLEAKS_PATH": str(fake_binary)}):
        result = bm.ensure_tool("gitleaks")
        assert result == fake_binary


def test_ensure_tool_system_path(tmp_path):
    bm = BinaryManager(cache_dir=tmp_path / "cache")
    with patch("shutil.which", return_value="/usr/local/bin/gitleaks"):
        result = bm.ensure_tool("gitleaks")
        assert result == Path("/usr/local/bin/gitleaks")


def test_clear_cache(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "somefile").write_text("data")

    bm = BinaryManager(cache_dir=cache_dir)
    bm.clear_cache()
    assert not cache_dir.exists()
