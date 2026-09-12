"""Validate the edge attribute side table without rebuilding the full graph."""
import json
import pandas as pd


def validate_evidence(edges, evidence):
    keys = ['head', 'rel', 'tail']
    if not set(keys + ['attributes_json']) <= set(evidence.columns):
        return ['edge evidence lacks required columns']
    problems = []
    if evidence[keys].isna().any().any():
        problems.append('null edge evidence keys')
    if evidence.duplicated(keys).any():
        problems.append('duplicate edge evidence keys')
    live = pd.MultiIndex.from_frame(edges[keys])
    claims = pd.MultiIndex.from_frame(evidence[keys])
    missing = int((~claims.isin(live)).sum())
    if missing:
        problems.append(f'{missing} evidence rows refer to absent triples')
    for index, text in enumerate(evidence.attributes_json):
        try:
            attrs = json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
            if not isinstance(attrs, dict) or not attrs or {'rel', 'relation'} & set(attrs):
                raise ValueError('empty or reserved attributes')
        except (TypeError, ValueError) as exc:
            problems.append(f'invalid evidence JSON at row {index}: {exc}')
            break
    return problems


def validate_release_evidence(root):
    edges = pd.read_parquet(root / 'data/kg/kg_edges.parquet')
    evidence = pd.read_parquet(root / 'data/kg/kg_edge_evidence.parquet')
    return validate_evidence(edges, evidence)
