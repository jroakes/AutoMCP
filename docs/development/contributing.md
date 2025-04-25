# Contributing to AutoMCP

Thank you for your interest in contributing to AutoMCP! This guide will help you get started with contributing to the project.

## Setting Up Development Environment

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/yourusername/AutoMCP.git
   cd AutoMCP
   ```

2. Install in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

3. Install development dependencies:
   ```bash
   pip install pytest pytest-cov black isort mypy
   ```

## Code Style

AutoMCP follows these code style guidelines:

- [Black](https://black.readthedocs.io/) for code formatting
- [isort](https://pycqa.github.io/isort/) for import sorting
- [mypy](http://mypy-lang.org/) for static type checking
- [PEP 8](https://www.python.org/dev/peps/pep-0008/) for code style
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) for docstrings

You can automatically format your code with:

```bash
black src tests
isort src tests
```

## Testing

Run tests with pytest:

```bash
pytest
```

For coverage report:

```bash
pytest --cov=src
```

## Pull Request Process

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit them:
   ```bash
   git commit -m "Add feature X"
   ```

3. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Open a pull request against the `main` branch of the original repository

## Pull Request Guidelines

- Include tests for new features or bug fixes
- Update documentation if necessary
- Follow the code style guidelines
- Keep pull requests focused on a single topic
- Write clear commit messages

## Documentation

When adding new features, please update the relevant documentation:

1. Update or add docstrings for public classes and methods
2. Update the relevant documentation in the `docs/` directory
3. Add examples if appropriate

## Feature Requests and Bug Reports

For feature requests or bug reports, please open an issue on GitHub with a clear description of the feature or bug.

## License

By contributing to AutoMCP, you agree that your contributions will be licensed under the project's license. 