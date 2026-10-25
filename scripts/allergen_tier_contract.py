"""Current allergen tiers describe current labels; removed tiers remain in history."""
import pandas as pd
from allergen_taxonomy import TOKENS

GENERATION = 'before_allergen_tier_reconciliation_v1'
# Later transactions that re-derived tier literals on rows of the 401 above. Each records, per changed row, the value it replaced.
LATER_GENERATIONS = ('before_diet_repair_v1',)
# Declared re-additions: a (recipe, class) the reconciliation removed as stale and a later owner-authorised transaction restored after reading the recipe
# text (fail-closed). Each names the generation that recorded the row's prior value and its decision record. The class must be back with the literal it
# was removed with, that generation's prior value must equal the current tiers without it, and the strict-removal check then applies to the rest.
REINSTATED = {
    (99336, 'gluten'): ('before_d16e_v1', 'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_E/LEAD_READ_5_GLUTEN_ROWS_2026-10-10.md; '
                                          'owner "Lead reads, fail-closed", OWNER_DECISIONS_BATCH_E_2026-10-10.json'),
    (99213, 'gluten'): ('before_d16i_v1', 'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I/review/review.md C3; '
                                          'owner "Keep + amend rules", OWNER_DECISIONS_BATCH_I1_ROUND2_2026-10-14.json point 1'),
}
# Declared first additions: a (recipe, class) on a row of the 401 above whose reconciliation prior never carried the class, added by a later
# owner-authorised transaction. There is no removed literal to restore, so the entry pins the literal. The class must be absent from the
# reconciliation prior and present now with exactly that literal, the named generation's prior value must equal the current tiers without it, and
# the strict-removal check then applies to the rest. Such a row may not also carry a REINSTATED entry or a later-generation record.
DECLARED_ADDITIONS = {
    (15690, 'gluten'): ('before_d16i_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I/review/review.md C3; '
                        'owner "Keep + amend rules", OWNER_DECISIONS_BATCH_I1_ROUND2_2026-10-14.json point 1'),
    # batch I-5 (D16M, 2026-10): owner-ruled additions on 401-set rows (I5-R10-1; post-install)
    (28021, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (30758, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (30758, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (40775, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (45836, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (47525, 'sulphites'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (52510, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (54385, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (81354, 'sulphites'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (85282, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (85282, 'milk'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (117104, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (119584, 'sulphites'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (126908, 'sulphites'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (126913, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (127710, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (127968, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (129964, 'gluten'): ('before_d16m_v1', 'derived',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (130331, 'gluten'): ('before_d16m_v1', 'derived',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (139708, 'sulphites'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (144079, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (144079, 'milk'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (155636, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (175159, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (184581, 'sulphites'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (184793, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (184793, 'milk'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (185104, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (202905, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (202905, 'milk'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (203067, 'gluten'): ('before_d16m_v1', 'derived',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (209602, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (210667, 'asafoetida'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (210679, 'ghee'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    (210679, 'milk'): ('before_d16m_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk) and BATCH_I4/OWNER_DECISIONS_BATCH_I4_ROUND2_2026-10-15.json (gluten vocabulary); owner ruling I5-R10-1 (OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json), applied only after an independent review APPROVE'),
    # batch K (D16O, data v21; K-R5-7): read-backed first additions on 401-set rows (K oats rule; 127968 milk on top of its D16M asafoetida)
    (3855, 'gluten'): ('before_d16o_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_K/OWNER_DECISIONS_BATCH_K_ROUND5_2026-10-23.json K-R5-7 (lead); BATCH_K/consolidate/K_TIER_CONTRACT_ADDITIONS.json (2e239099; K-R5-10 (d) inherited, was ce803282); decision lines: E5_oats_rule:E5_oats_rule'),
    (3860, 'gluten'): ('before_d16o_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_K/OWNER_DECISIONS_BATCH_K_ROUND5_2026-10-23.json K-R5-7 (lead); BATCH_K/consolidate/K_TIER_CONTRACT_ADDITIONS.json (2e239099; K-R5-10 (d) inherited, was ce803282); decision lines: E5_oats_rule:E5_oats_rule'),
    (24467, 'gluten'): ('before_d16o_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_K/OWNER_DECISIONS_BATCH_K_ROUND5_2026-10-23.json K-R5-7 (lead); BATCH_K/consolidate/K_TIER_CONTRACT_ADDITIONS.json (2e239099; K-R5-10 (d) inherited, was ce803282); decision lines: E5_oats_rule:E5_oats_rule'),
    (130714, 'gluten'): ('before_d16o_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_K/OWNER_DECISIONS_BATCH_K_ROUND5_2026-10-23.json K-R5-7 (lead); BATCH_K/consolidate/K_TIER_CONTRACT_ADDITIONS.json (2e239099; K-R5-10 (d) inherited, was ce803282); decision lines: E5_oats_rule:E5_oats_rule'),
    (214227, 'gluten'): ('before_d16o_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_K/OWNER_DECISIONS_BATCH_K_ROUND5_2026-10-23.json K-R5-7 (lead); BATCH_K/consolidate/K_TIER_CONTRACT_ADDITIONS.json (2e239099; K-R5-10 (d) inherited, was ce803282); decision lines: E5_oats_rule:E5_oats_rule'),
    (127968, 'milk'): ('before_d16o_v1', 'inherited',
                        'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_K/OWNER_DECISIONS_BATCH_K_ROUND5_2026-10-23.json K-R5-7 (lead); BATCH_K/consolidate/K_TIER_CONTRACT_ADDITIONS.json (2e239099; K-R5-10 (d) inherited, was ce803282); decision lines: S_dairy_egg_on_vegan:S_dairy_egg_on_vegan:127968:milk'),
}

# Declared combined re-addition (I5-R10-1; TODO B11): ONE row of the 401 above on which a later owner-authorised transaction both RE-ADDED a class the
# reconciliation removed (at the literal it was removed with) and ADDED classes the reconciliation prior never carried (at pinned literals). The entry
# pins: the generation of the row's prior record, the re-added {class: literal}, the added {class: literal}, and the exact remaining tiers, which must
# equal both the current tiers without the declared classes and that generation's single prior record. Additions only: any class removed, any literal
# changed or any extra class is refused, and the strict-removal check then applies to the remaining tiers. Such a row may not also carry a REINSTATED
# or DECLARED_ADDITIONS entry or a later-generation record.
COMBINED_READDITIONS = {
    184699: ('before_d16m_v1', {'milk': 'inherited'}, {'ghee': 'inherited', 'tree_nuts': 'inherited'}, 'coconut:direct;sulphites:derived',
             'datasets/_admin/progress/FOLLOWUPS_2026-10-08/BATCH_I5/OWNER_DECISIONS_BATCH_I5_ROUND10_2026-10-20.json I5-R10-1 (decision 4(a); TODO B11), '
             'BATCH_I5/OWNER_DECISIONS_BATCH_I5_2026-10-15.json (prose classes / ghee -> milk); applied only after an independent review APPROVE'),
}


# Ledger completeness (BATCH K D-19). The per-class check in validate_release_tiers trusts that every later tier change on a row of the 401
# recorded the value it replaced; an unrecorded change (a re-addition on a row that lost >=2 classes, say) leaves no snapshot to compare with.
# The pin below closes that from the pinned build on: it fixes the 401-row tier state of release v0.14.0 (data v20, master 6f1a017e) as a digest
# and the allergen_tier history generations that existed then, in build order (migrate_schema.py). validate_tier_ledger() rebuilds the state at
# the pin from the release itself -- for each row the earliest post-pin snapshot (the value the first later change replaced) when there is one,
# else the current tiers -- and refuses if its digest differs, or if an allergen_tier generation is neither pinned nor registered in
# TIER_LEDGER_LATER. So a tier change without a field_history record fails, whatever the number of classes involved. History before the pin is
# not re-proved (no after-values are recorded); the per-class and strict-removal checks above cover it as before.
TIER_HISTORY_ORDER = (GENERATION, 'before_diet_repair_v1', 'before_d13_round2_v1', 'before_d16a_v1', 'before_d16b_v1', 'before_d17_v1',
                      'before_d16c_v1', 'before_d16d_v1', 'before_d16e_v1', 'before_d16f_v1', 'before_d16g_v1', 'before_d16h_v1', 'before_d16i_v1',
                      'before_d16j_v1', 'before_d16k_v1', 'before_d16l_v1', 'before_d16m_v1', 'before_d16n_v1')
TIER_LEDGER_PIN = {'rows': 401, 'sha256': '5c7544df25ac06873606bb6fbc1ab87abb5fadda88482076b448b3250f69acf5',
                   'pinned_on': 'release v0.14.0 (data v20, master 6f1a017e), BATCH K D-19'}
# Generations a later build adds to allergen_tier history, in build order. A build that changes a tier on a row of the 401 records the replaced
# value under its own generation and appends that generation here; nothing else needs to change.
TIER_LEDGER_LATER = ('before_d16o_v1',)          # batch K (data v21, D16O): the K-R5-7 declared additions record their prior tiers here
_GEN_RANK = {g: i for i, g in enumerate(TIER_HISTORY_ORDER + TIER_LEDGER_LATER)}


def tier_state_digest(state):
    """sha256 over the sorted `recipe_id<TAB>class:tier;...` lines (classes sorted) of {recipe_id: tier string}."""
    import hashlib
    lines = [f'{int(rid)}\t' + ';'.join(f'{k}:{v}' for k, v in sorted(parse_tiers(state[rid]).items())) for rid in sorted(state)]
    return hashlib.sha256(('\n'.join(lines) + '\n').encode('utf-8')).hexdigest()


def validate_tier_ledger(root, pin=None, later=None):
    pin = TIER_LEDGER_PIN if pin is None else pin
    later = TIER_LEDGER_LATER if later is None else tuple(later)
    try:
        wide = pd.read_parquet(root / 'data/corpus/recipes_structured.parquet', columns=['recipe_id', 'allergen_tier']).set_index('recipe_id')
        hist = pd.read_parquet(root / 'data/provenance/field_history.parquet', filters=[('field', '==', 'allergen_tier')])
        recon = hist[hist.generation.eq(GENERATION)]
        ids = set(recon.recipe_id)
        if len(recon) != pin['rows'] or len(ids) != pin['rows'] or not ids <= set(wide.index):
            return ['allergen tier ledger: the reconciliation rows do not match the pin']
        if set(later) & set(TIER_HISTORY_ORDER) or len(set(later)) != len(later):
            return ['allergen tier ledger: a later generation repeats a pinned one']
        unknown = set(hist.generation) - set(TIER_HISTORY_ORDER) - set(later)
        if unknown:
            return [f'allergen tier ledger: unregistered allergen_tier history generation(s) {sorted(unknown)}']
        post = hist[hist.generation.isin(later) & hist.recipe_id.isin(ids)]
        if post.duplicated(['recipe_id', 'generation']).any():
            return ['allergen tier ledger: a later generation records a row twice']
        rank = {g: i for i, g in enumerate(later)}
        first = {}
        for rid, gen, value in sorted(zip(post.recipe_id, post.generation, post.value_str), key=lambda x: (x[0], rank[x[1]])):
            first.setdefault(rid, value)
        state = {rid: first.get(rid, wide.loc[rid, 'allergen_tier']) for rid in ids}
        if tier_state_digest(state) != pin['sha256']:
            return ['allergen tier ledger: a tier on the 401 reconciliation rows changed without a field_history record of the value it replaced']
        return []
    except (OSError, KeyError, ValueError, TypeError) as exc:
        return [f'cannot validate the allergen tier ledger: {exc}']


def parse_tiers(value):
    if value is None or pd.isna(value) or value == '':
        return {}
    out = {}
    for part in value.split(';'):
        token, separator, tier = part.partition(':')
        if not separator or token not in TOKENS or tier not in {'direct', 'derived', 'blend', 'inherited'} or token in out:
            raise ValueError('invalid or duplicate allergen tier')
        out[token] = tier
    return out


def validate_row(labels, tiers):
    expected = set(str(labels).split(';')) - {'unknown', 'none_detected', ''}
    if not expected.issubset(TOKENS):
        raise ValueError('invalid allergen label')
    if set(parse_tiers(tiers)) != expected:
        raise ValueError('current tier classes disagree with current labels')


def validate_release_tiers(root):
    try:
        wide = pd.read_parquet(root / 'data/corpus/recipes_structured.parquet',
                               columns=['recipe_id', 'Allergens_v2', 'allergen_tier']).set_index('recipe_id')
        narrow = pd.read_parquet(root / 'data/corpus/recipes.parquet',
                                 columns=['recipe_id', 'allergen_tier']).set_index('recipe_id')
        if not wide.index.is_unique or not narrow.index.is_unique or set(wide.index) != set(narrow.index):
            return ['tier surfaces have missing or duplicate recipe keys']
        if not wide.allergen_tier.fillna('').sort_index().equals(narrow.allergen_tier.fillna('').sort_index()):
            return ['current tiers disagree across recipe surfaces']
        for labels, tiers in wide[['Allergens_v2', 'allergen_tier']].itertuples(index=False, name=None):
            validate_row(labels, tiers)
        history = pd.read_parquet(root / 'data/provenance/field_history.parquet',
                                  filters=[('generation', '==', GENERATION)])
        if len(history) != 401 or history.recipe_id.duplicated().any() or not history.field.eq('allergen_tier').all():
            return ['401 unique prior tier values missing from correction history']
        later = pd.read_parquet(root / 'data/provenance/field_history.parquet',
                                filters=[('generation', 'in', list(LATER_GENERATIONS))])
        if later.recipe_id.duplicated().any() or not later.field.eq('allergen_tier').all() or not set(later.recipe_id) <= set(wide.index):
            return ['later tier history is duplicated, off-field or names an unknown recipe']
        later_value = dict(zip(later.recipe_id, later.value_str))
        reinstated_history = pd.read_parquet(root / 'data/provenance/field_history.parquet',
                                             filters=[('generation', 'in', sorted({g for g, _ in REINSTATED.values()}) or [''])])
        if not set(rid for rid, _ in REINSTATED) <= set(history.recipe_id):
            return ['a declared re-addition names a row outside the reconciliation history']
        addition_history = pd.read_parquet(root / 'data/provenance/field_history.parquet',
                                           filters=[('generation', 'in', sorted({g for g, _, _ in DECLARED_ADDITIONS.values()}) or [''])])
        if not set(rid for rid, _ in DECLARED_ADDITIONS) <= set(history.recipe_id):
            return ['a declared addition names a row outside the reconciliation history']
        combined_history = pd.read_parquet(root / 'data/provenance/field_history.parquet',
                                           filters=[('generation', 'in', sorted({v[0] for v in COMBINED_READDITIONS.values()}) or [''])])
        if not set(COMBINED_READDITIONS) <= set(history.recipe_id):
            return ['a combined re-addition names a row outside the reconciliation history']
        # Per-class removal check (OPEN_ITEMS 60; BATCH_E review_contract N1). Every tier value recorded for the row after the reconciliation,
        # under any generation, is a post-reconciliation snapshot, and so is the current value. A class of the reconciliation prior that is
        # absent from any snapshot was removed (by the reconciliation, whose output is one of the snapshots, or later). If such a class is in
        # the current tiers it was re-added, and only a declared re-addition (REINSTATED, or the re-added part of COMBINED_READDITIONS) admits
        # it. This holds whatever the number of classes removed; the strict-subset check below detects a re-addition only when every removed
        # class came back. Like the rest of the contract it relies on each later tier change recording the value it replaced;
        # validate_tier_ledger() enforces that from the v0.14.0 pin on (BATCH K D-19).
        snapshots = pd.read_parquet(root / 'data/provenance/field_history.parquet',
                                    filters=[('field', '==', 'allergen_tier'), ('generation', '!=', GENERATION)])
        snapshots = snapshots[snapshots.recipe_id.isin(set(history.recipe_id))]
        seen = {}
        for rid, value in zip(snapshots.recipe_id, snapshots.value_str):
            seen.setdefault(rid, []).append(parse_tiers(value))
        for row in history.itertuples(index=False):
            old = parse_tiers(row.value_str)
            current = parse_tiers(wide.loc[row.recipe_id, 'allergen_tier'])
            removed = {cls for cls in old if any(cls not in s for s in seen.get(row.recipe_id, []) + [current])}
            combo = COMBINED_READDITIONS.get(row.recipe_id)
            declared = {cls for rid, cls in REINSTATED if rid == row.recipe_id} | (set(combo[1]) if combo else set())
            if (removed & set(current)) - declared:
                return ['a class removed by the reconciliation is back without a declared re-addition']
        for row in history.itertuples(index=False):
            old = parse_tiers(row.value_str)
            # A later transaction replaced this row's tiers: the strict removal must have held at the value it replaced.
            if row.recipe_id in later_value:
                # The later record must be non-empty and name exactly the classes the row carries now: only literals may have moved.
                replaced = parse_tiers(later_value[row.recipe_id])
                if not replaced or set(replaced) != set(parse_tiers(wide.loc[row.recipe_id, 'allergen_tier'])):
                    return ['later tier history is empty or its classes differ from the current tier']
                now = replaced
            else:
                now = parse_tiers(wide.loc[row.recipe_id, 'allergen_tier'])
            back = {cls: gen for (rid, cls), (gen, _) in REINSTATED.items() if rid == row.recipe_id}
            added = {cls: (gen, literal) for (rid, cls), (gen, literal, _) in DECLARED_ADDITIONS.items() if rid == row.recipe_id}
            combo = COMBINED_READDITIONS.get(row.recipe_id)
            if combo:
                gen, readded, first, remaining, _ = combo
                if back or added or row.recipe_id in later_value:
                    return ['a combined re-addition is combined with another tier exemption']
                prior = combined_history[(combined_history.recipe_id == row.recipe_id) & combined_history.field.eq('allergen_tier')
                                         & combined_history.generation.eq(gen)]
                rest = {k: v for k, v in now.items() if k not in readded and k not in first}
                if (any(old.get(cls) != lit or now.get(cls) != lit for cls, lit in readded.items())
                        or any(cls in old or now.get(cls) != lit for cls, lit in first.items())
                        or rest != parse_tiers(remaining) or len(prior) != 1 or parse_tiers(prior.value_str.iloc[0]) != rest):
                    return ['a combined re-addition is not in its declared form or its prior value is not recorded']
                now = rest
            if added:
                if back or row.recipe_id in later_value:
                    return ['a declared addition is combined with another tier exemption']
                if any(cls in old or now.get(cls) != literal for cls, (_, literal) in added.items()):
                    return ['a declared addition is not in its declared form or its prior value is not recorded']
                # Additions declared under more than one generation (batch K: 127968 milk in before_d16o_v1 after asafoetida in
                # before_d16m_v1) are peeled latest generation first: each generation's single prior record must equal the tiers left
                # after removing the classes it and every later generation added.
                gens = sorted({gen for gen, _ in added.values()}, key=lambda g: _GEN_RANK.get(g, -1), reverse=True)
                if any(g not in _GEN_RANK for g in gens):
                    return ['a declared addition names a generation outside the tier history order']
                rest = dict(now)
                for gen in gens:
                    rest = {k: v for k, v in rest.items() if added.get(k, (None,))[0] != gen}
                    prior = addition_history[(addition_history.recipe_id == row.recipe_id) & addition_history.field.eq('allergen_tier')
                                             & addition_history.generation.eq(gen)]
                    if len(prior) != 1 or parse_tiers(prior.value_str.iloc[0]) != rest:
                        return ['a declared addition is not in its declared form or its prior value is not recorded']
                now = rest
            if back:
                prior = reinstated_history[(reinstated_history.recipe_id == row.recipe_id) & reinstated_history.field.eq('allergen_tier')
                                           & reinstated_history.generation.isin(set(back.values()))]
                rest = {k: v for k, v in now.items() if k not in back}
                if (any(cls not in now or cls not in old or now[cls] != old[cls] for cls in back) or len(prior) != 1
                        or parse_tiers(prior.value_str.iloc[0]) != rest):
                    return ['a declared re-addition does not restore the removed tier or its prior value is not recorded']
                now = rest
            if not set(now) < set(old) or any(old[k] != v for k, v in now.items()):
                return ['correction history does not preserve a strict removal of stale tiers']
        return []
    except (OSError, KeyError, ValueError, TypeError) as exc:
        return [f'cannot validate allergen tiers: {exc}']
