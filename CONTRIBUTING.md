# Contributing to s3lync

Thank you for your interest in contributing to s3lync! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback

## Getting Started

### Development Setup

1. Clone the repository
```bash
git clone https://github.com/bestend/s3lync.git
cd s3lync
```

2. Create a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install development dependencies
```bash
pip install -e ".[dev]"
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/s3lync tests/

# Run specific test file
pytest tests/test_s3object.py
```

### Code Quality

```bash
# Format code with Black
black src/ tests/

# Lint with Ruff
ruff check src/ tests/ --fix

# Type checking with mypy
mypy src/
```

## Making Changes

### Branch Naming

- Feature: `feature/description`
- Bug fix: `bugfix/description`
- Documentation: `docs/description`

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add support for multipart uploads
fix: resolve hash mismatch in ETag comparison
docs: update API reference
```

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add or update tests as needed
5. Ensure all tests pass: `pytest`
6. Ensure code quality: `black`, `ruff`, `mypy`
7. Submit a pull request with a clear description

## Testing Guidelines

- Write tests for new features
- Update tests when modifying existing code
- Aim for >80% code coverage
- Use descriptive test names

Example test structure:
```python
def test_feature_success_case(self):
    """Describe what is being tested."""
    # Setup
    # Execute
    # Assert
```

## Documentation

- Update README.md for user-facing changes
- Add docstrings to new functions and classes
- Use Google-style docstrings:

```python
def function(param1: str, param2: int) -> bool:
    """Short description.
    
    Longer description if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When value is invalid
    """
```

## Reporting Issues

When reporting bugs, please include:

- Python version
- s3lync version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error traceback (if applicable)

## Questions?

Feel free to open an issue or discussion for questions or suggestions!

Thank you for contributing! 🎉

