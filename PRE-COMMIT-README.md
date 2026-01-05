# Pre-commit Setup and Usage

## What is Pre-commit?

Pre-commit is a framework for managing and maintaining multi-language pre-commit hooks. It allows you to automatically run checks and fixes on your code before each commit, ensuring code quality and consistency across the project.

## Installation

To install pre-commit, ensure you have Python installed and run:

```bash
pip install pre-commit
```

Or if using Poetry (recommended for this project):

```bash
poetry add --group dev pre-commit
```

## Enabling Pre-commit

After installation, install the pre-commit hooks defined in this repository:

```bash
pre-commit install
```

This will set up the hooks to run automatically on each commit.

## Pre-commit Workflow

This repository uses pre-commit to enforce code quality through the following checks:

- **Environment Checks**: Verifies Poetry environment and dependencies
- **Formatting**: Automatically formats code with Black and Django templates with djLint
- **Import Sorting**: Organizes Python imports with isort
- **Linting**: Checks code style and potential issues with flake8 (including Django-specific rules)
- **File Validation**: Verifies YAML, JSON, TOML, XML, and other file formats
- **Security Checks**: Detects private keys and merge conflicts
- **Django Specific**: Runs collectstatic and tests to ensure Django application integrity

The hooks are configured to run in the `pre-commit` stage, providing immediate feedback before code is committed.

## Continuous Integration

Some hooks (environment checks, Django collectstatic, and tests) are skipped in CI environments to avoid redundancy with existing CI pipelines. The configuration checks for the `GITHUB_ACTIONS` environment variable to determine the execution context.

## Configuration

The authoritative configuration for all pre-commit hooks is defined in [.pre-commit-config.yaml](.pre-commit-config.yaml).

## Manual Runs

To manually run all pre-commit hooks:

```bash
pre-commit run --all-files
```

To update hooks to their latest versions:

```bash
pre-commit autoupdate
```

This setup helps keep the codebase clean, consistent, and easy to maintain for everyone.
