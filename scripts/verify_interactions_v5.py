"""Verify v5's complete synthetic grid and replay every user from declared inputs."""
import argparse
import json
from pathlib import Path

import pandas as pd

from audit_quality_inputs import sha256
from build_quality_flags import atomic_json
from build_interactions_v5 import VERSION, FEATURES, generate, logical_digest


def verify(root: Path, replay: bool = True):
    output = root / 'data/interactions_v5'
    manifest = json.loads((output / 'GENERATOR_MANIFEST.json').read_text(encoding='utf-8'))
    config = manifest['config']
    errors = []
    if config['version'] != VERSION or manifest['features'] != FEATURES:
        errors.append('generator or feature version mismatch')
    source = root / 'data/quality/item_attributes_v1.parquet'
    if sha256(source) != manifest['input_sha256']:
        errors.append('attribute input changed')
    if sha256(Path(__file__).with_name('build_interactions_v5.py')) != manifest['builder_sha256']:
        errors.append('generator source changed')
    frames = []
    names = ['users.parquet','interactions.parquet','generator_truth/choice_probabilities.parquet']
    expected_columns = [
        ['user_id','preferred_region','preferred_spice','grade_direction','popularity_direction'],
        ['user_id','recipe_id','event_index','split'],
        ['user_id','event_index','utility','conditional_choice_probability']]
    for name, columns in zip(names, expected_columns):
        p = output / name
        frame = pd.read_parquet(p)
        entry = manifest['outputs'][name]
        if frame.columns.tolist() != columns:
            errors.append('unexpected feature/schema: ' + name)
        if len(frame) != entry['rows'] or sha256(p) != entry['sha256'] or logical_digest(frame) != entry['logical_sha256']:
            errors.append('output receipt mismatch: ' + name)
        frames.append(frame)
    users, events, truth = frames
    attrs = pd.read_parquet(source)
    if users.user_id.isna().any() or users.user_id.duplicated().any() or len(users) != config['users']:
        errors.append('user population mismatch')
    if set(events.user_id) != set(users.user_id) or not events.recipe_id.isin(attrs.recipe_id).all():
        errors.append('event foreign-key mismatch')
    if events.duplicated(['user_id','recipe_id']).any() or events.duplicated(['user_id','event_index']).any():
        errors.append('duplicate user-item or event key')
    if not events.groupby('user_id').size().eq(config['events_per_user']).all():
        errors.append('per-user cardinality mismatch')
    if not events.event_index.between(0,config['events_per_user']-1).all():
        errors.append('event index out of range')
    expected_split = events.event_index.map(lambda i:'train' if i < config['train_events'] else 'test')
    if not events.split.equals(expected_split):
        errors.append('temporal/mechanism split mismatch')
    if not events[['user_id','event_index']].equals(truth[['user_id','event_index']]):
        errors.append('oracle key grid mismatch')
    if not truth.conditional_choice_probability.gt(0).all() or not truth.conditional_choice_probability.le(1).all():
        errors.append('invalid conditional choice probability')
    replay_equal = None
    if replay and not errors:
        rebuilt = generate(attrs, config)
        replay_equal = True
        for name, expected, actual in zip(names, rebuilt, frames):
            if not expected.equals(actual):
                errors.append('full replay differs: ' + name)
                replay_equal = False
    return {'status':'failed' if errors else 'passed', 'errors':errors,
            'users':len(users), 'events':len(events), 'full_replay_equal':replay_equal,
            'heldout_user_item_overlap':int(events.duplicated(['user_id','recipe_id']).sum()),
            'scope':'Synthetic mechanism and exact replay; no real-user or recommendation-quality validation.'}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    result=verify(a.root)
    atomic_json(result,a.output)
    print(json.dumps(result))
    return result['status']!='passed'


if __name__=='__main__':
    raise SystemExit(main())
