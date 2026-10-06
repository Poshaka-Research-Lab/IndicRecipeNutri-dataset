"""Contract tests for the canonical helper.  Parametrised over BOTH canonical files, because the shared
core (workers/budget/pmap/pmap_processes) must behave identically in the datasets and EAFR repos.
Run from a copy: pytest test_parallel_config_datasets.py   (parallel_config.py beside or on sys.path)."""
import concurrent.futures as cf
import importlib
import logging
import os
import sys
import threading
import time
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))
NAMES = ["parallel_config"]


@pytest.fixture(params=NAMES)
def M(request, monkeypatch):
    monkeypatch.delenv("PIPELINE_WORKERS", raising=False)
    monkeypatch.delenv("PIPELINE_WORKERS_REMAINING", raising=False)
    return importlib.import_module(request.param)


# ------------------------------------------------------------------ module-level fns (picklable)
def _sq(x):
    return x * x


def _slow_rev(x):
    time.sleep(0.05 * (5 - x))
    return x


def _budget_seen(_x):
    return importlib.import_module(os.environ["TEST_HELPER"]).budget()


def _boom_value(x):
    if x == 3:
        raise ValueError("boom %d" % x)
    return x


def _boom_runtime(x):
    if x == 3:
        raise RuntimeError("fn raised RuntimeError")
    return x


def _boom_os(x):
    if x == 2:
        raise OSError("fn raised OSError")
    return x


# ------------------------------------------------------------------ workers()
def test_workers_default_is_cpu_minus_two_min_one(M, monkeypatch):
    for cpus, want in [(32, 30), (3, 1), (2, 1), (1, 1), (None, 1)]:
        monkeypatch.setattr(os, "cpu_count", lambda c=cpus: c)
        assert M.workers() == want


def test_workers_env_positive_int(M, monkeypatch):
    monkeypatch.setenv("PIPELINE_WORKERS", "4")
    assert M.workers() == 4
    monkeypatch.setenv("PIPELINE_WORKERS", " 3 ")
    assert M.workers() == 3
    assert M.workers(cap=2) == 2
    monkeypatch.setenv("PIPELINE_WORKERS", "1")
    assert M.workers() == 1


def test_workers_empty_counts_as_unset(M, monkeypatch):
    monkeypatch.setenv("PIPELINE_WORKERS", "")
    monkeypatch.setattr(os, "cpu_count", lambda: 10)
    assert M.workers() == 8


@pytest.mark.parametrize("bad", ["0", "-3", "abc", "2.5", "1e2", "four"])
def test_workers_bad_value_raises_clear_error(M, monkeypatch, bad):
    monkeypatch.setenv("PIPELINE_WORKERS", bad)
    with pytest.raises(M.PipelineWorkersError) as ei:
        M.workers()
    assert "PIPELINE_WORKERS" in str(ei.value) and repr(bad) in str(ei.value)
    assert isinstance(ei.value, ValueError)


# ------------------------------------------------------------------ budget() / nesting
def test_budget_limited_by_remaining(M, monkeypatch):
    monkeypatch.setenv("PIPELINE_WORKERS", "8")
    assert M.budget() == 8
    monkeypatch.setenv("PIPELINE_WORKERS_REMAINING", "3")
    assert M.budget() == 3
    assert M.budget(cap=2) == 2
    monkeypatch.setenv("PIPELINE_WORKERS", "1")          # PIPELINE_WORKERS=1 always wins
    assert M.budget() == 1
    monkeypatch.setenv("PIPELINE_WORKERS_REMAINING", "0")
    with pytest.raises(M.PipelineWorkersError):
        M.budget()


def test_child_env_splits_budget(M, monkeypatch):
    monkeypatch.setenv("PIPELINE_WORKERS", "12")
    assert M.child_env(4)["PIPELINE_WORKERS_REMAINING"] == "3"
    assert M.child_env(30)["PIPELINE_WORKERS_REMAINING"] == "1"      # never below 1
    assert os.environ.get("PIPELINE_WORKERS_REMAINING") is None       # does not mutate os.environ


