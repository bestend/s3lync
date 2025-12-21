# GitHub Actions Configuration

This document describes the automated workflows configured for s3lync.

## Workflows

### 1. Tests (`tests.yml`)
**Trigger:** Push to main/develop, Pull Requests

Runs comprehensive test suite on multiple Python versions and operating systems:
- **OS:** Ubuntu, macOS, Windows
- **Python:** 3.9, 3.10, 3.11, 3.12
- **Tests:** pytest with coverage reporting
- **Coverage:** Uploaded to Codecov

**Steps:**
1. Checkout code
2. Setup Python environment
3. Install dependencies with dev extras
4. Run pytest with coverage
5. Upload coverage reports

### 2. Lint (`tests.yml` - lint job)
**Trigger:** Push to main/develop, Pull Requests

Validates code quality:
- **Black:** Code formatting check
- **Ruff:** Linting and style checks
- **mypy:** Type checking

### 3. Documentation (`documentation.yml`)
**Trigger:** Push to main/develop, Pull Requests

Validates documentation:
- Checks for required documentation files
- Validates markdown syntax
- Checks for broken documentation links
- Runs markdownlint for style consistency

**Required files:**
- README.md
- README.KO.md
- CHANGELOG.md
- DEVELOPMENTS.md
- CONTRIBUTING.md
- LICENSE

### 4. Code Quality (`code-quality.yml`)
**Trigger:** Push to main/develop, Pull Requests

Comprehensive code quality checks:

**Security Scans:**
- Bandit: Security vulnerability detection
- Safety: Dependency vulnerability checking

**Coverage Analysis:**
- Test coverage with detailed reports
- HTML coverage report generation
- Codecov upload
- PR comments with coverage status

**Requirements:**
- Minimum coverage for green: 85%
- Minimum coverage for orange: 70%

### 5. Release (`release.yml`)
**Trigger:** Tag push (v0.1.0, 0.1.0, etc.)

Automated release and PyPI publishing:

**Steps:**
1. Create GitHub Release
2. Build Python distribution
3. Validate distribution
4. Publish to PyPI

**Requirements:**
- PyPI API token configured as `PYPI_API_TOKEN` secret

**Version Pattern:**
- `v[0-9]+.[0-9]+.[0-9]+` (e.g., v0.1.0)
- `[0-9]+.[0-9]+.[0-9]+` (e.g., 0.1.0)

### 6. Version Update (`update-version.yml`)
**Trigger:** Tag push

Automatically updates version in `pyproject.toml`:
- Extracts version from git tag
- Updates version string in pyproject.toml
- Commits changes
- Pushes back to repository

**Note:** Uses `github-actions[bot]` for commits

## Setup Instructions

### 1. GitHub Secrets Required

**For PyPI publishing (optional):**
```
PYPI_API_TOKEN: <your-pypi-token>
```

Get PyPI token from: https://pypi.org/help/#apitoken

### 2. Branch Protection Rules (Recommended)

Setup in GitHub repository settings:

- **main branch:**
  - Require status checks to pass before merging
  - Required checks:
    - Tests (all Python versions & OS)
    - Lint
    - Documentation
    - Code Quality

### 3. Codecov Setup (Optional)

1. Visit https://codecov.io/
2. Connect GitHub account
3. Enable s3lync repository
4. No additional setup needed - token handled automatically for public repos

## Running Workflows Manually

To trigger workflows manually via GitHub CLI:

```bash
# Trigger tests workflow
gh workflow run tests.yml

# Trigger code quality workflow
gh workflow run code-quality.yml

# Trigger documentation workflow
gh workflow run documentation.yml
```

## Workflow Status Badges

Add to README.md:

```markdown
[![Tests](https://github.com/bestend/s3lync/actions/workflows/tests.yml/badge.svg)](https://github.com/bestend/s3lync/actions/workflows/tests.yml)
[![Code Quality](https://github.com/bestend/s3lync/actions/workflows/code-quality.yml/badge.svg)](https://github.com/bestend/s3lync/actions/workflows/code-quality.yml)
[![codecov](https://codecov.io/gh/bestend/s3lync/branch/main/graph/badge.svg)](https://codecov.io/gh/bestend/s3lync)
```

## Troubleshooting

### Workflow Fails to Run
- Check branch name (main or develop)
- Verify .github/workflows/ directory exists
- Ensure YAML syntax is valid

### Tests Fail on Specific Python Version
- Check Python version support in pyproject.toml
- May need to update python-version matrix

### PyPI Publishing Fails
- Verify PYPI_API_TOKEN is set correctly
- Check token has upload permissions
- Ensure version doesn't already exist on PyPI

### Coverage Not Uploading
- Verify Codecov integration is active
- Check GITHUB_TOKEN permissions

## Best Practices

1. **Always run tests locally before pushing:**
   ```bash
   pytest tests/
   ```

2. **Check code quality before committing:**
   ```bash
   black src/ tests/
   ruff check src/ tests/
   mypy src/
   ```

3. **Use meaningful commit messages:**
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `test:` for tests
   - `chore:` for maintenance

4. **Tag releases properly:**
   ```bash
   git tag -a v0.1.0 -m "Release version 0.1.0"
   git push origin v0.1.0
   ```

5. **Keep dependencies updated:**
   - Regularly check for security updates
   - Use Safety workflow for vulnerability scanning

## Performance Optimization

### Caching
- Pip dependencies cached with setup-python action
- Speeds up workflow execution

### Matrix Strategy
- Python 3.9-3.12 tested in parallel
- OS matrix: Ubuntu, macOS, Windows

### Fail-Fast
- Set to false to run all matrix combinations
- Prevents early termination

## Future Enhancements

Consider adding:
- Docker build and push to Docker Hub
- Integration test workflows
- Performance benchmarking
- Documentation deployment to GitHub Pages
- Automated dependency updates (Dependabot)

---

For more information, visit:
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [confee GitHub Actions](https://github.com/bestend/confee/tree/main/.github/workflows)

