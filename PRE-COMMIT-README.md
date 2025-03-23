# Pre-commit Workflow

## Overview

This project uses pre-commit hooks to ensure code quality and consistency. The hooks are configured to:

1. **Automatically fix** formatting issues when possible (won't fail the commit)
2. **Report** issues that require manual intervention (will fail the commit)

## Hook Types

### Auto-fixing Hooks (Commit Stage)

These hooks will automatically fix issues without failing the commit:

- `trailing-whitespace`: Removes trailing whitespace
- `end-of-file-fixer`: Ensures files end with a newline
- `mixed-line-ending`: Normalizes line endings
- `black`: Formats Python code
- `isort`: Sorts Python imports
- `djlint-django`: Formats Django HTML templates

### Analysis Hooks (Commit and Manual Stages)

These hooks require manual intervention and will fail the commit if issues are found:

- `flake8`: Checks Python code for errors and style issues
- `check-yaml`: Validates YAML files
- `check-added-large-files`: Prevents committing large files
- `check-json`, `check-toml`, `check-xml`: Validates various file formats
- `check-merge-conflict`: Checks for unresolved merge conflicts
- `detect-private-key`: Prevents committing private keys

### Django-specific Hooks

- `django-collectstatic`: Runs Django's collectstatic command (commit stage)
- `django-test`: Runs Django tests (manual stage only)

## VSCode Tasks

Three VSCode tasks are available to run pre-commit hooks:

1. **Run Pre-commit (Auto-fix)**: Runs only the commit stage hooks that auto-fix issues
   ```
   poetry run pre-commit run --hook-stage commit
   ```

2. **Run Pre-commit (All Checks)**: Runs all hooks on all files
   ```
   poetry run pre-commit run --all-files
   ```

3. **Run Pre-commit Manual Hooks**: Runs only the manual stage hooks
   ```
   poetry run pre-commit run --hook-stage manual
   ```

## Workflow Recommendations

1. Before committing, run the **Auto-fix** task to automatically format your code
2. If you want to check for issues that require manual intervention, run the **All Checks** task
3. Run the **Manual Hooks** task before pushing to ensure tests pass

## Customizing Pre-commit Configuration

The pre-commit configuration is defined in `.pre-commit-config.yaml`. You can modify this file to:

- Add or remove hooks
- Change hook arguments
- Adjust which hooks run in which stages

For more information, see the [pre-commit documentation](https://pre-commit.com/).
