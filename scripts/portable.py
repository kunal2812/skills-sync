"""Portable SKILL.md snapshots and cross-tool sync. No cloud account required."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

TOOL_ROOT = Path(__file__).resolve().parents[1]
MARKER = 'skills-sync-vault.json'
FORMAT = 2
TOOLS = ('agents', 'codex', 'claude', 'cursor', 'gemini')
IGNORED = {'.git', '__pycache__', '.DS_Store'}


def home() -> Path:
    return Path.home()


def tool_root(name: str) -> Path:
    roots = {
        'agents': home() / '.agents' / 'skills',
        'codex': Path(os.environ.get('CODEX_HOME', home() / '.codex')) / 'skills',
        'claude': home() / '.claude' / 'skills',
        'cursor': home() / '.cursor' / 'skills',
        'gemini': home() / '.gemini' / 'skills',
    }
    if name not in roots:
        raise ValueError(f'Unknown tool {name!r}; use one of {", ".join(TOOLS)} or --root PATH')
    return roots[name].expanduser().resolve()


def vault_root(arg: str | None) -> Path:
    return Path(arg or os.environ.get('SKILLS_SYNC_VAULT') or home() / '.skills-sync' / 'vault').expanduser().resolve()


def separate(root: Path, other: Path) -> None:
    if root == other or root in other.parents or other in root.parents:
        raise ValueError(f'Vault and skill/tool directory must be separate: {root} / {other}')


def check_vault_location(root: Path) -> None:
    separate(root, TOOL_ROOT)
    for name in TOOLS:
        separate(root, tool_root(name))


def init(root: Path) -> dict:
    check_vault_location(root)
    marker = root / MARKER
    if marker.is_file():
        return read_vault(root)
    if root.exists() and any(root.iterdir()):
        raise ValueError('Choose an empty dedicated folder, not an Obsidian vault root or existing data folder')
    root.mkdir(parents=True, exist_ok=True)
    data = {'format_version': FORMAT, 'vault_id': str(uuid.uuid4())}
    marker.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return data


def read_vault(root: Path) -> dict:
    check_vault_location(root)
    marker = root / MARKER
    if marker.is_symlink() or not marker.is_file():
        raise ValueError(f'Vault not initialized: {root}. Run skills-sync init')
    data = json.loads(marker.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('format_version') != FORMAT or not data.get('vault_id'):
        raise ValueError('Unsupported skills-sync vault')
    try:
        uuid.UUID(data['vault_id'])
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError('Invalid vault ID') from error
    return data


def safe_name(name: str) -> str:
    if not isinstance(name, str) or not name or name.startswith('.') or '/' in name or '\\' in name or ':' in name:
        raise ValueError(f'Unsafe skill name: {name!r}')
    return name


def files_in(folder: Path) -> dict[str, str]:
    files = {}
    for path in sorted(folder.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Symlink in snapshot: {path}')
        if path.is_file() and path != folder / 'manifest.json':
            files[path.relative_to(folder).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def verify(folder: Path) -> dict:
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError(f'Invalid snapshot directory: {folder}')
    manifest = folder / 'manifest.json'
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError(f'Missing snapshot manifest: {folder}')
    data = json.loads(manifest.read_text(encoding='utf-8'))
    if (not isinstance(data, dict) or data.get('format_version') != FORMAT or
            data.get('source') != folder.name or data.get('files') != files_in(folder)):
        raise ValueError(f'Incomplete or changed snapshot: {folder}')
    if not isinstance(data.get('skills'), list):
        raise ValueError(f'Invalid skill list: {folder}')
    for name in data.get('skills', []):
        safe_name(name)
        if not (folder / name / 'SKILL.md').is_file():
            raise ValueError(f'Missing SKILL.md for {name}')
    if len(data['skills']) != len(set(data['skills'])):
        raise ValueError(f'Duplicate skill in snapshot: {folder}')
    return data


def copy_skill(source: Path, target: Path) -> None:
    def ignore(directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name in IGNORED or name.endswith('.pyc') or (Path(directory) / name).is_symlink()}
    shutil.copytree(source, target, ignore=ignore)


def snapshot(root: Path, name: str, source: Path) -> dict:
    read_vault(root)
    safe_name(name)
    separate(root, source)
    if not source.is_dir():
        raise ValueError(f'Source skill directory not found: {source}')
    base = root / 'snapshots'
    if base.is_symlink():
        raise ValueError(f'Snapshot root must not be a symlink: {base}')
    base.mkdir(exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.stage-', dir=base))
    destination = base / name
    previous = base / f'.previous-{name}'
    try:
        if destination.is_symlink() or previous.is_symlink():
            raise ValueError('Snapshot paths must not be symlinks')
        names = []
        for entry in sorted(source.iterdir()):
            if (entry.name.startswith('.') or not entry.is_dir() or entry.is_symlink() or
                    (entry / 'SKILL.md').is_symlink() or not (entry / 'SKILL.md').is_file()):
                continue
            safe_name(entry.name)
            copy_skill(entry, staging / entry.name)
            names.append(entry.name)
        data = {'format_version': FORMAT, 'source': name, 'skills': names, 'files': files_in(staging)}
        (staging / 'manifest.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        if previous.exists():
            raise ValueError(f'Unresolved previous snapshot: {previous}')
        if destination.exists():
            destination.rename(previous)
        try:
            staging.rename(destination)
        except Exception:
            if previous.exists():
                previous.rename(destination)
            raise
        if previous.exists():
            shutil.rmtree(previous)
        return {'source': name, 'skills': len(names), 'snapshot': str(destination)}
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def sync(root: Path, source_name: str, target_name: str, target: Path, replace: bool, dry_run: bool) -> dict:
    vault = read_vault(root)
    safe_name(source_name)
    safe_name(target_name)
    separate(root, target)
    source = root / 'snapshots' / source_name
    data = verify(source)
    if not target.is_dir() and target.exists():
        raise ValueError(f'Target is not a directory: {target}')
    installed, skipped, unchanged, backups = [], [], [], []
    backup_root = home() / '.skills-sync' / 'backups' / vault['vault_id'] / target_name / str(uuid.uuid4())
    planned = []
    for name in data['skills']:
        src = source / name
        dest = target / name
        backup = backup_root / name
        if dest.is_symlink():
            raise ValueError(f'Refusing to replace symlink: {dest}')
        if dest.exists():
            if not dest.is_dir():
                skipped.append(name)
                continue
            if files_in(dest) == files_in(src):
                unchanged.append(name)
                continue
            if not replace:
                skipped.append(name)
                continue
            backups.append(str(backup))
        installed.append(name)
        planned.append((src, dest, backup))
    if dry_run:
        return {'source': source_name, 'target': target_name, 'installed': installed, 'skipped_conflicts': skipped,
                'unchanged': unchanged, 'backups': backups, 'dry_run': True}
    for src, dest, backup in planned:
        target.mkdir(parents=True, exist_ok=True)
        moved_backup = False
        if dest.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            dest.rename(backup)
            moved_backup = True
        try:
            copy_skill(src, dest)
        except Exception:
            if dest.exists():
                shutil.rmtree(dest)
            if moved_backup:
                backup.rename(dest)
            raise
    return {'source': source_name, 'target': target_name, 'installed': installed, 'skipped_conflicts': skipped,
            'unchanged': unchanged, 'backups': backups, 'dry_run': dry_run}


def doctor(root: Path) -> dict:
    result = {'vault': str(root), 'initialized': False, 'snapshots': {}, 'tools': {}}
    for name in TOOLS:
        path = tool_root(name)
        result['tools'][name] = {'path': str(path), 'exists': path.is_dir()}
    try:
        read_vault(root)
        result['initialized'] = True
        if (root / 'snapshots').is_symlink():
            raise ValueError('Snapshot root must not be a symlink')
        for folder in sorted((root / 'snapshots').iterdir()) if (root / 'snapshots').is_dir() else []:
            if folder.name.startswith('.') or not folder.is_dir():
                continue
            try:
                result['snapshots'][folder.name] = {'valid': True, 'skills': len(verify(folder)['skills'])}
            except (OSError, ValueError) as error:
                result['snapshots'][folder.name] = {'valid': False, 'error': str(error)}
    except (OSError, ValueError) as error:
        result['error'] = str(error)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description='Sync portable SKILL.md folders across AI tools, accounts, and devices.')
    parser.add_argument('--vault', help='Dedicated vault folder (or SKILLS_SYNC_VAULT); defaults to ~/.skills-sync/vault')
    parser.add_argument('--json', action='store_true', help='Print machine-readable JSON')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('tools', help='Discover built-in global skill folders')
    commands.add_parser('init', help='Initialize an empty vault folder')
    commands.add_parser('doctor', help='Check vault and snapshots')
    snap = commands.add_parser('snapshot', help='Copy one tool’s skills into the vault')
    snap.add_argument('--from', dest='source', required=True, help='Source name: agents, codex, claude, cursor, gemini, or custom name with --root')
    snap.add_argument('--root', help='Explicit source skills directory')
    push = commands.add_parser('sync', help='Install one snapshot into another tool; never deletes target skills')
    push.add_argument('--from', dest='source', required=True, help='Snapshot source name')
    push.add_argument('--to', dest='target', required=True, help='Target tool name or custom name with --root')
    push.add_argument('--root', help='Explicit target skills directory')
    push.add_argument('--replace', action='store_true', help='Back up and replace same-name target skills')
    push.add_argument('--dry-run', action='store_true', help='Show planned changes only')
    args = parser.parse_args()
    root = vault_root(args.vault)
    try:
        if args.command == 'tools':
            result = {name: {'path': str(tool_root(name)), 'exists': tool_root(name).is_dir()} for name in TOOLS}
        elif args.command == 'init':
            result = {'vault': str(root), **init(root)}
        elif args.command == 'doctor':
            result = doctor(root)
        elif args.command == 'snapshot':
            result = snapshot(root, args.source, Path(args.root).expanduser().resolve() if args.root else tool_root(args.source))
        else:
            result = sync(root, args.source, args.target, Path(args.root).expanduser().resolve() if args.root else tool_root(args.target), args.replace, args.dry_run)
        print(json.dumps(result, indent=2 if not args.json else None, sort_keys=True))
        if args.command == 'doctor' and (not result['initialized'] or any(not s['valid'] for s in result['snapshots'].values())):
            raise SystemExit(1)
    except (OSError, ValueError, RuntimeError) as error:
        if args.json:
            print(json.dumps({'error': str(error)}))
        else:
            print(f'skills-sync: {error}', file=sys.stderr)
        raise SystemExit(2)


if __name__ == '__main__':
    main()
