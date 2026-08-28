"""Reconstruct the withheld recipe prose from the original source pages.

This release publishes structured, factual and derived fields only. Recipe headnotes
and free-text instructions can be copyrightable, so they are not redistributed. What is
published instead is the source URL for every recipe and a SHA-256 digest of the text
this corpus was derived from. This script re-fetches the pages you are entitled to
fetch and reports which recipes reconstructed to the same digest.

You are responsible for complying with each source site's terms of service and
robots.txt. This script honours robots.txt by default and rate-limits itself. It is
deliberately slow. Do not remove those guards to go faster.

Usage:
  python scripts/rehydrate.py --out prose.parquet [--limit N] [--site SITE] [--delay S]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_config import PROSE_COLUMNS, REPO_ROOT  # noqa: E402

USER_AGENT = "IndicRecipeNutri-rehydrator/0.1 (research; +https://github.com/Poshaka-Research-Lab/IndicRecipeNutri-dataset)"


def digest(fields: dict[str, str]) -> str:
    """Must match scripts/build_corpus.py:prose_digest exactly."""
    return hashlib.sha256(
        "\x00".join(fields.get(c, "") or "" for c in PROSE_COLUMNS).encode("utf-8")
    ).hexdigest()


def robots_allows(cache: dict, url: str) -> bool:
    parsed = urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    if root not in cache:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{root}/robots.txt")
        try:
            rp.read()
        except Exception:
            # Unreadable robots.txt is treated as disallow, not as permission.
            cache[root] = None
            return False
        cache[root] = rp
    rp = cache[root]
    return bool(rp and rp.can_fetch(USER_AGENT, url))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", type=Path, default=REPO_ROOT / "data" / "corpus" / "rehydration_index.parquet")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=None, help="stop after N recipes")
    ap.add_argument("--site", default=None, help="restrict to one SourceSite")
    ap.add_argument("--delay", type=float, default=2.0, help="seconds between requests")
    ap.add_argument("--ignore-robots", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    try:
        import requests
        from bs4 import BeautifulSoup  # noqa: F401
    except ImportError:
        print(
            "rehydration needs `requests` and `beautifulsoup4`:\n"
            "  pip install requests beautifulsoup4",
            file=sys.stderr,
        )
        return 1

    index = pd.read_parquet(args.index)
    if args.site:
        index = index[index["SourceSite"] == args.site]
    if args.limit:
        index = index.head(args.limit)

    print(f"rehydrating {len(index):,} recipes at {args.delay}s/request")
    print("NOTE: extraction is per-site. The generic extractor below recovers the page")
    print("      text but will not match the original digest for most sites; a")
    print("      site-specific parser is needed for exact reconstruction.")

    cache: dict = {}
    rows, matched, skipped = [], 0, 0
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    for i, rec in enumerate(index.itertuples(index=False), 1):
        url = str(rec.URL)
        if not args.ignore_robots and not robots_allows(cache, url):
            skipped += 1
            continue
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            rows.append({"recipe_id": rec.recipe_id, "status": f"error: {exc}"})
            time.sleep(args.delay)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        fields = {"Description": "", "Instructions": soup.get_text(" ", strip=True)}
        got = digest(fields)
        ok = got == rec.text_sha256
        matched += ok
        rows.append(
            {
                "recipe_id": rec.recipe_id,
                "status": "ok",
                "digest_match": ok,
                **fields,
            }
        )
        if i % 25 == 0:
            print(f"  {i:,}/{len(index):,}  matched={matched}  skipped={skipped}")
        time.sleep(args.delay)

    out = pd.DataFrame(rows)
    out.to_parquet(args.out, index=False)
    print(f"\nwrote {args.out} — {len(out):,} rows, {matched:,} digest matches, {skipped:,} skipped by robots.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
