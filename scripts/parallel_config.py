"""Canonical parallel helper, datasets repo (gates, release scripts, tools).  Copies are byte-identical.

Install at: D:/datasets/_admin/scripts/parallel_config.py   (rebuild_all.py puts that dir on sys.path;
                                                             gate scripts there get it as sys.path[0])
            D:/datasets/IndicRecipeNutri-dataset/scripts/parallel_config.py   (release scripts)
            vendored, and hashed into the freeze, inside the next tools package (D13)

workers()  = $PIPELINE_WORKERS if a positive int (a bad value raises PipelineWorkersError),
             else max(1, cpu_count - 2).  PIPELINE_WORKERS=1 is the exact sequential path.
budget()   = workers(), limited by $PIPELINE_WORKERS_REMAINING.  An outer pool sets that for its
             children (pmap/pmap_processes do it automatically; child_env() does it for
             subprocess launchers such as a DAG runner), so outer x inner cannot oversubscribe.
pmap / pmap_processes (fn, items, ordered=True) = results in input order; exceptions raised by
             fn propagate; sequential fallback ONLY when the pool cannot start, and it is logged.
"""
from __future__ import annotations

import logging
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool

log = logging.getLogger("parallel")

ENV_WORKERS = "PIPELINE_WORKERS"
ENV_REMAINING = "PIPELINE_WORKERS_REMAINING"


class PipelineWorkersError(ValueError):
    """PIPELINE_WORKERS / PIPELINE_WORKERS_REMAINING is set to something that is not a positive int."""


def _env_positive_int(name):
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    try:
        n = int(raw.strip())
    except ValueError:
        n = 0
    if n < 1:
        raise PipelineWorkersError(f"{name} must be a positive integer, got {raw!r}")
    return n


def workers(cap=None):
    """Top-level worker count: $PIPELINE_WORKERS if a positive int, else max(1, cpu_count - 2).

    A set-but-bad value (0, negative, non-numeric, fractional) raises PipelineWorkersError; it is
    never clamped.  An empty value counts as unset.  1 means the exact sequential path.
    """
    n = _env_positive_int(ENV_WORKERS)
    if n is None:
        n = max(1, (os.cpu_count() or 1) - 2)
    return min(n, cap) if cap else n


def budget(cap=None):
    """Workers THIS level may use: workers(), further limited by $PIPELINE_WORKERS_REMAINING
    when an outer pool set it for its children.  Pools size themselves from budget(), so a DAG
    runner (or any outer pool) times an inner pool cannot exceed the top-level worker count."""
    n = workers()
    rem = _env_positive_int(ENV_REMAINING)
    if rem is not None:
        n = min(n, rem)
    return min(n, cap) if cap else n


def child_env(n_slots, env=None):
    """Environment for one of `n_slots` concurrent children: REMAINING = max(1, budget() // n_slots)."""
    out = dict(os.environ if env is None else env)
    out[ENV_REMAINING] = str(max(1, budget() // max(1, int(n_slots))))
    return out


class nested:
    """Context manager: while open, in-process code and spawned children see REMAINING for
    `n_slots` concurrent children.  Restores the previous value on exit.  Process-global (os.environ),
    so do not run two unrelated outer pools from different threads of one process at once."""

    def __init__(self, n_slots):
        self.n_slots = n_slots

    def __enter__(self):
        self._old = os.environ.get(ENV_REMAINING)
        os.environ[ENV_REMAINING] = child_env(self.n_slots)[ENV_REMAINING]
        return self

    def __exit__(self, *exc):
        if self._old is None:
            os.environ.pop(ENV_REMAINING, None)
        else:
            os.environ[ENV_REMAINING] = self._old
        return False


def _run_pool(make_pool, fn, items, w, ordered, pool_failures):
    """Core of pmap/pmap_processes.

    Sequential fallback happens ONLY when the pool cannot start: constructor error, submit
    raising RuntimeError/OSError (the not-yet-submitted remainder then runs here; submitted items
    are collected, never re-run), or a broken process pool before any result was delivered.  An
    exception raised by `fn` propagates; work not yet started is cancelled.
    """
    n = len(items)
    try:
        ex = make_pool(w)
    except (RuntimeError, OSError) as e:
        log.warning("pool could not start (%r); running sequentially", e)
        return [fn(x) for x in items]
    results = [None] * n
    futs, completion = [], []
    redo_all = False
    try:
        with nested(w):
            try:
                for x in items:
                    futs.append(ex.submit(fn, x))
            except (RuntimeError, OSError) as e:
                log.warning("pool stopped accepting work after %d of %d items (%r); "
                            "running the remainder sequentially", len(futs), n, e)
            try:
                if ordered:
                    for i, f in enumerate(futs):
                        results[i] = f.result()
                        completion.append(i)
                else:
                    index = {f: i for i, f in enumerate(futs)}
                    for f in as_completed(futs):
                        results[index[f]] = f.result()
                        completion.append(index[f])
            except pool_failures as e:
                if completion:
                    raise
                log.warning("pool broke before delivering any result (%r); running sequentially", e)
                redo_all = True
    except BaseException:
        ex.shutdown(wait=True, cancel_futures=True)
        raise
    ex.shutdown(wait=True, cancel_futures=True)
    if redo_all:
        return [fn(x) for x in items]
    for i in range(len(futs), n):                       # non-empty only after a submit failure
        results[i] = fn(items[i])
        completion.append(i)
    return results if ordered else [results[i] for i in completion]


def pmap(fn, items, *, n_workers=None, ordered=True):
    """Map fn over items with a thread pool.  ordered=True: results in input order.
    ordered=False: completion order (only for callers that do not depend on order).
    Worker exceptions propagate.  One worker (or <= 1 item) is the exact sequential list
    comprehension: no pool, no environment change."""
    items = list(items)
    w = min(n_workers or budget(), len(items)) or 1
    if w == 1:
        return [fn(x) for x in items]
    return _run_pool(ThreadPoolExecutor, fn, items, w, ordered, ())


def pmap_processes(fn, items, *, n_workers=None, ordered=True):
    """As pmap, over processes (fn and items must be picklable; fn a top-level function).  Children
    inherit PIPELINE_WORKERS_REMAINING = budget // pool size."""
    items = list(items)
    w = min(n_workers or budget(), len(items)) or 1
    if w == 1:
        return [fn(x) for x in items]
    return _run_pool(ProcessPoolExecutor, fn, items, w, ordered, (BrokenProcessPool,))
