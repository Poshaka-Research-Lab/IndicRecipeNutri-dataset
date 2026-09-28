# 0.12.0 reproduction and acceptance

Use the frozen 0.11.0 data at `620496feb4aeffaee7b01e1892418924d8b2fd47` with the 0.12.0 builder code. Build only in a separate candidate checkout, passing a distinct protected baseline checkout to `--protected-root`. Never overwrite the upstream master or run the whole corpus rebuild for this additive update. Resolve Git LFS objects before verification.

The original input inventory is `quality_0_12_0/preflight_inventory.json` in the method workspace. Its SHA-256 is `00d917593ca41ab77267855076c7be86787d0bc5ae55ce6a7604ef3585485dc9`. It pins original data digests and the permitted local instruction master; source joins and the source-reader gate must pass before instruction-derived generation. Without that source, the builder can represent unavailable inputs but cannot reproduce the audited instruction outputs. Do not fabricate source text.

## Build order

1. Verify the baseline and input inventory using `scripts/quality_freeze_contract.py`.
2. Run `scripts/build_quality_flags.py` with `--root`, `--protected-root`, `--input-manifest`, `--source-workspace` and `--config docs/quality_0_12_0/quality_rules_v1.json`. The source workspace is the folder containing `paths.py`; no K006 workspace is needed by the production quality rules.
3. Create an LF-terminated file of sorted integer recipe IDs whose published `Split_v3` is `test`. There are 11,094 IDs; its SHA-256 must be `c3517fda7c05e07f1e0d7d6e9f0e1d7c4e408fbad25ab7e824ed61965beef717`. This exactly reconstructs the original partition input without reading K006.
4. Run `scripts/build_allergen_evidence.py` with `--root`, `--protected-root`, `--input-manifest` and `--heldout-ids` pointing to that file. Export review candidates with `scripts/export_allergen_review_queue.py` according to its CLI.
5. Run `scripts/item_card.py` and `scripts/build_nutrition_evidence.py`, each with `--root`, `--protected-root` and `--input-manifest`.
6. Run `scripts/build_interactions_v5.py` with `--root` and `--protected-root`; omit pilot/size overrides to reproduce the 50,000-user release candidate.

The local item-card text renderer is deliberately not materialized in the release. Generator user IDs are a separate namespace; never join them to legacy users solely on the integer ID.

## Checks

Run `python -m unittest discover -s tests -q`. Use `quality_release_contract.validate_release_quality_layers(root)` for complete additive structural checks, including item/nutrition reconstruction. Run `scripts/verify_interactions_v5.py --root ... --output ...` for full generator replay, with output outside checksum-protected files. Run repeat quality/allergen builds and compare logical hashes, output bytes and manifests.

Normalize source/docs/configuration to repository LF conventions before generating final hashes. An LF-only change to a pinned source/configuration still changes its byte digest: rebuild affected manifests, retain a before/after receipt and confirm unchanged semantics/payload. Do not hand-edit a manifest to hide a stale build.

Generate the dictionary and release facts with `scripts/make_data_dictionary.py` and `scripts/build_release_facts.py`. Generate final checksums with `scripts/make_checksums.py`, then run `scripts/verify_release.py --strict-checksums`. Keep logs/volatile receipts under `.local/` or in the method workspace to avoid self-referential checksums. Recheck legacy data against the baseline receipt after all changes.

Source inspection, engineering checks and semantic validation are distinct. The proposal in `docs/quality_0_12_0/VALIDATION_PROTOCOL.md` does not contain completed human judgments. Public distribution of instruction-derived flags remains subject to source-specific terms verification. IFCT retention records owner-confirmed permission. This workflow authorizes local candidate generation/integration, not a remote push, DOI publication or silent K006 re-pin.