def test_dag_times_seed_sweep_cannot_oversubscribe(M, monkeypatch):
    """Outer pool of 4 on a budget of 8: each child sees 2; an inner pool in it never exceeds 2."""
    monkeypatch.setenv("PIPELINE_WORKERS", "8")
    monkeypatch.setenv("TEST_HELPER", M.__name__)
    assert M.pmap(_budget_seen, range(4), n_workers=4) == [2, 2, 2, 2]
    assert os.environ.get("PIPELINE_WORKERS_REMAINING") is None       # restored
    assert M.pmap_processes(_budget_seen, range(4), n_workers=4) == [2, 2, 2, 2]
    assert os.environ.get("PIPELINE_WORKERS_REMAINING") is None
    monkeypatch.setenv("PIPELINE_WORKERS_REMAINING", "2")             # already inside an outer pool
    assert M.pmap(_budget_seen, range(4), n_workers=4) == [1, 1, 1, 1]
    assert os.environ["PIPELINE_WORKERS_REMAINING"] == "2"            # restored to the outer value


def test_nested_restores_on_exception(M, monkeypatch):
    monkeypatch.setenv("PIPELINE_WORKERS", "8")
    with pytest.raises(KeyError):
        with M.nested(2):
            assert os.environ["PIPELINE_WORKERS_REMAINING"] == "4"
            raise KeyError
    assert "PIPELINE_WORKERS_REMAINING" not in os.environ


# ------------------------------------------------------------------ pmap ordering
@pytest.mark.parametrize("which", ["pmap", "pmap_processes"])
def test_pmap_results_in_input_order(M, monkeypatch, which):
    monkeypatch.setenv("PIPELINE_WORKERS", "4")
    f = getattr(M, which)
    assert f(_slow_rev, range(5)) == [0, 1, 2, 3, 4]               # finishes in reverse order
    assert f(_sq, []) == []
    assert f(_sq, [7]) == [49]


def test_pmap_unordered_is_a_permutation(M, monkeypatch):
    monkeypatch.setenv("PIPELINE_WORKERS", "4")
    out = M.pmap(_slow_rev, range(5), ordered=False)
    assert sorted(out) == [0, 1, 2, 3, 4]
    assert out != [0, 1, 2, 3, 4]                                   # completion order, not input order


# ------------------------------------------------------------------ exceptions propagate, never re-run
@pytest.mark.parametrize("exc_fn,exc", [(_boom_value, ValueError), (_boom_runtime, RuntimeError), (_boom_os, OSError)])
def test_worker_exception_propagates_threads_without_rerun(M, monkeypatch, exc_fn, exc):
    monkeypatch.setenv("PIPELINE_WORKERS", "4")
    calls, lock = [], threading.Lock()

    def fn(x):
        with lock:
            calls.append(x)
        return exc_fn(x)

    with pytest.raises(exc):
        M.pmap(fn, range(6))
    assert len(calls) == len(set(calls)), f"an item ran twice (silent sequential re-run): {calls}"


@pytest.mark.parametrize("exc_fn,exc", [(_boom_value, ValueError), (_boom_runtime, RuntimeError), (_boom_os, OSError)])
def test_worker_exception_propagates_processes(M, monkeypatch, exc_fn, exc):
    monkeypatch.setenv("PIPELINE_WORKERS", "3")
    with pytest.raises(exc):
        M.pmap_processes(exc_fn, range(6))


# ------------------------------------------------------------------ fallback only when pool cannot start
class _NoStart:
    def __init__(self, *a, **k):
        raise RuntimeError("can't start new thread")


