# Releasing

Tag-driven. Pushing a `v*.*.*` tag verifies the payload and, only if every check passes,
publishes a GitHub Release; Zenodo's webhook then mints the version DOI.

```
git tag v0.3.0 && git push origin v0.3.0
        │
        ├─ verify  ── checkout (lfs: true)
        │             ├─ no LFS pointers in the checkout
        │             ├─ ZIPBALL carries real LFS content   ← protects the Zenodo record
        │             ├─ verify_release.py --strict-checksums
        │             ├─ tag == DATASET_VERSION == CITATION.cff
        │             └─ payload summary
        │
        └─ release ── notes from the CHANGELOG section for this tag
                      └─ gh release create (published, not draft)
                                    │
                                    └─ Zenodo webhook → version DOI
```

The verifier is the point. **A tag must not be able to publish a payload that leaks withheld
prose, has drifted from its expected counts, or is missing the audit artefacts the datasheet
refers to.** Every check runs before the release is created, and the release job `needs:` it.

---

## One-time setup — these are yours to do, not the workflow's

### 1. Push the outstanding work

The repository is **not** empty — `refs/heads/main` on GitHub is already at the same commit
as local `HEAD`. (An earlier revision of this file said otherwise; that was wrong.) What is
outstanding is the working tree, and a tag pointing at a commit the remote does not carry
would build the wrong payload.

```bash
git push origin main            # then check: git ls-remote origin refs/heads/main
```

### 2. Turn on "Include Git LFS objects in archives"  ⚠️ before the first tag

**Settings → General → Archives → ☑ Include Git LFS objects in archives**

Large artefacts (`*.parquet` and the bulk `synthetic_interactions*/` files) are stored in Git LFS.
GitHub omits LFS content from source archives **by default**, and Zenodo archives the
zipball — so with this off, the DOI would point at a record full of 130-byte pointer stubs,
and nothing would say so.

The workflow downloads its own zipball and fails the build if that happens, so the setting
cannot be silently off. But the check costs a failed release; setting it first is cheaper.

### 3. Connect Zenodo  ⚠️ before the first tag

[zenodo.org](https://zenodo.org) → **GitHub** → flip this repository **ON**.

Zenodo only archives releases created **after** the switch is on. A release published first
will not be archived retroactively — you would have to tag again.

`.zenodo.json` in the repo root supplies the metadata (title, creators, licence, keywords);
Zenodo reads it on each archive.

---

## Every release

1. **Rebuild and gate.** `python D:\datasets\_admin\rebuild_all.py` — all eight gates green.
2. **Update `CHANGELOG.md`** with a `## [x.y.z] — YYYY-MM-DD` section. The workflow extracts
   exactly this section as the release notes; if it is missing, the release publishes with
   "No CHANGELOG entry", which is worse than a wrong number because nobody reads it as an
   error.
3. **Bump all three version declarations** — the workflow refuses to publish unless they
   agree, because the failure it guards is "two of the three were updated":
   - `scripts/release_config.py` → `DATASET_VERSION`
   - `CITATION.cff` → `version` and `date-released`
   - `.zenodo.json` → `version` and `publication_date`
4. **Regenerate checksums** — `python scripts/make_checksums.py`. Editing the version strings
   changes `.zenodo.json` and `CITATION.cff`, whose digests are pinned; skipping this fails
   `--strict-checksums`. Adding *any* file under `data/` or `docs/` fails it too: the
   verifier checks the manifest in both directions, so a new published file with no digest
   is a failure rather than a silent gap. (This very document was that gap on 2026-09-05.)
5. **Commit, then tag and push.**

```bash
python scripts/verify_release.py --strict-checksums   # rehearse locally first
git add -A && git commit -m "Release 0.3.0"
git push origin main
git tag v0.3.0 && git push origin v0.3.0
```

### Rehearsing without publishing

Actions → **release** → *Run workflow* → `dry_run: true`. Runs the whole `verify` job and
stops before creating anything.

---

## Watch the LFS quota

GitHub's free tier is **1 GB of LFS storage and 1 GB/month bandwidth**. Every rebuild of
`data/corpus/recipes_structured.parquet` (~99 MB) stores a **new** object — LFS keeps every
version — so roughly **ten rebuilds** exhausts the free tier. Current tracked payload is
~510 MB across 53 LFS files.

When it gets close: buy a data pack, or move the largest artefacts to a Zenodo-only tier the
way `docs/PROVENANCE.md` already does for the ~930 MB embedding matrices.

## If a clone has no git-lfs

`verify_release.py --strict-checksums` **fails**, loudly, on pointer files rather than
validating a 130-byte stand-in as if it were the corpus. That is deliberate. Install
git-lfs and `git lfs pull`.

## Line endings — why the verifier checks for CRLF

`.gitattributes` normalises source and docs to LF. A document authored on Windows with a
tool that translates newlines is **CRLF in the working tree and LF in the object store**, so
`make_checksums.py` records a digest one byte per line longer than what a Linux checkout
delivers. `--strict-checksums` then passes on the authoring machine and fails on the runner,
during the tag build, on 13 files at once — which is where this was found on 2026-09-05.

`verify_release.py` now fails locally on CRLF in any checksummed `eol=lf` file. If you hit
it: rewrite the file with `newline="\n"` (or `dos2unix`), re-run `make_checksums.py`.
