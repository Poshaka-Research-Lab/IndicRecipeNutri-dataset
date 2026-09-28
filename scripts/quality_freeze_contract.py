"""Compare immutable baseline payload bytes and release identity without writing inputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_quality_inputs import BASELINE, git, sha256


def validate_payload(root: Path, receipt: dict, data_only: bool = True) -> list[str]:
    root = root.resolve()
    problems = []
    entries = receipt['checksum_files']
    if not entries:
        return ['empty baseline receipt']
    seen = set()
    for entry in entries:
        rel = entry['path']
        if rel in seen:
            problems.append('duplicate baseline path: ' + rel)
        seen.add(rel)
        p = (root / rel).resolve()
        if not p.is_relative_to(root):
            problems.append('baseline path escapes root: ' + rel)
            continue
        if data_only and not rel.startswith('data/'):
            continue
        if not p.is_file() or sha256(p) != entry['expected']:
            problems.append('baseline payload changed: ' + rel)
    if data_only and not any(x.startswith('data/') for x in seen):
        problems.append('receipt has no baseline data paths')
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline-receipt', type=Path, required=True)
    ap.add_argument('--protected-root', type=Path, required=True)
    ap.add_argument('--candidate-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    receipt = json.loads(args.baseline_receipt.read_text(encoding='utf-8'))
    if args.protected_root.resolve() == args.candidate_root.resolve():
        raise ValueError('Protected checkout and candidate must be distinct')
    problems = validate_payload(args.protected_root, receipt, data_only=False)
    problems += validate_payload(args.candidate_root, receipt)
    head = git(args.protected_root, 'rev-parse', 'HEAD')
    tag = git(args.protected_root, 'rev-parse', 'v0.11.0^{commit}')
    status = git(args.protected_root, 'status', '--porcelain')
    if head != BASELINE or tag != BASELINE or status:
        problems.append('protected checkout identity/status changed')
    result = {'protected_head': head, 'baseline_tag': tag,
              'protected_status': status, 'problems': problems,
              'candidate_baseline_data_identical': not validate_payload(args.candidate_root, receipt),
              'k006_head_pin': 'known mismatch; not re-pinned'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
    return bool(problems)


if __name__ == '__main__':
    raise SystemExit(main())
