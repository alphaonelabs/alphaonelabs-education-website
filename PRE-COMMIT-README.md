# Pre-Commit Workflow & Configuration

This document explains how **pre-commit** is used in this repository, how to install and enable it, and how it integrates with local development and CI.



## What is pre-commit?

**pre-commit** is a framework for managing and running Git hooks. It helps ensure code quality and consistency by automatically running checks (such as formatting, linting, and static analysis) before code is committed.

Benefits:

* Catches issues early, before they reach CI
* Enforces consistent formatting and style
* Reduces review churn
* Keeps the codebase clean and predictable



## Installation & Setup

### 1. Install pre-commit

You can install `pre-commit` using pip:

pip install pre-commit


Or, if you use a virtual environment or dependency manager (recommended), add it to your development dependencies.

Verify installation:


pre-commit --version




### 2. Enable pre-commit hooks

From the root of the repository, run:


pre-commit install


This installs the Git hook so that checks run automatically on every `git commit`.



## Pre-Commit Workflow in This Repository

This repository uses pre-commit to enforce a consistent and reliable development workflow.

### What happens on `git commit`?

When you run:


git commit


pre-commit will:

1. Detect which files have changed
2. Run the configured hooks only on those files
3. Block the commit if any hook fails

You must fix the reported issues and re-commit.



### Types of Checks Used

The hooks configured in this repository typically include:

#### 1. Formatting

* Automatically formats code to match project standards
* Prevents unnecessary diffs caused by inconsistent formatting

#### 2. Linting

* Detects common bugs and style issues
* Enforces best practices

#### 3. Django Checks (if applicable)

* Runs Django-specific validations (such as `manage.py check`)
* Ensures settings and configurations are valid

#### 4. General Sanity Checks

* Trailing whitespace removal
* End-of-file newline enforcement
* YAML / JSON validation

> The exact hooks and versions are defined in `.pre-commit-config.yaml`.



## Manual Usage

You can run pre-commit manually without creating a commit.

### Run on all files


pre-commit run --all-files


Useful when:

* Setting up the repository for the first time
* After rebasing or pulling large changes
* Before pushing a big refactor

### Run a specific hook


pre-commit run <hook-id>


Example:
pre-commit run black




## Skipping Hooks (Not Recommended)

In rare cases, you may skip pre-commit checks:

bash
git commit --no-verify


Use this sparingly.CI may still fail if hooks are skipped locally.


## CI Integration

Pre-commit hooks are also expected to run in **Continuous Integration (CI)**.

Typical CI behavior:

* CI runs `pre-commit run --all-files`
* Ensures the same checks enforced locally are enforced in CI
* Prevents unformatted or invalid code from being merged

This guarantees consistency between local development and CI validation.



## Configuration Reference

All hook definitions, versions, and arguments are maintained in:


.pre-commit-config.yaml


If you need to:

* Add a new tool
* Update hook versions
* Modify hook behavior

Make changes **only** in `.pre-commit-config.yaml` and re-run:


pre-commit install
pre-commit run --all-files
```

---

## Troubleshooting

### Hooks fail after pulling changes

Run:


pre-commit clean
pre-commit run --all-files

### Hooks not running at all

Ensure hooks are installed:


pre-commit install




## Summary

* pre-commit enforces quality checks before commits
* Install once, hooks run automatically
* Same checks run locally and in CI
* Configuration lives in `.pre-commit-config.yaml`

Keeping pre-commit enabled helps maintain a clean, consistent, and reliable codebase.
