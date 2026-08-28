"""Write checksums/SHA256SUMS over every published artefact.

Paths are recorded repo-relative with forward slashes so the manifest verifies
identically on Windows and Linux.

Usage:  python scripts/make_checksums.py
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_config import REPO_ROOT  # noqa: E402

INCLUDE_DIRS = ["data", "docs"]
INCLUDE_FILES = ["README.md", "LICENSE-DATA", "LICENSE-CODE", "CITATION.cff", ".zenodo.json"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    targets: list[Path] = []
    for d in INCLUDE_DIRS:
        targets += [p for p in (REPO_ROOT / d).rglob("*") if p.is_file()]
    for f in INCLUDE_FILES:
        p = REPO_ROOT / f
        if p.exists():
            targets.append(p)

    out = REPO_ROOT / "checksums"
    out.mkdir(exist_ok=True)
    lines = []
    total = 0
    for p in sorted(targets, key=lambda x: x.as_posix()):
        rel = p.relative_to(REPO_ROOT).as_posix()
        lines.append(f"{sha256(p)}  {rel}")
        total += p.stat().st_size

    (out / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} digests, {total / 1e6:.1f} MB total -> checksums/SHA256SUMS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
