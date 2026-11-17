# Versioning and Release Guide

This project utilizes the Semantic Versioning standard. Version tags follow the format `vMAJOR.MINOR.PATCH`.

## 1. Nomenclature and Version Progression

The increment of each number reflects the scope and impact of the modifications on the codebase:

*   **MAJOR (`vX.0.0`):** Structural architectural modifications or changes that break backward compatibility (e.g., framework transitions, deep core refactoring).
*   **MINOR (`v1.X.0`):** Implementation of new functionalities in a backward-compatible manner (e.g., integration of new analytical modules, such as the phylogeny module).
*   **PATCH (`v1.2.X`):** Bug fixes and performance optimizations that do not alter the expected interfaces and behavior of the application.

## 2. Tagging the Latest Version (Current Branch)

To demarcate a release from the current state (*HEAD*) of the active working branch:

```bash
# Annotated tag creation
git tag -a v1.2.0 -m "Concise description of the release scope"

# Exclusive synchronization of the tag with the remote repository
git push origin v1.2.0
```

## 3. Retroactive Tagging (Specific Branch or Commit)

To formalize a release at a previous state in the Git history, without the need to switch the current working branch (checkout). It is strictly recommended to use the merge commit hash to ensure precision, although the branch name is also accepted.
```bash
# Tag creation referencing a specific commit (hash) or branch
git tag -a v1.1.0 0166797 -m "Concise description of the release"
# or
git tag -a v1.1.0 branch-name -m "Concise description of the release"

# Exclusive synchronization of the tag with the remote repository
git push origin v1.1.0
```