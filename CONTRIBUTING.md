# Contributing

Contributions to the CLI, scripts, tests, and documentation are welcome. Run `make test` before opening a pull request.

Use synthetic examples and temporary directories in tests. The repository's `skills/skills-sync/` companion skill is intentional; do not commit a real skills snapshot, `inventory/`, `snapshots/`, a vault marker or manifest, credentials, or another person's skill files. Preserve the dedicated-vault checks, snapshot integrity verification, and backup behavior.
