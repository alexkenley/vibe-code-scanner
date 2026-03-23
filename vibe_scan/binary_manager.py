"""Auto-download and cache Gitleaks/Trivy binaries."""

import io
import os
import platform
import shutil
import stat
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn

console = Console(stderr=True)

# Default cache location (respects XDG on Linux)
DEFAULT_CACHE_DIR = Path(
    os.environ.get("VIBE_SCAN_CACHE_DIR")
    or os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")
) / "vibe-scan" / "bin"

# Tool definitions with pinned versions
TOOL_DEFS = {
    "gitleaks": {
        "version": "8.24.3",
        "env_path": "VIBE_SCAN_GITLEAKS_PATH",
        "env_version": "VIBE_SCAN_GITLEAKS_VERSION",
        "url_template": (
            "https://github.com/gitleaks/gitleaks/releases/download/"
            "v{version}/gitleaks_{version}_{os}_{arch}.tar.gz"
        ),
        "windows_url_template": (
            "https://github.com/gitleaks/gitleaks/releases/download/"
            "v{version}/gitleaks_{version}_{os}_{arch}.zip"
        ),
        "platform_map": {
            ("Linux", "x86_64"): ("linux", "x64"),
            ("Linux", "aarch64"): ("linux", "arm64"),
            ("Darwin", "x86_64"): ("darwin", "x64"),
            ("Darwin", "arm64"): ("darwin", "arm64"),
            ("Windows", "AMD64"): ("windows", "x64"),
        },
    },
    "trivy": {
        "version": "0.62.1",
        "env_path": "VIBE_SCAN_TRIVY_PATH",
        "env_version": "VIBE_SCAN_TRIVY_VERSION",
        "url_template": (
            "https://github.com/aquasecurity/trivy/releases/download/"
            "v{version}/trivy_{version}_{os}-{arch}.tar.gz"
        ),
        "windows_url_template": (
            "https://github.com/aquasecurity/trivy/releases/download/"
            "v{version}/trivy_{version}_{os}-{arch}.zip"
        ),
        "platform_map": {
            ("Linux", "x86_64"): ("Linux", "64bit"),
            ("Linux", "aarch64"): ("Linux", "ARM64"),
            ("Darwin", "x86_64"): ("macOS", "64bit"),
            ("Darwin", "arm64"): ("macOS", "ARM64"),
            ("Windows", "AMD64"): ("Windows", "64bit"),
        },
    },
}


class BinaryManager:
    """Manages auto-downloading and caching of external tool binaries."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR

    def ensure_tool(self, name: str) -> Path:
        """Return path to a tool binary, downloading if needed.

        Resolution order:
        1. Environment variable override (e.g. VIBE_SCAN_GITLEAKS_PATH)
        2. System PATH
        3. Local cache
        4. Download from GitHub Releases
        """
        tool_def = TOOL_DEFS[name]

        # 1. Env var override
        env_path = os.environ.get(tool_def["env_path"])
        if env_path:
            p = Path(env_path)
            if p.is_file():
                return p
            raise FileNotFoundError(
                f"{tool_def['env_path']}={env_path} does not exist"
            )

        # 2. System PATH
        system_path = shutil.which(name)
        if system_path:
            return Path(system_path)

        # 3. Local cache
        version = os.environ.get(tool_def["env_version"]) or tool_def["version"]
        binary_name = self._binary_name(name)
        cached = self.cache_dir / f"{name}-{version}" / binary_name
        if cached.is_file():
            return cached

        # 4. Download
        return self._download(name, version)

    def clear_cache(self) -> None:
        """Remove all cached binaries."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            console.print(f"Cleared cache at {self.cache_dir}")

    def _download(self, name: str, version: str) -> Path:
        """Download a tool binary from GitHub Releases."""
        tool_def = TOOL_DEFS[name]
        os_name, arch = self._get_platform(name)
        is_windows = platform.system() == "Windows"

        if is_windows:
            url = tool_def["windows_url_template"].format(
                version=version, os=os_name, arch=arch
            )
        else:
            url = tool_def["url_template"].format(
                version=version, os=os_name, arch=arch
            )

        dest_dir = self.cache_dir / f"{name}-{version}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        binary_name = self._binary_name(name)

        console.print(
            f"[bold]Downloading {name} v{version} "
            f"for {platform.system()}/{platform.machine()}...[/bold]"
        )

        try:
            archive_data = self._download_url(url)
        except Exception as e:
            raise RuntimeError(
                f"Failed to download {name} v{version} from {url}\n"
                f"Error: {e}\n"
                f"You can manually install {name} and add it to your PATH, or set "
                f"{tool_def['env_path']} to point to the binary."
            ) from e

        # Extract binary
        binary_path = dest_dir / binary_name
        if url.endswith(".zip"):
            self._extract_zip(archive_data, name, binary_path)
        else:
            self._extract_tar(archive_data, name, binary_path)

        # Make executable
        if not is_windows:
            binary_path.chmod(binary_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        console.print(f"[green]Cached at {binary_path}[/green]")
        return binary_path

    def _download_url(self, url: str) -> bytes:
        """Download a URL with progress bar."""
        req = urllib.request.Request(url, headers={"User-Agent": "vibe-scan"})
        response = urllib.request.urlopen(req)
        total = int(response.headers.get("Content-Length", 0))

        with Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Downloading", total=total)
            chunks = []
            while True:
                chunk = response.read(8192)
                if not chunk:
                    break
                chunks.append(chunk)
                progress.update(task, advance=len(chunk))

        return b"".join(chunks)

    def _extract_tar(self, data: bytes, tool_name: str, dest: Path) -> None:
        """Extract a tool binary from a tar.gz archive."""
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            for member in tar.getmembers():
                if member.name == tool_name or member.name.endswith(f"/{tool_name}"):
                    member.name = dest.name
                    tar.extract(member, dest.parent)
                    return
        raise RuntimeError(f"Binary '{tool_name}' not found in archive")

    def _extract_zip(self, data: bytes, tool_name: str, dest: Path) -> None:
        """Extract a tool binary from a zip archive."""
        binary_name = f"{tool_name}.exe"
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in zf.namelist():
                if name == binary_name or name.endswith(f"/{binary_name}"):
                    with zf.open(name) as src, open(dest, "wb") as dst:
                        dst.write(src.read())
                    return
        raise RuntimeError(f"Binary '{binary_name}' not found in archive")

    def _get_platform(self, name: str) -> tuple[str, str]:
        """Get (os, arch) tuple for the current platform mapped to release naming."""
        tool_def = TOOL_DEFS[name]
        system = platform.system()
        machine = platform.machine()
        key = (system, machine)

        mapping = tool_def["platform_map"]
        if key not in mapping:
            raise RuntimeError(
                f"Unsupported platform: {system}/{machine}. "
                f"Supported: {list(mapping.keys())}"
            )
        return mapping[key]

    @staticmethod
    def _binary_name(name: str) -> str:
        """Return the binary filename for the current platform."""
        if platform.system() == "Windows":
            return f"{name}.exe"
        return name
