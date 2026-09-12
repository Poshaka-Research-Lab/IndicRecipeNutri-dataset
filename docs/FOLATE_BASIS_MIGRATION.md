# Folate percentage correction — unreleased candidate

`DV_Folate` is now null, and `DV_Folate_basis` contains
`unavailable_total_folate_not_dfe` in both the wide corpus and the narrow derived
nutrition table. `Nut_Folate` and all other nutrient values are unchanged.

The historical calculation used total folate as its numerator and a 400 microgram
DFE reference as its denominator. Total folate does not provide the separate food
folate and folic-acid components needed for a general DFE calculation. NIH describes
the distinct contributions of those forms in its [folate fact sheet](https://ods.od.nih.gov/factsheets/Folate-HealthProfessional/).
No assumption that all folate is natural, or that all is folic acid, is made here.

The correction preserves 219,386 published prior values in
`data/provenance/field_history.parquet`, selected by:

```python
old = history[
    (history["field"] == "DV_Folate")
    & (history["generation"] == "pre_folate_basis_v1")
]
```

Join by `recipe_id`. These are historical unsupported percentages, not alternative
current estimates. The source ledger also retains the withheld master record;
release exclusions apply before that ledger is exported.

Upstream writers apply `folate_basis_v1`. Release builders reject populated values
or missing basis status under this policy. The release verifier checks both active
surfaces and history coverage. A later DFE implementation needs traceable source
components, a new derivation version and validation; it must not refill these
percentages from total folate alone.

The physical values in `Nut_Folate` remain estimated total-folate values with their
existing source limitations. This correction does not validate ingredient amounts,
food-composition matches or other percentages. Those audits remain separate.
