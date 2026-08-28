# IndicRecipeNutri-Interactions (synthetic, v2 / 50K) — dataset card

A synthetic **user–recipe interaction benchmark** over the IndicRecipeNutri Indian-recipe corpus,
built in the style of MealRec+ (SIGIR'24) and HUMMUS (RecSys'23) so collaborative and KG
recommenders can be trained and compared on Indian cuisine — which no existing interaction
dataset covers. This is the 50K-user version (supersedes the 20K pilot).

## Composition
- **50,000 users**, each profiled: home_region (28 Indian regions), diet
  (Vegetarian/Vegan/Non-Vegetarian/Eggetarian), health_profile
  (general/diabetic/heart_lowsodium/weight_loss), spice_pref (mild/medium/hot), age_band.
- **990,273 explicit 1–5 ratings**; rating skew calibrated to real Food.com/HUMMUS
  (5★ 75.9% · 4★ 17.1% · 3★ 4.1% · 2★ 1.5% · 1★ 1.5%); per-user counts lognormal
  (median 15, p95 51, p99 85, max 200, mean 19.8).
- After positives (≥4) + iterative 10-core + per-user temporal 80/20 split:
  **35,833 users / 16,688 items / 821,213 interactions** (train 658,098 / test 163,115),
  **0** train/test leakage. Recipe-attribute KG: **74,576 triples** over 5 relations
  (has_region, has_diet, has_course, has_healthgrade, has_spice).
- Region coverage: all 28 regions with recipes represented (Pan-Indian held to 25.1%).
  Diet split: Veg 39.8% / Non-Veg 35.0% / Vegan 15.0% / Egg 10.1%.

## Generation model (reproducible — gen.py, seed 42, ZIPF_EXP=0.35, HOTC=18000)
affinity(u,r) = 0.35·region-match + hard diet-compatibility filter + 0.20·health-match
(diabetic→low glycemic/grade A-B; heart→low sodium/satfat; weight-loss→low calories) +
0.15·spice-match + 0.10·popularity + noise; a capped flat hot-catalog exposure term controls
item retention (tuned so ~16.7k recipes survive the 10-core). Recipes sampled ∝ softmax(affinity);
rating from within-user affinity percentile mapped onto the calibrated skew.

## Baselines (this release; per-user leave-last-20%-out, full-ranking, seen-item masking)
| Model | Recall@10 | Recall@20 | NDCG@10 | HR@10 |
|---|---|---|---|---|
| Popularity | 0.0144 | 0.0231 | 0.0120 | 0.0611 |
| ItemKNN | 0.0089 | 0.0139 | 0.0079 | 0.0461 |
| BPR-MF | 0.0083 | 0.0139 | 0.0064 | 0.0341 |

Numbers sit in a realistic regime (ranking over 16.7k items). Popularity leads under this
sparsity, as often seen on large sparse logs.

## Files
interactions.csv (user_id,recipe_id,rating,date) · users.csv · KGAT-format (train/test.txt,
user/item/entity/relation_list.txt, kg_final.txt) · stats.json · DISTRIBUTION_REPORT.md ·
gen.py · baselines.py · baseline_results.json.

## Limitations / ethics
Synthetic — not real human behaviour; rewards methods that recover region/diet/health structure.
Use for method comparison / cold-start, not for claims about real Indian users. recipe_id joins
to the IndicRecipeNutri master. Generated 2026-08-21.
