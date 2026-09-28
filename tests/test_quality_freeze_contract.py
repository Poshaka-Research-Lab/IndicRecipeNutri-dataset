import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from quality_freeze_contract import validate_payload


class FreezeContractTests(unittest.TestCase):
    def test_detects_mutation_deletion_and_ignores_additive_sidecar(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'data').mkdir()
            p = root / 'data/legacy.bin'
            p.write_bytes(b'original payload')
            receipt = {'checksum_files': [{'path': 'data/legacy.bin',
                        'expected': hashlib.sha256(p.read_bytes()).hexdigest()}]}
            (root / 'data/new_quality.bin').write_bytes(b'new sidecar')
            self.assertEqual(validate_payload(root, receipt), [])
            p.write_bytes(b'corrupted payload')
            self.assertIn('baseline payload changed', validate_payload(root, receipt)[0])
            p.unlink()
            self.assertTrue(validate_payload(root, receipt))

    def test_rejects_empty_or_escaping_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.assertTrue(validate_payload(root, {'checksum_files': []}))
            errors = validate_payload(root, {'checksum_files': [{'path': '../outside', 'expected': 'x'}]})
            self.assertTrue(any('escapes root' in e for e in errors))

    def test_detects_document_change_for_protected_checkout(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'README.md').write_text('modified')
            receipt = {'checksum_files': [{'path': 'README.md', 'expected': 'wrong'}]}
            self.assertTrue(validate_payload(root, receipt, data_only=False))


if __name__ == '__main__':
    unittest.main()