def test_fallback_when_pool_cannot_start(M, monkeypatch, caplog):
    monkeypatch.setenv("PIPELINE_WORKERS", "4")
    monkeypatch.setattr(M, "ThreadPoolExecutor", _NoStart)
    with caplog.at_level(logging.WARNING, logger="parallel"):
        assert M.pmap(_sq, range(5)) == [0, 1, 4, 9, 16]
    assert "could not start" in caplog.text                          # logged, not silent
    monkeypatch.setattr(M, "ProcessPoolExecutor", _NoStart)
    with caplog.at_level(logging.WARNING, logger="parallel"):
        assert M.pmap_processes(_sq, range(5)) == [0, 1, 4, 9, 16]


def test_submit_failure_runs_only_the_remainder_sequentially(M, monkeypatch, caplog):
    monkeypatch.setenv("PIPELINE_WORKERS", "4")

    class Flaky(cf.ThreadPoolExecutor):
        n = 0

        def submit(self, fn, *a, **k):
            Flaky.n += 1
            if Flaky.n > 2:
                raise RuntimeError("can't start new thread")
            return super().submit(fn, *a, **k)

    monkeypatch.setattr(M, "ThreadPoolExecutor", Flaky)
    calls, lock = [], threading.Lock()

    def fn(x):
        with lock:
            calls.append(x)
        return x * 10

    with caplog.at_level(logging.WARNING, logger="parallel"):
        assert M.pmap(fn, range(6)) == [0, 10, 20, 30, 40, 50]
    assert sorted(calls) == list(range(6)), f"each item must run exactly once: {calls}"
    assert "remainder sequentially" in caplog.text


def test_broken_process_pool_before_any_result_falls_back_logged(M, monkeypatch, caplog):
    monkeypatch.setenv("PIPELINE_WORKERS", "4")

    class Broken:
        def __init__(self, *a, **k):
            pass

        def submit(self, fn, *a, **k):
            f = cf.Future()
            f.set_exception(BrokenProcessPool("worker died"))
            return f

        def shutdown(self, *a, **k):
            pass

    monkeypatch.setattr(M, "ProcessPoolExecutor", Broken)
    with caplog.at_level(logging.WARNING, logger="parallel"):
        assert M.pmap_processes(_sq, range(4)) == [0, 1, 4, 9]
    assert "broke" in caplog.text


def test_broken_process_pool_after_results_raises(M, monkeypatch):
    monkeypatch.setenv("PIPELINE_WORKERS", "4")

    class Half:
        n = 0

        def __init__(self, *a, **k):
            pass

        def submit(self, fn, *a, **k):
            f = cf.Future()
            Half.n += 1
            if Half.n == 1:
                f.set_result(fn(*a, **k))
            else:
                f.set_exception(BrokenProcessPool("died midway"))
            return f

        def shutdown(self, *a, **k):
            pass

    monkeypatch.setattr(M, "ProcessPoolExecutor", Half)
    with pytest.raises(BrokenProcessPool):
        M.pmap_processes(_sq, range(4))


# ------------------------------------------------------------------ PIPELINE_WORKERS=1 is the sequential path
def test_one_worker_is_exact_sequential(M, monkeypatch):
    monkeypatch.setenv("PIPELINE_WORKERS", "1")
    monkeypatch.setattr(M, "ThreadPoolExecutor", lambda *a, **k: pytest.fail("pool built at 1 worker"))
    monkeypatch.setattr(M, "ProcessPoolExecutor", lambda *a, **k: pytest.fail("pool built at 1 worker"))
    seen = []
    main = threading.get_ident()

    def fn(x):
        seen.append((x, threading.get_ident(), os.environ.get("PIPELINE_WORKERS_REMAINING")))
        return x + 1

    assert M.pmap(fn, [5, 3, 9]) == [6, 4, 10]
    assert M.pmap_processes(fn, [5, 3, 9]) == [6, 4, 10]
    assert [s[0] for s in seen] == [5, 3, 9, 5, 3, 9]                # original order, in-process
    assert all(s[1] == main and s[2] is None for s in seen)          # same thread, env untouched
    with pytest.raises(ValueError):                                  # exception surfaces unchanged
        M.pmap(_boom_value, range(5))
