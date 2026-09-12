"""Stage frozen synthetic benchmarks and disclose their actual membership."""
from pathlib import Path
import hashlib
import json
import shutil
import pandas as pd

SNAPSHOTS = {
    'v1': ('synthetic_interactions', '57b53b1fdbc3b5a59c2f0bce8eb0af268d29b48939190ea5c21f336eb93f86fb'),
    'v3': ('synthetic_interactions_v3', '1e49553bb124b308d49983f642b763708aaccdf20a773920487b56427ddade8a'),
}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def id_map(path):
    """The final field is a remap ID; names may contain spaces."""
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    if not lines or lines[0].split() != ['org_id', 'remap_id']:
        raise ValueError(f'invalid ID-map header: {path}')
    result = {}
    originals = set()
    for line in lines[1:]:
        if not line.strip():
            continue
        original, remapped = line.rsplit(None, 1)
        remapped = int(remapped)
        if remapped in result or original in originals:
            raise ValueError(f'duplicate map identity: {path}')
        result[remapped] = original
        originals.add(original)
    return result


def read_split(path, users, items):
    pairs = set()
    count = 0
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        user, *rated = map(int, line.split())
        if user not in users or any(item not in items for item in rated):
            raise ValueError(f'split has an unknown remapped user/item ID: {path}')
        count += len(rated)
        pairs.update((user, item) for item in rated)
    return pairs, count


def describe(folder, snapshot, current_ids, withdrawn_ids):
    folder = Path(folder)
    for filename, expected in snapshot['files'].items():
        if digest(folder / filename) != expected:
            raise ValueError(f'historical bytes changed: {folder.name}/{filename}')
    items = id_map(folder / 'item_list.txt')
    users = id_map(folder / 'user_list.txt')
    entities = id_map(folder / 'entity_list.txt')
    relations = id_map(folder / 'relation_list.txt')
    triples = pd.read_csv(folder / 'kg_final.txt', sep=r'\s+', header=None,
                          names=['head', 'rel', 'tail'])
    if (not triples['head'].isin(entities).all() or
        not triples['tail'].isin(entities).all() or
        not triples['rel'].isin(relations).all()):
        raise ValueError('historical KG references an unknown entity/relation remap ID')
    for remapped, rid in items.items():
        if entities.get(remapped) != 'item:'+rid:
            raise ValueError('item/entity map namespace disagreement')
    train, train_rows = read_split(folder / 'train.txt', users, items)
    test, test_rows = read_split(folder / 'test.txt', users, items)
    interactions = pd.read_csv(folder / 'interactions.csv', usecols=['recipe_id'])
    recipe_ids = set(map(int, items.values()))
    interaction_ids = set(map(int, interactions.recipe_id))
    return {
        'protocol': 'historical_synthetic_v1', 'snapshot_id': snapshot['snapshot_id'],
        'status': 'frozen historical synthetic benchmark; not current-corpus or human relevance data',
        'original_corpus_snapshot_sha256': snapshot['original_corpus_snapshot_sha256'],
        'original_corpus_provenance': snapshot['original_corpus_provenance'],
        'files': snapshot['files'],
        'membership': {
            'post_core_items': len(items), 'post_core_users': len(users),
            'historical_graph_triples': len(triples), 'historical_graph_references_resolve': True,
            'interaction_rows_before_core': len(interactions),
            'interaction_recipe_ids_before_core': len(interaction_ids),
            'item_recipe_ids_missing_from_current_corpus': sorted(recipe_ids-current_ids),
            'interaction_recipe_ids_missing_from_current_corpus': sorted(interaction_ids-current_ids),
            'withdrawn_item_recipe_ids': sorted(recipe_ids & withdrawn_ids),
            'withdrawn_interaction_rows': int(interactions.recipe_id.isin(withdrawn_ids).sum()),
            'unexplained_missing_item_ids': sorted(recipe_ids-current_ids-withdrawn_ids),
            'unexplained_missing_interaction_ids': sorted(interaction_ids-current_ids-withdrawn_ids),
        },
        'splits': {
            'unit': 'synthetic user and remapped item pairs; not canonical recipe Split_v3',
            'train_rows': train_rows, 'test_rows': test_rows,
            'unique_train_pairs': len(train), 'unique_test_pairs': len(test),
            'overlapping_user_item_pairs': len(train & test),
            'canonical_recipe_split_alignment': 'not claimed; historical interaction protocol',
            'learned_feature_training_scope': 'not independently established; no inductive evaluation claim',
        },
        'interpretation': 'Historical results may use only this exact snapshot and protocol. Do not join silently to current recipe features. Original full-corpus reconstruction is not claimed. Regeneration requires a new version and fresh results.',
    }


def build_manifests(data_root, archive_root=None):
    from release_config import all_withdrawn_ids
    data_root = Path(data_root)
    current_ids = set(pd.read_parquet(data_root / 'corpus/recipes.parquet', columns=['recipe_id']).recipe_id)
    withdrawn = set(all_withdrawn_ids())
    reports = {}
    for version, (name, pin) in SNAPSHOTS.items():
        folder = data_root / name
        snapshot_path = (Path(archive_root) / version / 'SNAPSHOT.json') if archive_root else folder / 'SNAPSHOT.json'
        if digest(snapshot_path) != pin:
            raise ValueError(f'historical snapshot definition changed: {version}')
        snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
        if archive_root:
            folder.mkdir(parents=True, exist_ok=True)
            for filename, expected in snapshot['files'].items():
                source = Path(archive_root) / version / filename
                if digest(source) != expected:
                    raise ValueError(f'archived source changed: {source}')
                shutil.copyfile(source, folder / filename)
            shutil.copyfile(snapshot_path, folder / 'SNAPSHOT.json')
        report = describe(folder, snapshot, current_ids, withdrawn)
        report['current_corpus_sha256_for_comparison'] = digest(data_root / 'corpus/recipes.parquet')
        reports[folder / 'HISTORICAL_MANIFEST.json'] = report
    return reports


def stage_historical_synthetic(archive_root, data_root):
    for path, report in build_manifests(data_root, archive_root).items():
        path.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n', encoding='utf-8', newline='\n')
        print(f'staged historical snapshot: {path.parent.name}')


def validate_historical_synthetic(root):
    try:
        for path, expected in build_manifests(Path(root) / 'data').items():
            if json.loads(path.read_text(encoding='utf-8')) != expected:
                return [f'stale historical synthetic manifest: {path}']
    except (OSError, ValueError, KeyError) as exc:
        return [f'historical synthetic contract: {exc}']
    return []
