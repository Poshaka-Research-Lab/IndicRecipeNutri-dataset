#!/usr/bin/env python3
r"""Standard implicit-feedback top-N baselines over `data/interactions/`.

Port of the generation-v1 `baselines.py`, which shipped inside the data directory and could
not be re-run: it hardcoded `D = "/tmp/bench/synth50"`, a path on another machine. Paths are
arguments here, and the script lives in `scripts/` with the rest of the build chain.

TWO CORRECTIONS TO THE v1 SCRIPT, both visible in the artefact it published.

1. IT MISLABELLED THE DATASET. v1's `baseline_results.json` records
   `"dataset": "bench_foodcom"`. These baselines were never run on Food.com — they are
   computed over the synthetic Indian-recipe interaction log in this repository. A reader
   joining that field to a Food.com benchmark would be comparing unrelated numbers.

2. IT SEEDED ONLY NUMPY'S GLOBAL RNG. BPR-MF draws negatives with `np.random.randint` and
   shuffles with `np.random.shuffle`, so the run was reproducible only if nothing else had
   touched the global state first. A dedicated Generator is threaded through instead.

Protocol, unchanged and stated so the numbers are interpretable: per-user leave-last-20%-out
(the temporal split written by build_interactions.py), full-ranking over every item, seen
items masked out of the candidate scores.

Usage:
    python scripts/build_interaction_baselines.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from release_config import REPO_ROOT  # noqa: E402

K1, K2 = 10, 20


def load_ui(path: Path) -> dict[int, list[int]]:
    d: dict[int, list[int]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        d[int(parts[0])] = [int(x) for x in parts[1:]]
    return d


def evaluate(score_fn, name: str, train: dict, test: dict, test_users: list[int],
             n_items: int, batch: int = 256) -> dict:
    t0 = time.time()
    rec10 = rec20 = ndcg10 = hr10 = 0.0
    n = 0
    idcg = np.array([1 / np.log2(i + 2) for i in range(K1)]).cumsum()
    for s in range(0, len(test_users), batch):
        us = test_users[s:s + batch]
        scores = score_fn(us)
        for bi, u in enumerate(us):
            sc = scores[bi].copy()
            seen = train.get(u)
            if seen:
                sc[seen] = -1e9
            top = np.argpartition(-sc, min(K2, n_items - 1))[:K2]
            top = top[np.argsort(-sc[top])]
            gt = set(test[u])
            hits20 = [1 if it in gt else 0 for it in top]
            hits10 = hits20[:K1]
            nh = sum(hits10)
            rec10 += nh / min(len(gt), K1)
            rec20 += sum(hits20) / min(len(gt), K2)
            hr10 += 1.0 if nh else 0.0
            dcg = sum(h / np.log2(r + 2) for r, h in enumerate(hits10))
            ndcg10 += dcg / idcg[min(len(gt), K1) - 1]
            n += 1
    out = {"model": name,
           "Recall@10": round(rec10 / n, 4), "Recall@20": round(rec20 / n, 4),
           "NDCG@10": round(ndcg10 / n, 4), "HR@10": round(hr10 / n, 4)}
    print(f"  {name:<12} Recall@10={out['Recall@10']:.4f}  Recall@20={out['Recall@20']:.4f}  "
          f"NDCG@10={out['NDCG@10']:.4f}  HR@10={out['HR@10']:.4f}   ({time.time() - t0:.0f}s)")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=REPO_ROOT / "data" / "interactions")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dim", type=int, default=64)
    ap.add_argument("--epochs", type=int, default=25)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    train = load_ui(args.data / "train.txt")
    test = load_ui(args.data / "test.txt")
    n_users = max(max(train), max(test)) + 1
    n_items = max(max(max(v) for v in train.values()),
                  max(max(v) for v in test.values())) + 1
    print(f"users {n_users:,}  items {n_items:,}")

    rows = [u for u in train for _ in train[u]]
    cols = [i for u in train for i in train[u]]
    R = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n_users, n_items))
    test_users = sorted(test)
    results = []

    pop = np.asarray(R.sum(0)).ravel()
    results.append(evaluate(lambda us: np.tile(pop, (len(us), 1)), "Popularity",
                            train, test, test_users, n_items))

    col_norm = np.sqrt(np.asarray(R.multiply(R).sum(0)).ravel()) + 1e-9
    Rc = (R @ sp.diags(1.0 / col_norm)).tocsr()
    sim = (Rc.T @ Rc).tocsr()
    sim.setdiag(0)
    sim.eliminate_zeros()
    print(f"  ItemKNN similarity nnz={sim.nnz:,}")
    results.append(evaluate(lambda us: np.asarray((R[us] @ sim).todense()), "ItemKNN",
                            train, test, test_users, n_items))

    lr, reg = 0.05, 0.002
    U = rng.standard_normal((n_users, args.dim)) * 0.01
    V = rng.standard_normal((n_items, args.dim)) * 0.01
    pairs = np.array([(u, i) for u in train for i in train[u]])
    t0 = time.time()
    for _ in range(args.epochs):
        rng.shuffle(pairs)
        for s in range(0, len(pairs), 4096):
            b = pairs[s:s + 4096]
            uu, ii = b[:, 0], b[:, 1]
            jj = rng.integers(0, n_items, size=len(b))
            d = 1 / (1 + np.exp(np.einsum("bd,bd->b", U[uu], V[ii])
                                - np.einsum("bd,bd->b", U[uu], V[jj])))
            np.add.at(U, uu, lr * ((V[ii] - V[jj]) * d[:, None] - reg * U[uu]))
            np.add.at(V, ii, lr * (U[uu] * d[:, None] - reg * V[ii]))
            np.add.at(V, jj, lr * (-U[uu] * d[:, None] - reg * V[jj]))
    print(f"  BPR-MF trained {args.epochs} epochs ({time.time() - t0:.0f}s)")
    results.append(evaluate(lambda us: U[us] @ V.T, "BPR-MF",
                            train, test, test_users, n_items))

    payload = {
        "dataset": "IndicRecipeNutri synthetic interactions (data/interactions, v4)",
        "generator": "scripts/build_interactions.py",
        "evaluator": "scripts/build_interaction_baselines.py",
        "seed": args.seed,
        "n_users": int(n_users), "n_items": int(n_items), "n_train_int": int(R.nnz),
        "metrics": results,
        "protocol": "implicit top-N; per-user leave-last-20%-out (temporal); full-item "
                    "ranking; seen items masked. Synthetic behaviour, not observed users.",
    }
    (args.data / "baseline_results.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"\nwrote {args.data / 'baseline_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
