"""Data-only tests: no third-party reference or starter program is executed."""
from pathlib import Path
import copy
import importlib.util
import tempfile
import unittest
from unittest.mock import patch

from trainerlib.common import PackError, atomic_json, digest, read_json
from trainerlib.format import load_pack, payload_files
from trainerlib.store import PackStore

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('localize_exercism', ROOT / 'scripts/localize-exercism.py')
localize = importlib.util.module_from_spec(spec)
spec.loader.exec_module(localize)
TRANSLATIONS = ROOT / 'knowledge/translations/exercism-zh-cn'
ARCHIVES = ROOT / 'dist/Embedded-Trainer-0.12.0-Windows-x64-offline/knowledge/extras'
CATALOG = ROOT / '.trainer/release-downloads/knowledge-v1.1.0/catalog.json'


class TranslationDocuments(unittest.TestCase):
    def test_bundle_name_retains_patch_version_and_offline_marker(self):
        path = localize.bundle_path(Path('dist/Embedded-Trainer-Exercism-50-zh-CN-1.0.1-offline'))
        self.assertEqual('Embedded-Trainer-Exercism-50-zh-CN-1.0.1-offline.zip', path.name)

    def test_all_50_have_chinese_display_fields_and_separate_hints(self):
        files = list(TRANSLATIONS.glob('*.md'))
        self.assertEqual(50, len(files))
        for file in files:
            with self.subTest(file=file.name):
                fields, body = localize.parse_translation(file.read_text('utf-8'))
                self.assertGreaterEqual(len(fields['hints']), 2)
                self.assertNotIn('## 提示', body)
                self.assertTrue(localize.CHINESE.search(fields['title']))

    def test_parser_rejects_untranslated_summary(self):
        doc = (TRANSLATIONS / 'c.binary.md').read_text('utf-8')
        summary = localize.parse_translation(doc)[0]['summary']
        with self.assertRaises(PackError):
            localize.parse_translation(doc.replace(summary, 'English only summary'))

    def test_parser_rejects_active_html(self):
        doc = (TRANSLATIONS / 'c.binary.md').read_text('utf-8')
        with self.assertRaises(PackError):
            localize.parse_translation(doc.replace('## 提示', '<script>alert(1)</script>\n\n## 提示'))

    def test_parser_requires_hints(self):
        doc = (TRANSLATIONS / 'c.binary.md').read_text('utf-8')
        with self.assertRaises(PackError):
            localize.parse_translation(doc.split('## 提示')[0])


@unittest.skipUnless(CATALOG.exists() and ARCHIVES.exists(), 'Pinned release archives not present')
class PinnedTranslationGate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='trainer-zh-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.entry = localize.pinned_entries(CATALOG)[0]
        self.archive = ARCHIVES / (self.entry['id'] + '-1.0.0.zip')
        self.document = (TRANSLATIONS / 'c.armstrong-numbers.md').read_text('utf-8')
        self.base, self.target = self.root / 'base', self.root / 'target'
        self.base.mkdir()
        self.target.mkdir()
        PackStore.extract(self.archive.read_bytes(), self.base)
        manifest, payload = localize.expected_payload(self.base, self.document, self.entry)
        for name, raw in payload.items():
            file = self.target / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(raw)
        atomic_json(self.target / 'pack.json', manifest)

    def verify(self):
        return localize.verify_delta(self.base, self.target, self.document, self.entry)

    def reindex(self):
        manifest = read_json(self.target / 'pack.json')
        manifest['files'] = payload_files(self.target)
        atomic_json(self.target / 'pack.json', manifest)

    def test_only_presentation_changes_pass_without_execution_claim(self):
        result = self.verify()
        self.assertTrue(result['passed'])
        self.assertEqual([], result['referenceVerified'])
        self.assertFalse(result['referenceReExecuted'])
        self.assertEqual('none', result['runner'])

    def test_reference_change_is_rejected_even_if_reindexed(self):
        reference = next(self.target.glob('lessons/*/reference/*.c'))
        reference.write_bytes(reference.read_bytes() + b'\n/* tamper */\n')
        self.reindex()
        with self.assertRaises(PackError):
            self.verify()

    def test_test_change_is_rejected_even_if_reindexed(self):
        test = next(self.target.glob('lessons/*/tests/test_*.c'))
        test.write_bytes(test.read_bytes() + b'\n/* tamper */\n')
        self.reindex()
        with self.assertRaises(PackError):
            self.verify()

    def test_build_configuration_change_is_rejected(self):
        data = read_json(self.target / 'questions.json')
        data['questions'][0]['build']['standard'] = 'c17'
        atomic_json(self.target / 'questions.json', data)
        self.reindex()
        with self.assertRaises(PackError):
            self.verify()

    def test_license_change_is_rejected(self):
        license_file = next((self.target / 'licenses').glob('*.txt'))
        license_file.write_bytes(license_file.read_bytes() + b'\nChanged\n')
        self.reindex()
        with self.assertRaises(PackError):
            self.verify()

    def test_extra_file_is_rejected(self):
        (self.target / 'extra.md').write_text('Unapproved extra content', 'utf-8')
        self.reindex()
        with self.assertRaises(PackError):
            self.verify()

    def test_source_origin_change_is_rejected(self):
        data = read_json(self.target / 'questions.json')
        data['questions'][0]['origin']['commit'] = '0' * 40
        atomic_json(self.target / 'questions.json', data)
        self.reindex()
        with self.assertRaises(PackError):
            self.verify()

    def test_base_archive_mismatch_is_rejected(self):
        entry = copy.deepcopy(self.entry)
        entry['sha256'] = '0' * 64
        with self.assertRaises(PackError):
            localize.build_one(entry, self.archive, self.document, self.root / 'output')

    def test_round_trip_keeps_old_version_and_does_not_inherit_trust(self):
        output = self.root / 'output'
        with patch('trainerlib.audit.run_program', side_effect=AssertionError('No code execution')):
            entry = localize.build_one(self.entry, self.archive, self.document, output)
        store = PackStore(self.root / 'store')
        store.install(self.archive, self.entry['sha256'])
        store.trust(self.entry['id'], self.entry['sha256'])  # Test fixture only.
        trust_before = copy.deepcopy(store.index()['trusted'])
        store.install(output / entry['filename'], entry['sha256'])
        self.assertEqual(trust_before, store.index()['trusted'])
        self.assertEqual({'1.0.0', '1.0.1'}, set(store.index()['versions'][entry['id']]))
        lessons = store.lessons()[entry['id']]
        self.assertEqual(self.entry['id'].replace('review.', 'oss.', 1), lessons[0]['id'])
        self.assertTrue(lessons[0]['_needsTrust'])
        target = store.location(entry['id'], '1.0.1')
        _, questions = load_pack(target, integrity=True, approved=True)
        self.assertTrue(localize.CHINESE.search(questions[0]['title']))
        review = read_json(target / 'review.json')
        provenance = read_json(target / 'localization.json')
        self.assertEqual(localize.REVIEWER, review['reviewer'])
        self.assertFalse(review['newHumanReview'])
        self.assertNotIn('ciReportSha256', review)
        self.assertEqual(read_json(self.base / 'review.json'), provenance['baseReview'])
        store.rollback(entry['id'], '1.0.0')
        self.assertFalse(store.lessons()[entry['id']][0]['_needsTrust'])


if __name__ == '__main__':
    unittest.main()
