import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import portable


class PortableTests(unittest.TestCase):
    def test_cross_tool_snapshot_and_sync_with_conflict_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            vault = base / 'obsidian' / 'Skills Sync'
            source = base / 'codex' / 'skills'
            target = base / 'claude' / 'skills'
            (source / 'alpha').mkdir(parents=True)
            (source / 'alpha' / 'SKILL.md').write_text('new')
            (target / 'alpha').mkdir(parents=True)
            (target / 'alpha' / 'SKILL.md').write_text('local')
            (target / 'keep').mkdir()
            (target / 'keep' / 'SKILL.md').write_text('keep')
            with patch.object(portable, 'home', return_value=base / 'home'):
                portable.init(vault)
                self.assertEqual(portable.snapshot(vault, 'codex', source)['skills'], 1)
                self.assertEqual(portable.sync(vault, 'codex', 'claude', target, False, False)['skipped_conflicts'], ['alpha'])
                self.assertEqual((target / 'alpha' / 'SKILL.md').read_text(), 'local')
                preview = portable.sync(vault, 'codex', 'claude', target, True, True)
                self.assertEqual(preview['installed'], ['alpha'])
                self.assertEqual((target / 'alpha' / 'SKILL.md').read_text(), 'local')
                result = portable.sync(vault, 'codex', 'claude', target, True, False)
                self.assertEqual((target / 'alpha' / 'SKILL.md').read_text(), 'new')
                self.assertEqual(Path(result['backups'][0], 'SKILL.md').read_text(), 'local')
                self.assertEqual((target / 'keep' / 'SKILL.md').read_text(), 'keep')

    def test_tampered_snapshot_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, target, vault = base / 'source', base / 'target', base / 'vault'
            (source / 'alpha').mkdir(parents=True)
            (source / 'alpha' / 'SKILL.md').write_text('original')
            with patch.object(portable, 'home', return_value=base / 'home'):
                portable.init(vault)
                portable.snapshot(vault, 'custom', source)
                (vault / 'snapshots' / 'custom' / 'alpha' / 'SKILL.md').write_text('changed')
                with self.assertRaisesRegex(ValueError, 'Incomplete or changed'):
                    portable.sync(vault, 'custom', 'other', target, False, False)
                self.assertFalse(target.exists())

    def test_nested_manifest_file_is_hashed(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, vault = base / 'source', base / 'vault'
            (source / 'alpha').mkdir(parents=True)
            (source / 'alpha' / 'SKILL.md').write_text('skill')
            (source / 'alpha' / 'manifest.json').write_text('supporting file')
            with patch.object(portable, 'home', return_value=base / 'home'):
                portable.init(vault)
                portable.snapshot(vault, 'custom', source)
                self.assertIn('alpha/manifest.json', portable.verify(vault / 'snapshots' / 'custom')['files'])
                (vault / 'snapshots' / 'custom' / 'alpha' / 'manifest.json').write_text('changed')
                with self.assertRaisesRegex(ValueError, 'Incomplete or changed'):
                    portable.verify(vault / 'snapshots' / 'custom')

    def test_nonempty_vault_and_overlap_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            occupied = base / 'notes'
            occupied.mkdir()
            (occupied / 'note.md').write_text('keep')
            with patch.object(portable, 'home', return_value=base / 'home'):
                with self.assertRaisesRegex(ValueError, 'empty dedicated folder'):
                    portable.init(occupied)
                self.assertEqual((occupied / 'note.md').read_text(), 'keep')

    def test_symlinked_snapshot_root_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, vault, outside = base / 'source', base / 'vault', base / 'outside'
            (source / 'alpha').mkdir(parents=True)
            (source / 'alpha' / 'SKILL.md').write_text('skill')
            outside.mkdir()
            with patch.object(portable, 'home', return_value=base / 'home'):
                portable.init(vault)
                try:
                    (vault / 'snapshots').symlink_to(outside, target_is_directory=True)
                except (OSError, NotImplementedError):
                    self.skipTest('Symlinks unavailable in this environment')
                with self.assertRaisesRegex(ValueError, 'must not be a symlink'):
                    portable.snapshot(vault, 'custom', source)
                self.assertEqual(list(outside.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
