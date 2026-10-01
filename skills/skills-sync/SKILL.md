---
name: skills-sync
description: Use the Skills Sync CLI to snapshot portable SKILL.md folders and copy them between AI tools or devices when the user asks to sync skills.
---

# Skills Sync

Find an installed `skills-sync` command or the repository's `skills-sync` script. Check `skills-sync --json doctor` and `skills-sync --json tools` before changing files. Python 3.10+ is required; no network login is needed. `SKILLS_SYNC_VAULT` or global `--vault` selects a dedicated folder, which may live inside a privately synced Obsidian vault.

For a requested source, run `skills-sync snapshot --from SOURCE`; inspect `skills-sync sync --from SOURCE --to TARGET --dry-run` before copying into the target. Same-name target folders are skipped unless the user requests replacement. `--replace` backs them up, but do not use it to resolve conflicts without inspecting the differences or obtaining direction. Never treat Obsidian or another folder-sync service as complete until its own status says so.

Examples:

```bash
skills-sync --json tools
skills-sync snapshot --from codex
skills-sync sync --from codex --to claude --dry-run
```

Use `--root PATH` with `snapshot` or `sync` for tools not in the built-in list. The CLI handles portable skill folders only; do not promise cross-provider plugin, MCP credential, or account transfer. It has no raw network/API command because it only reads and writes local folders. Do not publish the vault or repository history without explicit authorization and a privacy review.
