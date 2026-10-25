"""D-16: README node/relation count tables must equal the built KG (data/kg/kg_stats.json)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_release_facts as brf  # noqa: E402


def _block(text, summary):
    m = re.search(r"<summary><b>All \d+ " + re.escape(summary) + r"</b></summary>(.*?)</details>",
                  text, flags=re.S)
    assert m, summary
    return dict((k, int(v.replace(",", ""))) for k, v in re.findall(r"\| `(\w+)` \| ([\d,]+)", m[1]))


def test_readme_counts_match_built_kg():
    stats = json.loads((ROOT / "data/kg/kg_stats.json").read_text(encoding="utf-8"))
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert _block(text, "relation types, with counts") == stats["edge_types"]
    assert _block(text, "node types, with counts") == stats["node_types"]


def test_refresh_is_scoped_to_its_block():
    text = ("| `diet` | 7 |\n<details>\n<summary><b>All 2 node types, with counts</b></summary>\n"
            "| `diet` | 1 | | `zone` | 2 |\n</details>\n| `diet` | 7 |\n")
    out = brf._refresh_block(text, "node types, with counts", {"diet": 8, "zone": 5})
    assert out.count("| `diet` | 7 |") == 2
    assert "| `diet` | 8 | | `zone` | 5 |" in out
