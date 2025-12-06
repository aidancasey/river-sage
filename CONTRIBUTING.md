# Contributing to River Guru

Thank you for considering contributing to River Guru! This document provides guidelines for contributing to the project.

## Ways to Contribute

- 🐛 Report bugs
- 💡 Suggest new features or improvements
- 📝 Improve documentation
- 🔧 Submit code changes
- 🌊 Add support for new river stations
- 🧪 Add tests

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- AWS Account (for deployment testing)
- AWS SAM CLI

### Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/river-data-scraper.git
cd river-data-scraper
```

2. **Set up Python environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

3. **Set up web app**
```bash
cd web
npm install
cd ..
```

4. **Run tests**
```bash
pytest
```

5. **Start development server (web app)**
```bash
make dev-web
# Or: cd web && npm run dev
```

## Development Workflow

### Making Changes

1. **Create a branch**
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

2. **Make your changes**
   - Write clear, readable code
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
```bash
# Run Python tests
pytest

# Run web app locally
make dev-web

# Test SAM build
make build
```

4. **Commit your changes**
```bash
git add .
git commit -m "Clear, concise commit message"
```

### Commit Message Guidelines

Use clear, descriptive commit messages:

```
Add support for Carrigadrohid station
Fix PDF parsing error for edge cases
Update deployment documentation
Refactor data aggregation logic
```

## Pull Request Process

1. **Update documentation** - If you've added features, update README.md and other docs
2. **Ensure tests pass** - All tests should pass before submitting
3. **Update CHANGELOG** - Add a note about your changes (if applicable)
4. **Submit PR** - Push your branch and create a pull request
5. **Respond to feedback** - Address any review comments

### Pull Request Template

When creating a PR, please include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Performance improvement

## Testing
How has this been tested?

## Checklist
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] Code follows existing style
- [ ] No sensitive data committed
```

## Code Style

### Python
- Follow [PEP 8](https://pep8.org/)
- Use type hints where appropriate
- Document functions with docstrings
- Keep functions focused and small

### JavaScript/Vue
- Follow existing Vue.js patterns
- Use Composition API (not Options API)
- Keep components small and focused
- Use TypeScript-style JSDoc comments

### General
- Write self-documenting code
- Add comments for complex logic
- Keep files under 500 lines when possible
- Use meaningful variable names

## Testing

- Write unit tests for new functionality
- Ensure existing tests still pass
- Test edge cases and error conditions
- Mock external services (S3, API calls)

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_http_connector.py -v

# Run with coverage
pytest --cov=src tests/
```

## Adding New River Stations

To add support for a new river station:

1. Add station configuration to `template.yaml`
2. Create parser for the station's data format (if different)
3. Add tests for the new station
4. Update documentation
5. Test deployment

See existing stations as examples.

## Documentation

- Update README.md for user-facing changes
- Update DEPLOYMENT_GUIDE.md for deployment changes
- Add inline comments for complex code
- Keep documentation current with code

## Questions?

- Open a [discussion](../../discussions) for general questions
- Open an [issue](../../issues) for bug reports or feature requests
- Review existing issues before creating new ones

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Provide constructive feedback
- Focus on the work, not the person

## License

By contributing to River Guru, you agree that your contributions will be licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
