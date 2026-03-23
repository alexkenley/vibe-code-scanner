# Publishing vibe-scan to PyPI

## Prerequisites

1. Create a free account at https://pypi.org/account/register/
2. Enable 2FA on your account (required by PyPI)
3. Create an API token at https://pypi.org/manage/account/token/
   - Scope: "Entire account" for the first upload, then you can create a project-scoped token
   - Save the token somewhere safe — it's shown only once

## First-Time Setup

Install the build and upload tools:

```bash
pip install build twine
```

## Building

From the repo root:

```bash
python -m build
```

This creates two files in `dist/`:
- `vibe_scan-0.3.0.tar.gz` — source distribution
- `vibe_scan-0.3.0-py3-none-any.whl` — wheel (pre-built package)

## Testing with TestPyPI (Optional but Recommended)

Before publishing to the real PyPI, test on TestPyPI:

1. Create a separate account at https://test.pypi.org/account/register/
2. Create an API token there too
3. Upload:

```bash
twine upload --repository testpypi dist/*
```

4. Test installing from TestPyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ vibe-scan
```

Note: Dependencies like semgrep won't be on TestPyPI, so the install may partially fail. This is just to verify the package itself uploads correctly.

## Publishing to PyPI

```bash
twine upload dist/*
```

When prompted:
- Username: `__token__`
- Password: paste your API token (starts with `pypi-`)

Alternatively, store your token so you don't have to paste it each time:

```bash
# Create ~/.pypirc
cat > ~/.pypirc << 'EOF'
[pypi]
username = __token__
password = pypi-YOUR-TOKEN-HERE
EOF
chmod 600 ~/.pypirc
```

Then just `twine upload dist/*` with no prompts.

## Verifying

After upload, check it's live:

```bash
pip install vibe-scan
vibe-scan --version
```

Your package page will be at: https://pypi.org/project/vibe-scan/

## Releasing a New Version

1. Update the version in two places:
   - `pyproject.toml` → `version = "0.4.0"`
   - `vibe_scan/__init__.py` → `__version__ = "0.4.0"`

2. Commit and tag:

```bash
git add pyproject.toml vibe_scan/__init__.py
git commit -m "Bump version to 0.4.0"
git tag v0.4.0
git push && git push --tags
```

3. Clean old builds, rebuild, and upload:

```bash
rm -rf dist/
python -m build
twine upload dist/*
```

## Troubleshooting

**"File already exists"** — You can't re-upload the same version. Bump the version number.

**"Invalid API token"** — Make sure you're using `__token__` as the username (literally that string), and the full token starting with `pypi-` as the password.

**"Package name taken"** — Check https://pypi.org/project/vibe-scan/ . If someone else took the name, you'll need to rename the package in `pyproject.toml`.
