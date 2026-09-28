"""A separate synthetic choice log driven only by published item attributes.

All users are fictional and have no modeled dietary restrictions. This is a
mechanism benchmark, not a recommended menu or a health/safety assessment.
Group-weighted sampling is exact softmax over remaining items, without replacement.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd

from audit_quality_inputs import sha256
from build_quality_flags import atomic_json, atomic_parquet, validate_output_root

VERSION = 'published-attribute-generator-v5.1'
FEATURES = ['Region', 'SpiceLevel', 'HealthGrade', 'rating_count_bin']
CONFIG = {'version': VERSION, 'seed': 20260928, 'users': 50000, 'events_per_user': 20,
          'train_events': 16, 'train_weights': [1.4, 0.9, 0.5, 0.4],
          'test_weights': [1.1, 1.2, 0.4, 0.5], 'temperature': 1.0,
          'replacement': False, 'test_mechanism': 'declared_coefficient_shift',
          'restrictions': 'none_modeled_synthetic_benchmark_only'}
POP = {'unknown': 0.0, 'zero': 0.0, '1_9': 1/3, '10_99': 2/3, '100_plus': 1.0}
GRADE = {'A': 1.0, 'B': 0.75, 'C': 0.5, 'D': 0.25, 'E': 0.0, 'unknown': 0.0}


def groups_from_attributes(attributes: pd.DataFrame):
    if attributes.recipe_id.isna().any() or attributes.recipe_id.duplicated().any():
        raise ValueError('Non-unique or missing item IDs')
    frame = attributes[['recipe_id', *FEATURES]].copy().sort_values('recipe_id')
    frame[FEATURES] = frame[FEATURES].fillna('unknown')
    if not frame.SpiceLevel.isin(['mild', 'medium', 'hot', 'unknown']).all():
        raise ValueError('Unknown spice domain')
    if not frame.HealthGrade.isin(GRADE).all() or not frame.rating_count_bin.isin(POP).all():
        raise ValueError('Unknown grade/popularity domain')
    groups = defaultdict(list)
    for rid, *values in frame.itertuples(index=False, name=None):
        groups[tuple(values)].append(int(rid))
    keys = sorted(groups)
    return keys, [np.asarray(groups[k], dtype=np.int64) for k in keys]


def utility(keys, profile: dict, weights: list[float]) -> np.ndarray:
    vals = []
    for region, spice, grade, rating in keys:
        # Missing grade/rating contributes zero, never an invented good or bad score.
        grade_score = 0.0 if grade == 'unknown' else (2 * GRADE[grade] - 1) * profile['grade_direction']
        pop_score = 0.0 if rating == 'unknown' else (2 * POP[rating] - 1) * profile['popularity_direction']
        features = [float(region == profile['preferred_region']),
                    float(spice == profile['preferred_spice']), grade_score, pop_score]
        vals.append(float(np.dot(features, weights)))
    return np.asarray(vals)


def draw_user(keys, members, profile, rng, config):
    count = config['events_per_user']
    if count < 2 or not 0 < config['train_events'] < count or sum(map(len, members)) < count:
        raise ValueError('Invalid event count/split or insufficient unique items')
    remaining = np.asarray([len(x) for x in members], dtype=np.int64)
    used = defaultdict(set)
    scores = [utility(keys, profile, config[k]) / config['temperature'] for k in ['train_weights', 'test_weights']]
    masses = [np.exp(s - s.max()) for s in scores]
    out = []
    for step in range(count):
        phase = int(step >= config['train_events'])
        mass = remaining * masses[phase]
        denominator = float(mass.sum())
        cdf = np.cumsum(mass)
        group = min(int(np.searchsorted(cdf, rng.random() * denominator, side='right')), len(keys)-1)
        while True:
            rid = int(members[group][rng.integers(len(members[group]))])
            if rid not in used[group]:
                break
        used[group].add(rid)
        probability = float(masses[phase][group] / denominator)
        remaining[group] -= 1
        out.append((rid, step, 'train' if phase == 0 else 'test', float(scores[phase][group]), probability))
    return out


def generate(attributes, config):
    if config['temperature'] <= 0 or config['users'] < 1:
        raise ValueError('Positive temperature and user count required')
    keys, members = groups_from_attributes(attributes)
    regions = sorted({k[0] for k in keys if k[0] not in {'unknown', 'Pan-Indian'}})
    if not regions:
        raise ValueError('No named region available for synthetic preference profiles')
    users, events, truth = [], [], []
    for user in range(config['users']):
        # Each user has independent reproducible streams; event counts do not change profiles.
        profile_rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([config['seed'], user, 0])))
        choice_rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([config['seed'], user, 1])))
        profile = {'user_id': user, 'preferred_region': regions[int(profile_rng.integers(len(regions)))],
                   'preferred_spice': ['mild', 'medium', 'hot'][int(profile_rng.integers(3))],
                   'grade_direction': int(profile_rng.choice([-1, 1])),
                   'popularity_direction': int(profile_rng.choice([-1, 1]))}
        users.append(profile)
        for rid, step, split, score, prob in draw_user(keys, members, profile, choice_rng, config):
            events.append((user, rid, step, split))
            truth.append((user, step, score, prob))
        if (user + 1) % 5000 == 0:
            print(json.dumps({'users_generated': user + 1}), flush=True)
    return (pd.DataFrame(users),
            pd.DataFrame(events, columns=['user_id', 'recipe_id', 'event_index', 'split']),
            pd.DataFrame(truth, columns=['user_id', 'event_index', 'utility', 'conditional_choice_probability']))


def logical_digest(frame):
    return hashlib.sha256(frame.to_json(orient='records', double_precision=15).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--protected-root', type=Path, required=True)
    ap.add_argument('--users', type=int, default=CONFIG['users'])
    ap.add_argument('--pilot', action='store_true')
    a = ap.parse_args()
    root = a.root.resolve()
    validate_output_root(root, a.protected_root)
    output = (root / ('.local/quality_0_12_0/generator_pilot' if a.pilot else 'data/interactions_v5')).resolve()
    if not output.is_relative_to(root):
        raise ValueError('Output escapes candidate')
    path = root / 'data/quality/item_attributes_v1.parquet'
    item_manifest = json.loads((root / 'data/quality/item_card_manifest.json').read_text(encoding='utf-8'))
    if sha256(path) != item_manifest['payload_sha256']:
        raise ValueError('Item attributes differ from manifest')
    attrs = pd.read_parquet(path)
    config = dict(CONFIG, users=a.users)
    started = time.perf_counter()
    users, events, truth = generate(attrs, config)
    if events.duplicated(['user_id', 'recipe_id']).any() or len(events) != config['users'] * config['events_per_user']:
        raise ValueError('Generated event contract failed')
    if not events.recipe_id.isin(attrs.recipe_id).all():
        raise ValueError('Unknown generated item')
    frames = {'users.parquet': users, 'interactions.parquet': events,
              'generator_truth/choice_probabilities.parquet': truth}
    outputs = {}
    for name, frame in frames.items():
        atomic_parquet(frame, output / name)
        outputs[name] = {'rows': len(frame), 'sha256': sha256(output / name), 'logical_sha256': logical_digest(frame)}
    manifest = {'config': config, 'numpy_version': np.__version__, 'input_sha256': sha256(path),
                'builder_sha256': sha256(Path(__file__)), 'outputs': outputs,
                'features': FEATURES, 'oracle_only': ['utility', 'conditional_choice_probability'],
                'legacy_interactions_modified': False, 'synthetic_user_namespace': 'interactions_v5 only; do not join to v4 by numeric ID',
                'scope': 'Fully synthetic mechanism benchmark. No diet/medical constraints modeled; not meal recommendations.',
                'test_design': 'Per-user event indices 16-19 use a declared coefficient shift; no user-item pair appears twice.',
                'claims': 'No empirical superiority, real exposure propensity, or safety claim.'}
    atomic_json(manifest, output / 'GENERATOR_MANIFEST.json')
    print(json.dumps({'users': len(users), 'events': len(events), 'seconds': round(time.perf_counter()-started, 2)}))


if __name__ == '__main__':
    main()
