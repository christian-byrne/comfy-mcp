# Contributing to ComfyUI MCP Server

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/comfy-mcp.git
   cd comfy-mcp
   ```

2. **Set up development environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   ```

3. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

## Development Workflow

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes and add tests:**
   - Write code following the existing style
   - Add unit tests for new functionality
   - Update documentation if needed

3. **Run tests and checks:**
   ```bash
   # Run tests
   pytest
   
   # Check formatting
   black .
   
   # Check linting
   ruff check .
   
   # Type checking
   mypy comfy_mcp
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and create pull request:**
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style

- **Python:** Follow PEP 8, enforced by Black and Ruff
- **Docstrings:** Use Google-style docstrings
- **Type hints:** Required for all public functions
- **Tests:** Required for all new functionality

## Testing

- **Unit tests:** Test individual components in isolation
- **Integration tests:** Test components working together
- **Mark slow tests:** Use `@pytest.mark.slow` for long-running tests

## Documentation

- Update docstrings for any new or modified functions
- Add examples for new features
- Update README.md if needed

## Commit Message Guidelines

Follow conventional commits:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation changes
- `test:` adding tests
- `refactor:` code refactoring
- `style:` formatting changes

## Pull Request Process

1. Ensure all tests pass
2. Update documentation
3. Add changelog entry if significant
4. Request review from maintainers

## Questions?

Feel free to open an issue for any questions about contributing!