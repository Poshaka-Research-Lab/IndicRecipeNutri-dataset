# Synthetic Indian-Recipe Interaction Log — Distribution Report

Generated 2026-08-21 with numpy seed 42. Source: 224,003 recipes.

## Scale
- Users: 50,000
- Interactions (explicit 1-5): 990,273 (mean 19.8/user)
- Distinct items rated: 18,096

## Rating distribution (achieved vs target, normalized dropping implicit-0)
| Star | Achieved | Target |
|------|----------|--------|
| 5★ | 75.93% | 75.79% |
| 4★ | 17.09% | 16.84% |
| 3★ | 4.08% | 4.21% |
| 2★ | 1.45% | 2.11% |
| 1★ | 1.45% | 1.05% |

## Per-user interaction count (heavy-tailed lognormal, clip [5,200])
| pctl | 1 | 5 | 25 | 50 | 75 | 90 | 95 | 99 |
|------|------|------|------|------|------|------|------|------|
| count | 5 | 5 | 9 | 15 | 25 | 39 | 51 | 85 |

min=5, max=200, mean=19.8

## User diet split
- Vegetarian: 39.8%
- Non-Vegetarian: 35.0%
- Vegan: 15.0%
- Eggetarian: 10.1%

## Region coverage of users
28 regions have recipes; 28 are covered by ≥1 user (Pan-Indian share 25.1%).

<details><summary>users per home_region</summary>

- Pan-Indian: 12553
- Tamil Nadu: 3736
- Kerala: 3580
- South India: 3520
- Punjab: 3293
- North India: 3045
- West Bengal: 2658
- Maharashtra: 2310
- Karnataka: 2308
- Mughlai (North India): 2016
- Gujarat: 2000
- Andhra Pradesh: 1397
- Goa: 1265
- Bihar: 975
- Telangana: 932
- Rajasthan: 924
- Uttar Pradesh: 709
- Jammu & Kashmir: 679
- Sindhi (community): 589
- Parsi (community): 381
- Assam: 254
- Himachal Pradesh: 249
- Odisha: 246
- East India: 104
- Uttarakhand: 91
- Nagaland: 88
- West India: 68
- Manipur: 30
</details>

## KGAT export
- After iterative 10-core on positives (rating≥4): 821,213 positives, 35,833 users, 16,688 items
- Temporal 80/20 split: train 658,098 / test 163,115
- KG: 74,576 triples over 16,737 entities, 5 relations (has_region/diet/course/healthgrade/spice)

## Integrity checks
- (a) Diet compatibility HELD: Vegan-user→non-Vegan ratings = 0; Veg/Egg-user→Non-Veg ratings = 0 (expected 0).
- (b) 10-core satisfied: every retained user ≥10 items, every retained item ≥10 users.
- (c) Train/test leakage = 0 (expected 0).