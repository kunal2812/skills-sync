# Skills Sync

Keep your AI skills available across tools, accounts, and devices without manually reinstalling the same folders each time.

## Why this exists

Using more than one AI coding tool—or separate work and personal accounts—often means maintaining the same skills in several places. A new laptop or a fresh installation means copying them all over again. Skills Sync was created to take a snapshot of portable `SKILL.md` folders in one place and copy them into another supported tool when you need them. It does not require a new GitHub repository or upload your skills to this code repository.

The tool handles **cross-tool copying** locally. For **cross-device sync**, put its dedicated folder inside a private Obsidian vault and use Obsidian Sync. Skills Sync does not operate Obsidian Sync or sync accounts by itself.

## What it supports

Built-in global skill folders: Codex, Claude Code, Cursor, Gemini CLI, and the shared `~/.agents/skills` directory. You can also point `--root` at another tool's skills folder. Skills must be directories containing `SKILL.md`; their supporting files are copied with them. Provider-specific plugins, MCP credentials, account settings, and app/cloud skills are **not** translated between tools.

Requires Python 3.10+; no Python packages, GitHub account, or AI-tool login is required for portable skill syncing.

## Quick start

From this repository checkout (use `python3` instead of `python` where appropriate):

```bash
python skills-sync init
python skills-sync tools
python skills-sync snapshot --from codex
python skills-sync sync --from codex --to claude --dry-run
python skills-sync sync --from codex --to claude
```

On Windows, run `py skills-sync ...` if `python` is unavailable. The default vault is `~/.skills-sync/vault`. On another device, use the same synced vault folder, wait for its folder-sync service to finish, then run `python skills-sync doctor` and `python skills-sync sync --from codex --to cursor` (or another target).

Existing same-name target skills are skipped by default. Use `--replace` only after reviewing `--dry-run`: each replaced target folder is backed up under `~/.skills-sync/backups/<vault-id>/<target>/<run-id>/`. Sync never deletes target skills. The snapshot is checked against its SHA-256 manifest before copying.

### Use an Obsidian vault

Create a **new, empty subfolder** inside a private Obsidian vault; do not point at the vault root or any existing data folder. For example:

```powershell
py skills-sync --vault 'C:\Users\You\Documents\Obsidian\My Vault\Skills Sync' init
py skills-sync --vault 'C:\Users\You\Documents\Obsidian\My Vault\Skills Sync' snapshot --from codex
```

Set `SKILLS_SYNC_VAULT` to avoid repeating `--vault`. When using Obsidian Sync, enable **Sync all other types** on every device: skills can contain Python, JSON, images, and other non-Markdown files. The local vault is an ordinary folder, not locally encrypted; use private transport and review contents for secrets or licenses before syncing. Obsidian Sync is transport, not a separate backup.

### Other tools and custom folders

```bash
python skills-sync snapshot --from claude
python skills-sync sync --from claude --to gemini --dry-run
python skills-sync sync --from claude --to gemini
python skills-sync snapshot --from my-agent --root /path/to/my-agent/skills
python skills-sync sync --from my-agent --to cursor
```

Snapshots are source-specific. To share skills both ways, take a snapshot of each source and sync each one into the other; review name conflicts before replacing. The tool does not merge two different versions of a skill automatically.

## Commands

| Command | Purpose |
| --- | --- |
| `skills-sync tools` | Discover built-in skill paths and whether they exist. |
| `skills-sync init` | Initialize an empty dedicated vault folder. |
| `skills-sync snapshot --from TOOL [--root PATH]` | Save one tool's portable skills. |
| `skills-sync sync --from TOOL --to TOOL [--root PATH] [--dry-run] [--replace]` | Copy one snapshot into a target tool. |
| `skills-sync doctor` | Check vault and every snapshot's integrity. |

Add global `--json` for compact machine-readable stdout. Successful output is a JSON object; errors with `--json` use `{"error":"..."}` and a nonzero exit code. `doctor` returns nonzero when the vault is uninitialized or any snapshot is invalid. No network or authentication is required; `--vault` or `SKILLS_SYNC_VAULT` selects the vault.

On Unix-like systems, `make install-local` adds `skills-sync` to `~/.local/bin`. Otherwise call the checked-out `skills-sync` file with Python from any working directory. The executable resolves its own code location.

This repository contains only tool code and documentation. Keep actual vaults outside this checkout and out of public repositories.

A portable [Skills Sync agent skill](skills/skills-sync/SKILL.md) is included for agents that support the Agent Skills format; it is not installed automatically.

## Development and license

Run `python -m unittest discover -s tests -v`. Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md). MIT licensed; see [LICENSE](LICENSE).
