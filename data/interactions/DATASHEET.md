# IndicRecipeNutri-Interactions (synthetic, v4 / 50K) — dataset card

A synthetic **user–recipe interaction benchmark** over the IndicRecipeNutri Indian-recipe
corpus, built in the style of MealRec+ (SIGIR'24) and HUMMUS (RecSys'23) so collaborative and
KG recommenders can be trained and compared on Indian cuisine, which no existing interaction
dataset covers.

**Synthetic. This is simulated behaviour, not observations of real users**, and it rewards
methods that recover the region / diet / health structure the generator encodes. It is not
evidence about human dietary preference.

Regenerate with `python scripts/build_interactions.py`; re-score with
`python scripts/build_interaction_baselines.py`. Both read and write only repository paths.

## Provenance

| | |
|---|---|
| Source | `data/corpus/recipes_structured.parquet` — **219,386** published recipes |
| Generator | `scripts/build_interactions.py`, seed 42 |
| Parameters | `HOTC=18000`, `ZIPF_EXP=0.35`, `GAMMA_EXP=0.6` |
| Withdrawn recipes referenced | **0** — enforced by the generator and re-checked by `verify_release.py` |
| Recipe id space | corpus `recipe_id`, **not** positional index |

Generating *from the published corpus* is what makes the zero above structural. The two
retired generations were built from a retrieval-side CSV that predated the withdrawals, so
they could only ever be **declared** clean at a pinned nonzero count.

## Composition

- **50,000 users**, each profiled: `home_region` (27 published Region codes), `diet`
  (Vegetarian / Vegan / Non-Vegetarian / Eggetarian), `health_profile`
  (general / diabetic / heart_lowsodium / weight_loss), `spice_pref` (mild / medium / hot),
  `age_band`.
- **990,273 explicit 1–5 ratings** over **18,010** distinct rated recipes; per-user counts
  lognormal, clipped to [5, 200] — median 15, mean 19.8, p95 51, p99 85.
- Rating skew calibrated to real Food.com / HUMMUS logs:

| Star | Achieved | Target |
|---|---:|---:|
| 5★ | 75.93% | 75.79% |
| 4★ | 17.09% | 16.84% |
| 3★ | 4.08% | 4.21% |
| 2★ | 1.45% | 2.11% |
| 1★ | 1.45% | 1.05% |

- After positives (≥4) + iterative 10-core + per-user temporal 80/20 split:
  **35,801 users / 16,567 items / 820,566 interactions** (train 657,610 / test 162,956),
  **0** train/test leakage.
- Recipe-attribute KG: **82,835 triples** over **16,614** entities and 5 relations
  (`has_region`, `has_diet`, `has_course`, `has_healthgrade`, `has_spice`).
- User diet split: Vegetarian 40.02% · Non-Vegetarian 34.79% · Vegan 14.96% ·
  Eggetarian 10.22%. All 27 regions that have recipes are represented by ≥1 user;
  Pan-Indian is held to 24.96%.

## Generation model

`affinity(u,r) = 0.35·region-match + 0.20·health-match + 0.15·spice-match + 0.10·popularity
+ noise`, over a **hard diet-compatibility filter**; recipes drawn ∝ softmax(affinity/0.3 +
0.6·log q), where `q` is a capped flat hot-catalogue exposure weight tuned so enough items
survive the 10-core. Rating assigned from the within-user affinity rank mapped onto the
calibrated skew.

Health match by profile: diabetic → low glycemic load + high HealthGrade; heart_lowsodium →
low sodium, low saturated fat, high grade; weight_loss → low calories, high grade;
general → grade only.

## Baselines

Per-user leave-last-20%-out (the temporal split above), full-item ranking, seen items masked.

| Model | Recall@10 | Recall@20 | NDCG@10 | HR@10 |
|---|---:|---:|---:|---:|
| Popularity | 0.0114 | 0.0196 | 0.0089 | 0.0496 |
| ItemKNN | 0.0059 | 0.0102 | 0.0050 | 0.0336 |
| BPR-MF | 0.0049 | 0.0088 | 0.0039 | 0.0227 |

Ranking over 16,567 items. Popularity leads, as it often does on large sparse logs. These are
reference points for comparison on this benchmark, not evidence that any method is good.

## What changed from the retired generations

v0.7.0 replaces `data/synthetic_interactions/` (v1) and `data/synthetic_interactions_v3/`
with this single directory. They were **not merged** — they were independent simulations
whose remapped id spaces collide (user 0 rated recipe 4489 in v1 and 121171 in v3; 2 of
~16,000 item entries agreed), so concatenating them would have invented users who rated
across two catalogues and destroyed both the 10-core property and the zero-leakage guarantee.
One coherent set could only come from regeneration.

Three defects in the retired generator were found while doing it, and all three are fixed
here rather than carried forward:

1. **The glycemic term never operated.** `gen.py` mapped `GlycemicLoad` through
   `{'low','medium','high'}`, but that column is ~98.6% numeric in both source CSVs and holds
   no such value, so every row fell to `.fillna(0.5)` and the `diabetic` profile (15% of
   users) silently reduced to HealthGrade alone. The categorical column it wanted,
   `gl_bucket`, sat directly beside it. v4 maps `gl_bucket`: **216,353 of 219,386 recipes
   (98.62%)**, against 0.00% before, and the build fails if that ever drops below half.
2. **Diet normalisation failed open.** Anything unrecognised returned `'Vegetarian'`, so
   **731** recipes carrying `Diet == 'unknown'` entered the Vegan, Vegetarian and Eggetarian
   pools — and the audit reported zero violations because it re-used the same function. Here
   an undeclared diet is its own class, excluded from every pool, and the audit reads the raw
   corpus column so it can actually fail. `verify_release.py` re-checks it independently at
   release time.
3. **Ids were positional.** Candidate selection produced dataframe row offsets, which were
   written into a column named `recipe_id` and read downstream as corpus ids. v4 maps
   position → `recipe_id` explicitly.

The retired directories remain in the v0.6.0 tag and its DOI for anyone reproducing published
results against them. They must not be joined to this one.

## Limitations and ethics

Synthetic behaviour, not real users; no human subjects and no personal data. Diet
compatibility is enforced as a hard constraint, but a *synthetic* guarantee says nothing
about a deployed system's safety — an allergen or dietary decision must not rest on this
benchmark. Region is the corpus's own state-level administrative-cultural label, unevenly
sampled, and interaction frequency here is a property of the generator, not of any
population's diet. Licensed as the rest of `data/`; see `LICENSE-DATA`.
