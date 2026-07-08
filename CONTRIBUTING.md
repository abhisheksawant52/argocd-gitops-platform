# Contributing

Thanks for your interest in contributing! This project welcomes issues, feature
requests, and pull requests.

## Ground Rules

- Be respectful — see our [Code of Conduct](CODE_OF_CONDUCT.md).
- Discuss significant changes in an issue before opening a large PR.
- Keep pull requests focused and small where possible.

## Development Workflow

1. Fork the repository and create a feature branch from `main`:
   ```bash
   git checkout -b feat/short-description
   ```
2. Install dependencies and set up the toolchain (see the `README.md` and
   `Makefile`).
3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```
4. Make your change with clear, focused commits.
5. Run linters/tests locally:
   ```bash
   make lint
   make test
   ```
6. Push your branch and open a pull request against `main`.

## Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add support for X
fix: correct handling of Y
docs: clarify Z
chore: bump dependencies
```

## Pull Request Checklist

- [ ] Change is covered by tests where applicable
- [ ] `make lint` and `make test` pass
- [ ] Documentation updated (README/docs)
- [ ] PR description explains the motivation and approach

## Reporting Bugs & Requesting Features

Use the issue templates in `.github/ISSUE_TEMPLATE/`. Provide as much context
as possible (versions, logs, reproduction steps).

## License

By contributing, you agree that your contributions will be licensed under the
project's [MIT License](LICENSE).
