# Contributing to DuckGuard

Thank you for your interest in contributing to DuckGuard! We welcome contributions from the community.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/duckguard.git
   cd duckguard
   ```
3. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

## Development Setup

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src/
black --check src/

# Run type checking
mypy src/
```

## Making Changes

1. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and add tests

3. **Run the test suite**:
   ```bash
   pytest
   ```

4. **Format your code**:
   ```bash
   black src/ tests/
   ruff check --fix src/ tests/
   ```

5. **Commit your changes**:
   ```bash
   git commit -m "feat: add your feature description"
   ```

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

## Pull Request Process

1. Update documentation if needed
2. Add tests for new functionality
3. Ensure all tests pass
4. Update the README if applicable
5. Submit your PR with a clear description

## Code Style

- Use [Black](https://black.readthedocs.io/) for formatting (line length: 100)
- Use [Ruff](https://docs.astral.sh/ruff/) for linting
- Add type hints to all functions
- Write docstrings for public APIs

## Reporting Issues

- Use GitHub Issues to report bugs
- Include Python version, OS, and DuckGuard version
- Provide a minimal reproducible example

## Feature Requests

- Open a GitHub Issue with the `enhancement` label
- Describe the use case and expected behavior

## Questions?

- Open a GitHub Discussion
- Tag maintainers if needed

Thank you for contributing!
