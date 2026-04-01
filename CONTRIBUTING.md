# Contributing to WebVM

Thank you for your interest in contributing to WebVM!

## How to Contribute

### Reporting Bugs

- Check the [issue tracker](https://github.com/quickemu-project/webvm/issues) before opening a new issue
- Include your OS version, QEMU version, browser, and steps to reproduce
- Run `journalctl --user -u webvm -n 50` and include relevant log output

### Suggesting Features

Open a discussion or feature request on GitHub. Since WebVM targets the single-user homelab use case, the scope is intentionally focused.

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes with appropriate tests
4. Ensure code is formatted and commented
5. Submit a pull request against `master`

### Code Style

- Python: Follow [PEP 8](https://pep8.org/). Keep functions short and documented with docstrings.
- JavaScript: Vanilla JS, no frameworks. ES6+ syntax is fine.
- Jinja2 templates: Keep logic minimal; push logic into Python where possible.
- Comments: Write in English for all code and documentation.

### Development Setup

See [docs/DEVELOP.md](./docs/DEVELOP.md) for the local development setup.

## Repository Structure

```
src/              # Python backend (Flask, QEMU runner, QMP client)
web/              # Frontend (Jinja2 templates, vanilla JS, CSS)
docs/             # Documentation (INSTALL, USAGE, DEVELOP)
contrib/          # Distribution files (systemd service, packaging)
```

## Dependency Policy

Python dependencies are kept minimal. Flask is the only required runtime dependency; all other modules use the Python standard library.
