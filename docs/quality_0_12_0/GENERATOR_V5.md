# Separate published-attribute generator

`data/interactions_v5/` is a new synthetic choice benchmark beside unchanged v4. Version `published-attribute-generator-v5.1`, seed 20260928, 50000 fictional users and 20 distinct chosen items per user (1000000 events). Numeric user IDs belong only to the v5 namespace; do not join them to v4 identities.

Item inputs: Region, SpiceLevel, HealthGrade and rating_count_bin from the published item-attribute view. Profiles publish preferred region/spice and grade/popularity preference directions. Missing grade/rating contributes zero to utility and remains marked unknown in the item view; no hidden quality, hotness or item noise is created. HealthGrade is a source label; this is not a health or diet recommendation benchmark. No dietary restrictions are modeled for these fictional profiles.

Utility is a declared weighted sum of region match, spice match, signed normalized grade and signed rating-bin rank. Training coefficients are [1.4, 0.9, 0.5, 0.4]; test coefficients are [1.1, 1.2, 0.4, 0.5]. Temperature is 1. Events 0-15 train and 16-19 test, providing an explicit coefficient-shift mechanism. These are design choices, not fitted or empirically optimal parameters.

Sampling is exact softmax over remaining eligible items, without replacement within each user. Items with the same public attributes are grouped; group probability is remaining group size times exponentiated utility, followed by a uniform draw of an unused member. Independent unit tests compare the emitted probability to a direct per-item calculation. Every user has PCG64 streams derived from seed/user/profile-or-choice, recorded in the implementation. Full replay reproduced all users, events and truth values exactly.

Ordinary feature/log surfaces: users.parquet and interactions.parquet. Exact utility and conditional choice probabilities live only in `generator_truth/choice_probabilities.parquet`. They are an oracle evaluation surface, never ordinary model input. These probabilities describe the synthetic conditional mechanism, not real-world exposure propensities. No model-performance or realism claim has been measured.

Validation: 50000 users, 1000000 events, valid recipe foreign keys, unique user-item/event pairs, temporal split agreement, manifest and logical hashes, and exact full replay. The reference tests also prove extra hidden columns do not affect the generator. Keep the existing interactions directory byte-identical.
