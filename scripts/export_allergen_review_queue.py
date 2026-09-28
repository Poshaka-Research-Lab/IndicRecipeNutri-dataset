"""Export ID/class-only review candidates; never auto-correct a legacy label."""
import argparse
from pathlib import Path
import pandas as pd
from build_quality_flags import atomic_parquet, validate_output_root


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--protected-root', type=Path, required=True)
    a = ap.parse_args()
    output = validate_output_root(a.root, a.protected_root)
    frame = pd.read_parquet(output / 'allergen_evidence_v1.parquet',
                            filters=[('status_reason', '==', 'name_conflicts_with_legacy_absence')],
                            columns=['recipe_id', 'allergen', 'legacy_status', 'evidence_kind', 'status_v012'])
    if not frame.legacy_status.eq('absent').all() or not frame.status_v012.eq('unknown').all():
        raise ValueError('Candidate status contract violated')
    frame['review_status'] = 'unreviewed_candidate'
    frame = frame.sort_values(['recipe_id', 'allergen']).reset_index(drop=True)
    if frame.duplicated(['recipe_id', 'allergen']).any():
        raise ValueError('Duplicate candidate keys')
    atomic_parquet(frame, output / 'allergen_review_candidates_v1.parquet')
    print('Exported %d ID/class candidates; no text, human labels or status corrections.' % len(frame))


if __name__ == '__main__':
    main()
