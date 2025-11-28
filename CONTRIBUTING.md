# Contributing to Garbage Truck Tracker

First off, thank you for considering contributing to Garbage Truck Tracker! 🎉

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### 🐛 Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title** describing the issue
- **Steps to reproduce** the behavior
- **Expected behavior** vs actual behavior
- **Screenshots** if applicable
- **Environment** (OS, Python version, etc.)

### 💡 Suggesting Features

Feature suggestions are welcome! Please include:

- **Clear description** of the feature
- **Use case** - why is this needed?
- **Possible implementation** if you have ideas

### 🔧 Pull Requests

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit PR

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/garbage-truck-tracker.git
cd garbage-truck-tracker

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies

# Create .env file
cp .env.example .env

# Run tests
python tests/test_api.py

# Start development server
uvicorn app.main:app --reload
```

## Pull Request Process

1. **Update documentation** if needed
2. **Add tests** for new features
3. **Run all tests** and ensure they pass
4. **Update README.md** if adding new features
5. **Request review** from maintainers

### PR Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] No merge conflicts

## Style Guidelines

### Python Code Style

- Follow **PEP 8**
- Use **type hints**
- Write **docstrings** for functions
- Keep functions **small and focused**

```python
# Good example
def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate distance between two points using Haversine formula.
    
    Args:
        lat1, lng1: First point coordinates
        lat2, lng2: Second point coordinates
    
    Returns:
        Distance in meters
    """
    # Implementation...
```

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add push notification support
fix: correct ETA calculation for slow speeds
docs: update API documentation
test: add tests for alert system
refactor: simplify location service
```

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation
- `refactor/description` - Code refactoring

## Questions?

Feel free to open an issue with the `question` label or reach out to maintainers.

---

Thank you for contributing! 🚛