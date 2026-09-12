"""Checked flavour-view integration and explicit legacy identity resolution."""
from pathlib import Path
import hashlib
import json
import pandas as pd

KEYS = ['head', 'rel', 'tail']


def resolve_legacy_compound(legacy_id, crosswalk):
    targets = crosswalk.loc[crosswalk.legacy_node_id.eq(legacy_id), 'node_id'].unique()
    if len(targets) == 0:
        raise KeyError(f'unknown legacy compound ID {legacy_id}')
    if len(targets) > 1:
        raise ValueError(f'ambiguous legacy compound ID {legacy_id}; candidate IDs: {sorted(targets)}')
    return targets[0]


def merge_flavor_tables(nodes, edges, flavor_nodes, flavor_edges):
    compounds = nodes.loc[nodes.type.eq('compound')].set_index('node_id')
    if nodes.node_id.duplicated().any() or flavor_nodes.node_id.duplicated().any():
        raise ValueError('duplicate node IDs')
    if set(flavor_nodes.node_id) != set(compounds.index):
        raise ValueError('optional compound node set differs from core')
    for row in flavor_nodes.itertuples(index=False):
        if row.node_id not in compounds.index or str(compounds.at[row.node_id, 'pubchem_id']) != str(row.pubchem_id):
            raise ValueError('optional compound identity disagrees with core')
    actual = set(map(tuple, flavor_edges.loc[flavor_edges.rel.eq('has_compound'), KEYS].values))
    expected = set(map(tuple, edges.loc[edges.rel.eq('has_compound'), KEYS].values))
    if actual != expected:
        raise ValueError('optional ingredient-compound associations differ from core')
    merged = pd.concat([edges[KEYS], flavor_edges[KEYS]], ignore_index=True).drop_duplicates(KEYS).reset_index(drop=True)
    live = set(nodes.node_id)
    if not merged['head'].isin(live).all() or not merged['tail'].isin(live).all():
        raise ValueError('combined graph contains dangling endpoints')
    return nodes.copy(), merged


def load_with_flavor(root):
    root = Path(root)
    return merge_flavor_tables(
        pd.read_parquet(root / 'data/kg/kg_nodes.parquet'),
        pd.read_parquet(root / 'data/kg/kg_edges.parquet'),
        pd.read_parquet(root / 'data/kg_flavor/flavor_nodes.parquet'),
        pd.read_parquet(root / 'data/kg_flavor/flavor_edges.parquet'),
    )


def validate_release_flavor(root):
    try:
        from flavor_view import make_view
        kg = root / 'data/kg'
        expected_n, expected_e = make_view(*(pd.read_parquet(kg / name) for name in
            ['kg_nodes.parquet', 'kg_edges.parquet', 'kg_edge_evidence.parquet']))
        actual_n = pd.read_parquet(root / 'data/kg_flavor/flavor_nodes.parquet')
        actual_e = pd.read_parquet(root / 'data/kg_flavor/flavor_edges.parquet')
        pd.testing.assert_frame_equal(expected_n, actual_n)
        pd.testing.assert_frame_equal(expected_e, actual_e)
        crosswalk = pd.read_csv(kg / 'compound_id_crosswalk.csv', dtype=str)
        if crosswalk.duplicated(['legacy_node_id', 'node_id']).any():
            raise ValueError('duplicate crosswalk associations')
        if set(crosswalk.node_id) != set(expected_n.node_id):
            raise ValueError('crosswalk target set differs from current compounds')
        if not crosswalk.node_id.eq('compound::' + crosswalk.pubchem_id).all():
            raise ValueError('crosswalk CID identity mismatch')
        cardinality = crosswalk.groupby('legacy_node_id').node_id.transform('nunique')
        expected_status = cardinality.map(lambda n: 'ambiguous' if n > 1 else 'unique')
        if not crosswalk.status.eq(expected_status).all():
            raise ValueError('crosswalk ambiguity status is incorrect')
        manifest = json.loads((root / 'data/kg_flavor/flavor_manifest.json').read_text(encoding='utf-8'))
        if manifest['nodes'] != len(expected_n) or manifest['relations'] != expected_e.rel.value_counts().to_dict():
            raise ValueError('flavour manifest counts are stale')
        inputs = ['kg_nodes.parquet', 'kg_edges.parquet', 'kg_edge_evidence.parquet']
        hashes = {name: hashlib.sha256((kg / name).read_bytes()).hexdigest() for name in inputs}
        if manifest['input_sha256'] != hashes:
            raise ValueError('flavour manifest source hashes are stale')
        return []
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        return [str(exc)]
