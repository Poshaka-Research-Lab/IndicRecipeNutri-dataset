# Validation Report: South Asian 5 Allergen Lexicon

Text agreement between the shipped allergen labels and the shipped ingredient lists,
for the four South Asian 5 classes that no regulator enumerates and that therefore
rest entirely on this project's own lexicon: `coconut`, `tamarind`, `fenugreek`,
`asafoetida`.

> **This is a consistency check, not an accuracy measurement.** It compares a label to
> a regex over the same corpus the label was derived from, so it shares that lexicon's
> blind spots by construction and cannot discover a food the lexicon never knew about.
> A high figure here is evidence that the published label and the published text agree —
> not evidence that either is right. Read it alongside `docs/ALLERGEN_AUDIT.md`.

## Protocol

* **Scope.** All **219,386** recipes in the published payload
  (`data/corpus/recipes_structured.parquet`), measured at build time — not a sample,
  and not a figure carried over from an earlier corpus generation.
* **Column scanned.** `IngredientsList`, the canonicalised list that ships. Earlier
  versions of this report scanned a raw `Ingredients` column that is **not** part of
  the release, so their figures were not reproducible from the published data.
* **Word boundaries.** Short terms are `\b`-anchored on both sides, so `hing` does not
  match `garnishing`. The long `asafoetida` spellings drop the LEFT boundary only,
  because quantities fuse to the word in scraped text (`pinchasafoetida`, `2asafetida`)
  and `\b` does not fire between a digit and a letter. The corpus is fully Roman
  (`ingredients_romanised`), which is what makes `\b` usable at all; it is not reliable
  against Indic script and must not be reused on one.
* **Precision (text-confirmable).** Of the recipes carrying the label, the share whose
  ingredient list names the allergen or a regional synonym.
* **Recall (text-confirmable).** Of the recipes naming it, the share that carry the label.
* **Status.** Derived, not asserted. **Any** false negative returns `REVIEW` with the
  count, whatever the rate — a missed allergen is not a rounding error against a
  percentage (CLAUDE.md §4.3). Absent that, `agrees` needs precision ≥ 70% and recall ≥ 99%.

## Corpus-wide agreement

| Allergen | Labelled | Named in text | TP | FP | FN | Precision | Recall | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| coconut | 36,824 | 35,524 | 35,524 | 1,300 | 0 | 96.47% | 100.00% | agrees |
| tamarind | 12,163 | 12,059 | 12,059 | 104 | 0 | 99.14% | 100.00% | agrees |
| fenugreek | 20,025 | 17,864 | 17,864 | 2,161 | 0 | 89.21% | 100.00% | agrees |
| asafoetida | 30,518 | 23,741 | 23,657 | 6,861 | 84 | 77.52% | 99.65% | REVIEW — 84 fail-open |

> **Read the recall column with care.** For `coconut`, `tamarind` and `fenugreek` it is
> close to a tautology: the labels were derived from a lexicon that is a superset of the
> regex, so a row naming the allergen is labelled almost by construction and 100.00% is
> the expected reading, not an achievement. It is **not** evidence that the corpus
> contains no unlabelled instances of those foods.
>
> `asafoetida` is the exception, and it is the one worth reading. Its arm carries a
> **misspelling family** the labelling lexicon does not, so its FN count is a genuine
> measurement rather than a definitional zero — and it is **non-zero**. Those rows are
> recipes that name asafoetida in a spelling the labeller missed, so they carry no
> asafoetida label. That is a **fail-open** direction, the one CLAUDE.md §4.3 says is
> never traded, and it is tracked in
> `_docs/audits/PROPOSE_asafoetida_spellings_2026-09-05.tsv`.

## Why asafoetida's precision is the outlier

**6,861** recipes carry the `asafoetida` label without naming it in the shipped
ingredient list. An earlier version of this report put that count at 1,321 and
attributed it to *"valid knowledge-graph (KG-sourced) labels"*. **There is no KG
allergen source in this payload** — `allergens_sa5_src` takes only `lexicon_v8` (72,941), `none` (146,445). The actual
explanation is compositional, and is the reason the class behaves differently from the
other three:

**Asafoetida is a component of blended masalas that do not name it.** Chaat masala,
sambar powder and pav bhaji masala all standardly contain hing. A recipe calling for
chaat masala contains asafoetida; its ingredient list does not say so. Labelling those
recipes is correct and is the fail-closed behaviour Codex CXC 80-2020 requires — but it
makes the label deliberately exceed the text, which is what depresses precision here.

Of those 6,861 rows, **6,529 (95.2%)** name such a blend:

| Blend named | Recipes |
|---|---:|
| chaat masala | 4,285 |
| chat masala | 931 |
| sev | 766 |
| sambar powder | 630 |
| pav bhaji | 560 |
| garam masala | 385 |

Leaving **332** rows (0.15% of the corpus) where the
label is not explained by either a spelling variant or a named blend. These are
recorded, not resolved. They are a **known open item**, and because the residual
direction is a label the text does not support — an over-warning, not a missed
allergen — it is the tolerable direction of the two.

## Notes

1. **Coconut vs tree nuts.** Coconut is a separate token; the generic `tree_nuts` class
   is cleared where coconut is the only nut present. This follows the project's own
   taxonomy boundary and not a regulator's — FSSAI's clause 5(14) does not enumerate
   coconut, and its `tree nuts` entry is illustrative (`e.g.`), so whether coconut falls
   inside it is open on the face of the text. See `docs/ALLERGEN_TAXONOMY.md`.
2. **Plant milks.** `coconut milk`, `almond milk` and `soy milk` do not trigger the
   dairy `milk` class while retaining their own allergen identity.
3. **Provenance.** The four classes here are lexicon-derived and carry no regulatory
   backing; they are an investigator-defined extension on South Asian prevalence
   grounds. Do not present them as a regulator's list.

---

Regenerate with `python scripts/validate_sa5.py`; `--check` fails if this file has
drifted from the payload.
