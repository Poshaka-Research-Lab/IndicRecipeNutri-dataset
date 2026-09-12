"""Validate current graph diagnostics separately from a frozen silver baseline."""
import hashlib
import json
from pathlib import Path
from release_config import EXPECTED_SILVER_REGRESSION_SHA256, EXPECTED_BENCHMARK_QUERIES


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_benchmark(root):
    root = Path(root)
    folder = root / 'data/benchmark'
    problems = []
    try:
        manifest = json.loads((folder / 'BENCHMARK_MANIFEST.json').read_text(encoding='utf-8'))
        frozen = folder / 'silver_regression_v1.jsonl'
        current = folder / 'eval_queries.jsonl'
        checks = {
            'frozen regression': (digest(frozen), EXPECTED_SILVER_REGRESSION_SHA256),
            'manifest frozen regression': (manifest['frozen_regression_sha256'], EXPECTED_SILVER_REGRESSION_SHA256),
            'current queries': (digest(current), manifest['current_queries_sha256']),
            'current graph': (digest(root / 'data/kg/kg_edges.parquet'), manifest['graph_edges_sha256']),
        }
        for label, (actual, expected) in checks.items():
            if actual != expected:
                problems.append(f'{label} hash disagrees with benchmark contract')
        for path, expected in [(frozen, 67), (current, EXPECTED_BENCHMARK_QUERIES)]:
            qs = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
            if len(qs) != expected or len({q['query'] for q in qs}) != expected:
                problems.append(f'{path.name}: wrong count or duplicate query identities')
        baseline = [json.loads(line) for line in frozen.read_text(encoding='utf-8').splitlines() if line.strip()]
        active = [json.loads(line) for line in current.read_text(encoding='utf-8').splitlines() if line.strip()]
        if [(q['query'], q['template']) for q in baseline] != [(q['query'], q['template']) for q in active]:
            problems.append('current question definitions differ from frozen regression')
        protocol = json.loads((folder / 'eval_queries_protocol.json').read_text(encoding='utf-8'))
        if protocol['protocol'] != 'fixed_silver_v1' or protocol['queries_sha256'] != digest(current):
            problems.append('fixed silver label protocol missing or stale')
        if protocol['frozen_definition_sha256'] != EXPECTED_SILVER_REGRESSION_SHA256 or protocol['definitions_changed'] != 0:
            problems.append('fixed silver protocol changed question definitions')
        for query in active:
            key = query['template'] + '\n' + query['query']
            expected_id = 'silver_' + hashlib.sha256(key.encode()).hexdigest()[:16]
            if query.get('query_id') != expected_id or query.get('label_source') != 'full_graph_silver':
                problems.append('query identity or label provenance differs from fixed silver contract')
                break
        if manifest['current_query_count'] != EXPECTED_BENCHMARK_QUERIES:
            problems.append('manifest current query count is stale')
        if manifest['evaluation_mode'] != 'full-graph transductive diagnostic; not held-out human relevance':
            problems.append('benchmark evaluation mode must disclose full-graph silver provenance')
    except (OSError, ValueError, KeyError) as exc:
        problems.append(f'cannot validate benchmark manifest: {exc}')
    return problems
