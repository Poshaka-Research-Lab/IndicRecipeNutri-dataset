#!/usr/bin/env python
"""Stage the occasion registry and dietary-rule layer from internal source S1.

Writes ONLY to
    <staging_root>/data/cultural_context/  (staging_root comes from the private source map)
the five artefacts frozen by the integration schema (path from the private source map):
    occasion_registry.parquet, dietary_rules.parquet, context_citations.parquet,
    context_tag_links.parquet, CONTEXT_MANIFEST.json

Read-only inputs
    S1  data/registry/occasions.csv   (sha256 pinned; STOP if changed)
    S1  data/rules/rules.yaml         (sha256 pinned; STOP if changed)
    destination 0.10.0 data/kg/kg_nodes.parquet (occasion::/context:: node ids only)
    destination scripts/release_config.py (parsed with ast, never imported) and
    data/provenance/withdrawn_ids.json (withdrawn-ID exclusion scan only)

Guarantees
    * Deterministic and idempotent: no wall-clock values, rows sorted by primary key,
      fixed parquet writer options, JSON with sorted keys. Re-running yields byte-identical
      files.
    * Rule predicates are imported as DATA. Nothing here evaluates a rule against a recipe.
    * Citations are never invented: every string placed in a citation field is asserted to
      be a verbatim substring of the upstream cell it came from. A cited work that cannot be
      pinned to a title, URL or identifier is kept and counted as `unresolved`.
    * Verbatim third-party quotations are removed from shipped source S1 text only through the
      reviewed span table below; an unreviewed quoted span stops the run (fail closed).

Usage:  python scripts/stage_cultural_context.py
Exit codes: 0 ok; 2 pinned input hash changed (STOP); 3 a self-check failed.
"""
from __future__ import annotations

import ast
import datetime as dt
import hashlib
import io
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

# ----------------------------------------------------------------------------- paths
# Machine-local paths are NOT in this file. They come from a private source-map JSON named by
# $INDICRECIPE_CONTEXT_SOURCE_MAP, which is kept outside the release. The shipped provenance
# names the sources only as "internal source S1" / "internal source S2", with commit and hashes.
import os as _os


def _source_map() -> dict:
    p = _os.environ.get("INDICRECIPE_CONTEXT_SOURCE_MAP")
    if not p:
        raise SystemExit("set INDICRECIPE_CONTEXT_SOURCE_MAP to the private source-map JSON "
                         "(it is not part of the release); nothing was read or written")
    return json.loads(Path(p).read_text(encoding="utf-8"))


_MAP = _source_map()
SCHEMA_JSON = Path(_MAP["schema_json"])
S1_ROOT = Path(_MAP["sources"]["S1"]["root"])
DEST = Path(_MAP["destination"])
STAGING_ROOT = Path(_MAP["staging_root"])
OUT = STAGING_ROOT / "data" / "cultural_context"

OCC_REL = "data/registry/occasions.csv"
RULES_REL = "data/rules/rules.yaml"
SCRIPT_ID = "scripts/stage_cultural_context.py"  # same path in the integration workspace and in the release
SCHEMA_VERSION = "1.1.0"
TAG_VOCAB = "s1_rules_v0.2.0"

# ----------------------------------------------------------------------------- pinned
PIN = {
    OCC_REL: dict(sha256="4da2145b711618e40775ee7a4c5b0cfcde7434f11cc5845745f687547f641d68",
                  commit="5d8d7808d0252ecc23e66255d2616d74e1d5d3b2",
                  blob="e0f408d556119205e26e5d9a851f18a837e30619"),
    RULES_REL: dict(sha256="b1ed03b0a4fcda4aa2d05d3b164b7e988e68c3a5c94ab00a3b8be73076952c9f",
                    commit="uncommitted:b1ed03b0a4fcda4aa2d05d3b164b7e988e68c3a5c94ab00a3b8be73076952c9f",
                    blob=None),
}

# User-confirmed tier outcome (DATASET_INTEGRATION_SCOPE addendum 3, D2).
EXPECTED_TIERS = {"sourced": 6, "descriptive": 11, "unsourced": 7}
EXPECTED_SOURCED = {"halal", "halal_feast", "kosher_feast", "christian_abstinence",
                    "khalsa_rehat", "bahai_alcohol_prohibition"}

# ============================================================================ helpers
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class Stop(SystemExit):
    pass


def read_pinned(rel: str) -> bytes:
    """Hash immediately before use; STOP (exit 2) on any change."""
    b = (S1_ROOT / rel).read_bytes()
    got = sha256_bytes(b)
    if got != PIN[rel]["sha256"]:
        print(f"STOP: {rel} sha256 {got} != pinned {PIN[rel]['sha256']}", file=sys.stderr)
        raise Stop(2)
    return b


def fail(msg: str):
    print(f"SELF-CHECK FAILED: {msg}", file=sys.stderr)
    raise SystemExit(3)


def check(cond: bool, msg: str):
    if not cond:
        fail(msg)


def d(s: str | None):
    return None if s in (None, "") else dt.date.fromisoformat(str(s))


# Quoted-span detection. Single quotes need word-boundary guards so transliteration
# apostrophes (Bahá'í, 'Azamat) are not read as quotation marks.
_Q = [re.compile(r'"([^"]+)"'), re.compile(r"“([^”]+)”"),
      re.compile(r"(?<!\w)'([^']+?)'(?!\w)"), re.compile(r"(?<!\w)‘([^‘’]+?)’(?!\w)")]
MIN_QUOTE = 20


def quoted_spans(text: str) -> list[str]:
    """Quoted spans whose inner text is >= 20 chars, in order, each including its marks."""
    out = []
    for q in _Q:
        for m in q.finditer(text or ""):
            if len(m.group(1)) >= MIN_QUOTE:
                out.append(m.group(0))
    return out


PCT = re.compile(r"\d+(\.\d+)?\s?%")
URL = re.compile(r"https?://[^\s\"“”<>]+")


def clean_url(u: str) -> str:
    while u and u[-1] in ".,;:'’":
        u = u[:-1]
    while u.endswith(")") and u.count("(") < u.count(")"):
        u = u[:-1]
    return u


# ============================================================================ reviewed
# Every quoted span (>= 20 chars) found in a SHIPPED source S1 text field, with a decision.
# REMOVE = verbatim text of a third party (or of unidentified origin) -> replaced by
# QUOTE_MARK. KEEP = not a third-party quotation (source S1 cross-referencing its own field,
# or a transliteration apostrophe). A span missing from this table stops the run.
QUOTE_MARK = "[quotation removed]"
REVIEWED_SPANS = {
    # registry
    ("registry_note", "hornbill_festival_nagaland", "'festival of festivals'"):
        ("REMOVE", "quoted epithet; origin not identified in the row"),
    ("registry_note", "meitei_prenatal", "'becomes a perfect human being'"):
        ("REMOVE", "quoted phrase; origin not identified in the row (likely the cited paper)"),
    ("date_rule_text", "bahai_declaration_of_the_b_b", "'Azamat, the fourth month of the Badi'"):
        ("KEEP", "not a quotation: transliteration apostrophes in 'Azamat and Badi'"),
    ("date_rule_text", "holy_week_goan_observance_latin_rite_catholic",
     "'Palm Sunday of the Passion of the Lord'"):
        ("REMOVE", "verbatim liturgical title from the Universal Norms (third-party text)"),
    # rules
    ("rule_note", "halal", '"according to the different Islamic Schools of Thought"'):
        ("REMOVE", "verbatim Codex CXG 24-1997 text"),
    ("variation_not_enumerable_reason", "halal",
     "'according to the different Islamic Schools of Thought'"):
        ("REMOVE", "verbatim Codex CXG 24-1997 text"),
    ("rule_note", "bahai_alcohol_prohibition",
     '"Alcoholic and intoxicating drinks are prohibited except when medically prescribed and necessary"'):
        ("REMOVE", "verbatim wording of the external audit sheet"),
    ("time_of_day_absent_reason", "christian_abstinence", "'To sundown on Holy Thursday'"):
        ("KEEP", "source S1 quoting its own registry date_rule for Lent, not third-party text"),
    ("rule_note", "mourning_restriction", "'vegetarian AND no alcohol'"):
        ("KEEP", "source S1 quoting its own registry corpus_filter, not third-party text"),
}
# Explicit, reviewed note edit for the Pew survey percentages (addendum 2: percentages removed).
NOTE_EDITS = {
    "sattvic_vegetarian": (
        "Pew (2021) finds 22% of highly-observant Hindus avoid root vegetables against 17% "
        "otherwise, so root exclusion",
        "[survey figures removed; see the prevalence_reference citation] Root exclusion"),
}
SCRUBBED_FIELDS_REG = ["registry_note", "date_rule_text", "trigger", "states_observed",
                       "season_hint", "native_name", "saka_date_2026", "sect", "name"]
SCRUBBED_FIELDS_RULE = ["rule_note", "corpus_filter_text", "time_of_day_text",
                        "time_of_day_absent_reason", "variation_not_enumerable_reason"]

# ============================================================================ citations
# Registry base clauses (the text before the first `A<n> <date>` annotation), curated.
# Each string field must be a verbatim substring of the clause (asserted). A citation with
# only a publisher/site is kept and counted `unresolved`; a genre phrase is kind
# descriptive_genre whose `title` holds the upstream's own genre wording (not a work title).
def C(kind, title=None, publisher=None, locator=None, identifier=None, url=None,
      access=None, only_if_name=None, external=None):
    # `external` = {"fields": [...], "evidence": str, "verified_on": date}: fields filled from a
    # user-authorised web verification, exempt from the verbatim-substring check and listed in
    # the manifest. Every other field must still be verbatim in the source row.
    return dict(kind=kind, title=title, publisher=publisher, locator=locator,
                identifier=identifier, url=url, access=access, only_if_name=only_if_name,
                external=external)


R0829 = "2026-08-29"
BASE_CITATIONS = {
    "Cross-referenced state-wise festival lists retrieved 2026-08-29: pw.live 'Festivals of India, State and Season Wise'; studyiq.com 'List of Indian Festivals'; cheggindia.com 'List of Festivals in India'. General-knowledge sources, NOT gazette notifications. `n_sources` gives how many of the three list the festival for that state; 1 means uncorroborated. Ministry of Tourism (utsav.gov.in) corroborates Sarhul and Hornbill.": [
        C("web_page", "Festivals of India, State and Season Wise", "pw.live", access=R0829),
        C("web_page", "List of Indian Festivals", "studyiq.com", access=R0829),
        C("web_page", "List of Festivals in India", "cheggindia.com", access=R0829),
        C("web_page", None, "Ministry of Tourism", locator="utsav.gov.in", access=R0829,
          only_if_name=r"(?i)sarhul|hornbill"),
    ],
    "GoI DoPT O.M. F.No.12/2/2023-JCA dated 2025-07-03, 'Holidays to be observed in Central Government Offices during the year 2026'": [
        C("official_document", "Holidays to be observed in Central Government Offices during the year 2026",
          "GoI DoPT", identifier="O.M. F.No.12/2/2023-JCA"),
    ],
    "Vaishnava sampradayas and Indian sect enumeration: hinduscriptures.in, indianetzone.com, and general reference. Retrieved 2026-08-29. SINGLE-SOURCE for many rows -- vocabulary, not evidence.": [
        C("web_page", None, "hinduscriptures.in", access=R0829),
        C("web_page", None, "indianetzone.com", access=R0829),
        C("descriptive_genre", "general reference", access=R0829),
    ],
    "List of Indian state days, Wikipedia; retrieved 2026-08-29.": [
        C("web_page", "List of Indian state days", "Wikipedia", access=R0829)],
    "Household puja service enumeration; retrieved 2026-08-29.": [
        C("descriptive_genre", "Household puja service enumeration", access=R0829)],
    "Nationally observed commemorative days. **Dates are commonly cited and NOT verified against a gazette notification.** Retrieved 2026-08-29.": [
        C("descriptive_genre", "Nationally observed commemorative days", access=R0829)],
    "PRIMARY SOURCE. bahai.org/action/devotional-life/calendar — the Bahá'í International Community's own calendar, incl. 183 B.E. holy-day dates. Retrieved 2026-08-29.": [
        C("web_page", None, "Bahá'í International Community",
          locator="bahai.org/action/devotional-life/calendar", access=R0829)],
    "Shodasha Samskara enumeration; count varies 12-18 in the Grhya Sutras, settles at 16 in later tradition. Retrieved 2026-08-29.": [
        C("descriptive_genre", "Shodasha Samskara enumeration", access=R0829)],
    "Library of Congress Country Studies, 'Religions of India -- Life-Cycle Rituals' (public-domain text), https://photius.com/religion/india_life-cycle_rituals.html": [
        C("book_or_article", "Religions of India -- Life-Cycle Rituals", "Library of Congress Country Studies",
          url="https://photius.com/religion/india_life-cycle_rituals.html")],
    "General reference for cross-religion life-stage parity. Retrieved 2026-08-29.": [
        C("descriptive_genre", "General reference for cross-religion life-stage parity", access=R0829)],
    "Vaishnava (Gaudiya/ISKCON) calendar 2026 — Ekadashi, Chaturmas, Gaurabda era: iskcongurugram.com/vaishnava-calendar. Retrieved 2026-08-29.": [
        C("web_page", "Vaishnava (Gaudiya/ISKCON) calendar 2026", "iskcongurugram.com",
          locator="iskcongurugram.com/vaishnava-calendar", access=R0829)],
    "District Administration Leh (leh.nic.in) and Ladakh Tourism (tourism.ladakh.gov.in), both Government of India sources; retrieved 2026-08-29.": [
        C("web_page", None, "District Administration Leh", locator="leh.nic.in", access=R0829),
        C("web_page", None, "Ladakh Tourism", locator="tourism.ladakh.gov.in", access=R0829)],
    "Annaprashana regional names and practice: Wikipedia (mukhebhat, chorunu, bhat khulai); smartpuja.com; goldenmemoriesindia.com; ourparampara.com. Retrieved 2026-08-29.": [
        C("web_page", None, "Wikipedia", access=R0829),
        C("web_page", None, "smartpuja.com", access=R0829),
        C("web_page", None, "goldenmemoriesindia.com", access=R0829),
        C("web_page", None, "ourparampara.com", access=R0829)],
    "List of Sikh festivals, Wikipedia and SikhiWiki; retrieved 2026-08-29.": [
        C("web_page", "List of Sikh festivals", "Wikipedia", access=R0829),
        C("web_page", None, "SikhiWiki", access=R0829)],
    "Indian Christian fasting traditions by rite (Latin, Syro-Malabar, Malankara Orthodox, Goan, North-East). Retrieved 2026-08-29.": [
        C("descriptive_genre", "Indian Christian fasting traditions by rite", access=R0829)],
    "PEER-REVIEWED. Thangjam Chinky Devi, 'Rites and Rituals of the Meitei from Birth to Marriage', IJIRAS 5(1), Jan 2018; 'Beliefs and Practices of Pre- and Post-Natal Rituals of the Meiteis in Manipur', IJAR, May 2025; Ngangom Meeta Devi & H. B. Sharma, 'The Life Cycle Rituals of the Meitei Hindu', Int. J. of Interdisciplinary Cultural Studies 20(1), 2025.": [
        C("book_or_article", "Rites and Rituals of the Meitei from Birth to Marriage", "IJIRAS", locator="5(1), Jan 2018"),
        C("book_or_article", "Beliefs and Practices of Pre- and Post-Natal Rituals of the Meiteis in Manipur", "IJAR", locator="May 2025"),
        C("book_or_article", "The Life Cycle Rituals of the Meitei Hindu", "Int. J. of Interdisciplinary Cultural Studies", locator="20(1), 2025")],
    "GKToday, 'Important Fairs & Festivals of Indian States and Union Territories'; webindia123 territory pages. Retrieved 2026-08-29.": [
        C("web_page", "Important Fairs & Festivals of Indian States and Union Territories", "GKToday", access=R0829),
        C("web_page", None, "webindia123", access=R0829)],
    "Indian pre-wedding function guides; retrieved 2026-08-29.": [
        C("descriptive_genre", "Indian pre-wedding function guides", access=R0829)],
    "Santal life-cycle rituals: philosophy.institute/tribal-philosophy; encyclopedia.com; Nayan Jyoti Das (2013), thecho.in; indianetzone. Retrieved 2026-08-29.": [
        C("web_page", None, "philosophy.institute", locator="philosophy.institute/tribal-philosophy", access=R0829),
        C("web_page", None, "encyclopedia.com", access=R0829),
        C("web_page", None, "thecho.in", access=R0829),
        C("web_page", None, "indianetzone", access=R0829)],
    "Shia Islam in India; Muharram/Ashura observance; Dawoodi Bohra practice; Dhamma Chakra Pravartan Din. Wikipedia, wincalendar, News18. Retrieved 2026-08-29.": [
        C("web_page", None, "Wikipedia", access=R0829),
        C("web_page", None, "wincalendar", access=R0829),
        C("web_page", None, "News18", access=R0829)],
    "Jewish life-cycle rites in the Indian context; Bene Israel practice. Retrieved 2026-08-29.": [
        C("descriptive_genre", "Jewish life-cycle rites in the Indian context", access=R0829)],
    "Puducherry festivals: tourmyindia.com state pages. Retrieved 2026-08-29.": [
        C("web_page", None, "tourmyindia.com", access=R0829)],
    "IndicRecipeNutri KG for_occasion edges, measured 2026-08-29": [
        C("corpus_self_reference", "IndicRecipeNutri KG for_occasion edges")],
    "Lakshadweep festivals: irisholidays.com. Retrieved 2026-08-29.": [
        C("web_page", None, "irisholidays.com", access=R0829)],
    "Jain festivals (Paryushana / Das Lakshana / Samvatsari), Wikipedia and ReadTheSpirit religious-holidays desk; retrieved 2026-08-29.": [
        C("web_page", None, "Wikipedia", access=R0829),
        C("web_page", None, "ReadTheSpirit", access=R0829)],
    "Shaiva schools incl. Kashmir Shaivism: Wikipedia. Retrieved 2026-08-29.": [
        C("web_page", None, "Wikipedia", access=R0829)],
    "Meitei/Sanamahi and Zeliangrong observances of Manipur. Retrieved 2026-08-29.": [
        C("descriptive_genre", "Meitei/Sanamahi and Zeliangrong observances of Manipur", access=R0829)],
    "Zoroastrian calendars (Fasli/Bastani, Shenshai/Shahenshahi, Kadmi/Qadimi): heritageinstitute.com, zoroastriancalendar.com, parsikhabar.net. Retrieved 2026-08-29.": [
        C("web_page", None, "heritageinstitute.com", access=R0829),
        C("web_page", None, "zoroastriancalendar.com", access=R0829),
        C("web_page", None, "parsikhabar.net", access=R0829)],
    "Hindu mourning and ancestral practice: sutak/ashaucha, dietary restriction, 13-day terahvi, pind daan composition. Retrieved 2026-08-29.": [
        C("descriptive_genre", "Hindu mourning and ancestral practice", access=R0829)],
    "Bahá'í Naw-Rúz and Ridván: bahaipedia.org. Retrieved 2026-08-29.": [
        C("web_page", None, "bahaipedia.org", access=R0829)],
    "Sarhul Mahotsav -- Ministry of Tourism, Government of India, utsav.gov.in; with Jharkhand 2026 observance detail. Retrieved 2026-08-29.": [
        C("web_page", None, "Ministry of Tourism, Government of India", locator="utsav.gov.in", access=R0829)],
    "Bene Israel Malida ceremony: jewishideas.org; yahelisrael.com; Indian Express on Ori Z. Soltes, 'Growing up Jewish in India' (Niyogi Books). Retrieved 2026-08-29.": [
        C("web_page", None, "jewishideas.org", access=R0829),
        C("web_page", None, "yahelisrael.com", access=R0829),
        C("web_page", None, "Indian Express", access=R0829),
        C("book_or_article", "Growing up Jewish in India", "Niyogi Books")],
    "Godh bharai regional food rituals -- NDTV Food, 'Interesting Godh Bharai (Baby Shower) Food Rituals From Across the Country'; retrieved 2026-08-29.": [
        C("web_page", "Interesting Godh Bharai (Baby Shower) Food Rituals From Across the Country", "NDTV Food", access=R0829)],
    "Griha pravesh sattvic menu rules; retrieved 2026-08-29.": [
        C("descriptive_genre", "Griha pravesh sattvic menu rules", access=R0829)],
    "Ritu Kala Samskaram, Wikipedia; retrieved 2026-08-29.": [
        C("web_page", "Ritu Kala Samskaram", "Wikipedia", access=R0829)],
    "BaHammam AS, Almeneessier AS (2020), Frontiers in Nutrition 7:28, DOI 10.3389/fnut.2020.00028 -- 'abstain from food as well as drinks from dawn to sunset for the whole month (29-30 days)'; 'Ramadan is the ninth month of Islamic (Hijri) year'. Claim checked against the full text 2026-09-01, not merely the DOI.": [
        C("book_or_article", None, "Frontiers in Nutrition", locator="7:28",
          identifier="10.3389/fnut.2020.00028", access="2026-09-01")],
}
IRN_SELF = "IndicRecipeNutri KG for_occasion edges"
ANNOT = re.compile(r"\s*\b(A\d{1,2}) (20\d\d-\d\d-\d\d)")

# Rule-side citations: (role, spec, field-of-origin). Same verbatim discipline.
RULE_CITATIONS = {
    "fasting": [("rule_source", C("descriptive_genre", "Operational reading"), "source"),
                ("rule_source", C("descriptive_genre", "Concurring secondary sources"), "source")],
    "ramadan_fasting": [
        ("rule_source", C("descriptive_genre", "Operational reading"), "source"),
        ("time_of_day_source", C("book_or_article", None, "Frontiers in Nutrition", locator="7:28",
                                 identifier="10.3389/fnut.2020.00028", access="2026-09-01"), "time_of_day_source")],
    "vrat_fasting": [("rule_source", C("descriptive_genre", "Operational reading"), "source")],
    "terminal_fast": [("rule_source", C("descriptive_genre", "Santhara / Sallekhana"), "source")],
    "halal": [
        ("rule_source", C("standard", 'General Guidelines for Use of the Term "Halal"', "Codex Alimentarius",
                          locator="§3.1.1", identifier="CXG 24-1997", access="2026-09-01"), "source"),
        ("rule_source", C("standard", "General Guidelines on Claims", "Codex",
                          identifier="CAC/GL 1-1979 (Rev. 1-1991)", access="2026-09-01"), "source"),
        ("certification_source", C("standard", None, "Codex", identifier="CAC/GL 1-1979 (Rev. 1-1991)"),
         "certification_source")],
    "halal_feast": [
        ("rule_source", C("standard", None, "Codex", identifier="CXG 24-1997"), "source"),
        ("rule_source", C("standard", "General Guidelines on Claims", "Codex",
                          identifier="CAC/GL 1-1979 (Rev. 1-1991)", access="2026-09-01"), "source"),
        ("certification_source", C("standard", None, "Codex", identifier="CAC/GL 1-1979 (Rev. 1-1991)"),
         "certification_source")],
    "kosher_feast": [
        ("rule_source", C("scripture", "Leviticus", locator="11:2-3"), "source"),
        ("rule_source", C("descriptive_genre", "Concurring secondary descriptions of kashrut structure"), "source"),
        ("rule_source", C("standard", "General Guidelines on Claims", "Codex",
                          identifier="CAC/GL 1-1979 (Rev. 1-1991)", access="2026-09-01"), "source"),
        ("certification_source", C("standard", None, "Codex", identifier="CAC/GL 1-1979 (Rev. 1-1991)"),
         "certification_source")],
    "jain_sattvic": [("rule_source", C("descriptive_genre", "Concurring sources"), "source")],
    "sattvic_vegetarian": [
        ("rule_source", C("descriptive_genre", "Sattvic dietary reading; concurring secondary sources"), "source"),
        # "Pew (2021)" is all the rule row itself says. Title/locator/URL verified online
        # 2026-09-23 on user instruction (pewresearch.org and JSTOR resrep63064 record).
        ("prevalence_reference", C(
            "book_or_article", "Religion in India: Tolerance and Segregation", "Pew",
            locator="ch. 10 “Religion and food” (29 June 2021)",
            url="https://www.pewresearch.org/religion/2021/06/29/religion-and-food",
            access="2026-09-23",
            external={"fields": ["title", "locator", "url", "access"],
                      "evidence": "https://www.pewresearch.org/religion/2021/06/29/religion-and-food ; "
                                  "https://www.jstor.org/stable/resrep63064.3 (ch. 10, pp. 185-192)",
                      "verified_on": "2026-09-23"}), "note")],
    "christian_abstinence": [
        ("rule_source", C("official_document", "Paenitemini", locator="III:1"), "source"),
        ("rule_source", C("official_document", "Code of Canon Law", locator="c. 1251"), "source")],
    "khalsa_rehat": [("rule_source", C("official_document", "Sikh Rehat Maryada", "SGPC"), "source")],
    "feast": [("rule_source", C("descriptive_genre", "A feast day imposes no exclusion of its own"), "source")],
    "langar_feast": [("rule_source", C("descriptive_genre",
                      "Langar is conventionally lacto-vegetarian so that anyone may eat together"), "source")],
    "post_fast_feast": [("rule_source", C("descriptive_genre", "Marks the end of a fast"), "source")],
    "fast_breaking": [("rule_source", C("descriptive_genre", "Marks the breaking of a fast"), "source")],
    "ritual_offering": [("rule_source", C("descriptive_genre",
                         "Concerns what is offered, not what the observer may eat"), "source")],
    "bahai_alcohol_prohibition": [("rule_source", C(
        "web_page", "A Chaste and Holy Life", "Bahá’í Reference Library", locator="section 3 (Alcohol)",
        url="https://www.bahai.org/library/authoritative-texts/compilations/chaste-holy-life/3",
        access="2026-09-04"), "source")],
}
STANDING_CITATIONS = {  # religion -> specs, verbatim against meta.standing_rules.<religion>.source
    "islam": [C("standard", 'General Guidelines for Use of the Term "Halal"', "Codex",
                locator="3.1.1", identifier="CXG 24-1997")],
    "sikh": [C("official_document", "Sikh Rehat Maryada", "SGPC",
               url="https://old.sgpc.net/CDN/Sikh_Rehat_Maryada_English.pdf"),
             C("book_or_article", "Encyclopaedia of Sikhism", "Punjabi University, Patiala",
               locator="entry PATIT", url="https://eos.learnpunjabi.org/PATIT.html", access="2026-09-04"),
             C("web_page", None, "Sikh Missionary Society U.K.",
               url="https://www.sikhmissionarysociety.org/sms/smssikhism/codeofconduct/", access="2026-09-04")],
    "bahai": [C("web_page", "A Chaste and Holy Life", "Bahá’í Reference Library", locator="section 3",
                url="https://www.bahai.org/library/authoritative-texts/compilations/chaste-holy-life/3",
                access="2026-09-04")],
}
ROLE_ORDER = ["registry_source", "rule_source", "certification_source", "time_of_day_source",
              "standing_rule_source", "prevalence_reference"]

# The rights review's Flag 2 as published (CSV lines) and the prefix list the schema review replayed.
RIGHTS_REVIEW_LINES = {
    "Household puja service enumeration": [195, 223, 380, 382, 384, 386, 391, 392, 393, 394, 395, 396, 398,
                                           400, 401, 402, 403, 405, 406, 416, 417],
    "Shodasha Samskara enumeration": [300, 302, 306, 311, 336, 345, 348, 349, 357, 361, 364, 371, 375, 377, 378],
    "General reference for cross-religion life-stage parity": [303, 310, 329, 330, 331, 332, 334, 355, 356,
                                                               359, 360, 374],
    "Indian pre-wedding function guides": [379, 381, 383, 385, 387, 388, 389, 390],
    "Jewish life-cycle rites in the Indian context": [289, 294, 314, 325, 340, 353, 368],
    "Indian Christian fasting traditions by rite": [122, 151, 172, 173, 215, 246],
    "Meitei/Sanamahi and Zeliangrong observances": [60, 96, 190, 197],
    "Hindu mourning and ancestral practice": [313, 322, 326],
    "Griha pravesh sattvic menu rules": [399],
    "IndicRecipeNutri KG for_occasion edges": [86, 248, 249, 250],
}


# ============================================================================ citation rows
def verbatim(spec: dict, text: str, where: str):
    ext = set((spec.get("external") or {}).get("fields", []))
    for k in ("title", "publisher", "locator", "identifier", "url"):
        v = spec.get(k)
        if k not in ext and v is not None and v not in text:
            fail(f"citation field {k}={v!r} is not a verbatim substring of {where}")
    if "access" not in ext and spec.get("access") and spec["access"] not in text:
        fail(f"access date {spec['access']} not stated in {where}")


def citation_status(kind, title, url, identifier, publisher) -> str:
    if kind in ("descriptive_genre", "corpus_self_reference", "none_recorded"):
        return kind
    if url or identifier or title:
        return "resolved"
    return "unresolved"  # only a publisher/site is named; the specific work is not identifiable


def registry_citations(row: dict, line: int, prov: dict):
    """Return citation dicts for one registry row, plus a per-row reduction log."""
    src = row["source"]
    parts = ANNOT.split(src)
    base = parts[0].strip()
    if base not in BASE_CITATIONS:
        fail(f"registry line {line}: base clause not in the reviewed table: {base[:80]!r}")
    cites, log = [], {"line": line, "base_clause_sha256": sha256_text(base), "annotations": []}
    for spec in BASE_CITATIONS[base]:
        verbatim(spec, base, f"registry line {line} base clause")
        if spec["only_if_name"] and not re.search(spec["only_if_name"], row["name"]):
            continue
        cites.append(dict(spec, origin="base"))
    # annotations: [marker, date, text, marker, date, text, ...]
    for i in range(1, len(parts), 3):
        marker, adate, seg = parts[i], parts[i + 1], parts[i + 2]
        urls = [clean_url(u) for u in URL.findall(seg)]
        log["annotations"].append({"marker": marker, "date": adate, "urls": len(urls),
                                   "quoted_spans_dropped": len(quoted_spans(seg))})
        for u in urls:
            check(u in seg, f"url not verbatim in line {line}")
            cites.append(dict(C("web_page", url=u, access=adate), origin=f"{marker} {adate}"))
    if IRN_SELF in src and not any(c["kind"] == "corpus_self_reference" for c in cites):
        cites.append(dict(C("corpus_self_reference", IRN_SELF), origin="annotation mention"))
    # de-duplicate on the identifying tuple, keep first
    seen, out = set(), []
    for c in cites:
        key = (c["kind"], c["title"], c["publisher"], c["locator"], c["identifier"], c["url"])
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out, log


def cite_row(subject_kind, key, subject_uid, role, seq, spec, prov, locator_line, search_recorded=None):
    uid = f"cite::{subject_kind}.{key}.{seq:02d}"
    return {
        "citation_uid": uid, "subject_uid": subject_uid, "citation_role": role, "citation_seq": seq,
        "citation_kind": spec["kind"], "title": spec["title"], "publisher": spec["publisher"],
        "locator": spec["locator"], "identifier": spec["identifier"], "url": spec["url"],
        "access_date": d(spec.get("access")), "search_recorded": d(search_recorded),
        "prov_source_repo": "internal source S1", "prov_source_path": prov["path"],
        "prov_source_sha256": prov["sha256"], "prov_source_commit": prov["commit"],
        "prov_source_locator": str(locator_line), "prov_import_script": SCRIPT_ID,
        "prov_schema_version": SCHEMA_VERSION,
        "_status": citation_status(spec["kind"], spec["title"], spec["url"], spec["identifier"],
                                   spec["publisher"]),
    }


# ============================================================================ scrubbing
def scrub(field: str, subject: str, text, log: list):
    """Apply the reviewed quotation decisions and the percentage guard to one text value."""
    if text is None:
        return None, False
    new = text
    for span in quoted_spans(text):
        dec = REVIEWED_SPANS.get((field, subject, span))
        if dec is None:
            fail(f"unreviewed quoted span in {field} of {subject}: {span[:60]!r}")
        if dec[0] == "REMOVE":
            new = new.replace(span, QUOTE_MARK)
            log.append({"field": field, "subject": subject, "action": "quotation_removed",
                        "span_sha256": sha256_text(span), "span_chars": len(span), "reason": dec[1]})
        else:
            log.append({"field": field, "subject": subject, "action": "quoted_span_kept",
                        "span_sha256": sha256_text(span), "span_chars": len(span), "reason": dec[1]})
    if PCT.search(new):
        fail(f"percentage left in {field} of {subject}")
    return new, new != text


# ============================================================================ build
def yaml_lines(text: str):
    lines = text.splitlines()
    rule_line, field_line, standing_line = {}, {}, {}
    cur, in_standing, cur_rel = None, False, None
    for i, ln in enumerate(lines, 1):
        m = re.match(r"^- name: (\S+)\s*$", ln)
        if m:
            cur = m.group(1)
            rule_line[cur] = i
            continue
        if cur:
            m = re.match(r"^  ([a-z_]+):", ln)
            if m:
                field_line.setdefault((cur, m.group(1)), i)
        if ln.startswith("  standing_rules:"):
            in_standing = True
            continue
        if in_standing:
            m = re.match(r"^    ([a-z_]+):", ln)
            if m:
                cur_rel = m.group(1)
            m = re.match(r"^      source:", ln)
            if m and cur_rel:
                standing_line[cur_rel] = i
            if ln.startswith("rules:"):
                in_standing = False
    return rule_line, field_line, standing_line


def parse_bool(v: str, nullable: bool, where: str):
    if v == "" and nullable:
        return None
    check(v in ("True", "False"), f"non-boolean {v!r} at {where}")
    return v == "True"


def build():
    schema = json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))

    # ---- pinned inputs: hash immediately before reading
    occ_bytes = read_pinned(OCC_REL)
    rules_bytes = read_pinned(RULES_REL)
    occ_prov = dict(path=OCC_REL, sha256=PIN[OCC_REL]["sha256"], commit=PIN[OCC_REL]["commit"],
                    blob=PIN[OCC_REL]["blob"])
    rules_prov = dict(path=RULES_REL, sha256=PIN[RULES_REL]["sha256"], commit=PIN[RULES_REL]["commit"],
                      blob=None)

    occ = pd.read_csv(io.StringIO(occ_bytes.decode("utf-8")), dtype=str, keep_default_na=False)
    check(occ.shape == (444, 34), f"occasions.csv shape {occ.shape}")
    rules_text = rules_bytes.decode("utf-8")
    ydoc = yaml.safe_load(rules_text)
    rules = ydoc["rules"]
    meta = ydoc["meta"]
    check(len(rules) == 24, "rules.yaml must hold 24 rules")
    rule_line, field_line, standing_line = yaml_lines(rules_text)
    rule_names = [r["name"] for r in rules]
    check(len(set(rule_names)) == 24, "rule names unique")

    transformations = []
    scrub_log: list = []

    # ------------------------------------------------------------------ occasion_registry
    reg_rows, cit_rows, reduction_log = [], [], []
    for idx, r in occ.iterrows():
        r = r.to_dict()
        line = idx + 2  # header = line 1, no embedded newlines (445 CRLF lines)
        oid = r["occasion_id"]
        check(re.fullmatch(r"[a-z0-9_]{1,96}", oid) is not None, f"occasion_id {oid!r}")
        where = f"occasions.csv:{line}"
        note, _ = scrub("registry_note", oid, r["note"] or None, scrub_log)
        date_rule, _ = scrub("date_rule_text", oid, r["date_rule"] or None, scrub_log)
        other = {}
        for f_out, f_in in [("trigger", "trigger"), ("states_observed", "states_observed"),
                            ("season_hint", "season_hint"), ("native_name", "native_name"),
                            ("saka_date_2026", "saka_date_2026"), ("sect", "sect"), ("name", "name")]:
            other[f_out], _ = scrub(f_out, oid, r[f_in] or None, scrub_log)
        cites, rlog = registry_citations(r, line, occ_prov)
        rlog["occasion_uid"] = f"occ::{oid}"
        rlog["source_text_sha256"] = sha256_text(r["source"])
        rlog["citations"] = len(cites)
        reduction_log.append(rlog)
        statuses = []
        for seq, spec in enumerate(cites, 1):
            row = cite_row("o", oid, f"occ::{oid}", "registry_source", seq, spec, occ_prov, line)
            cit_rows.append(row)
            statuses.append(row["_status"])
        locatable = any(s in ("resolved", "unresolved") for s in statuses)
        n_src = r["n_sources"]
        reg_rows.append({
            "occasion_uid": f"occ::{oid}", "source_occasion_id": oid, "name": other["name"],
            "native_name": other["native_name"], "kind": r["kind"], "category": r["category"],
            "religion": r["religion"], "scope": r["scope"], "calendar_system": r["calendar_system"] or None,
            "dietary_rule_uid": f"rule::{r['dietary_context']}" if r["dietary_context"] else None,
            "dietary_status": r["dietary_status"],
            **{b: parse_bool(r[b], False, where) for b in
               ["gazetted_2026", "restricted_2026", "national_holiday", "compulsory_outside_delhi",
                "optional_outside_delhi", "moon_sighting_dependent"]},
            "date_2026": d(r["date_2026"]), "saka_date_2026": other["saka_date_2026"],
            "weekday_2026": r["weekday_2026"] or None, "trigger": other["trigger"],
            "date_rule_text": date_rule, "states_observed": other["states_observed"],
            "season_hint": other["season_hint"],
            "n_sources": (int(float(n_src)) if n_src else None),
            "region_defining": parse_bool(r["region_defining"], True, where), "sect": other["sect"],
            "variant_of_uid": f"occ::{r['variant_of']}" if r["variant_of"] else None,
            "verification_status": r["verification_status"],
            "registry_evidence_tier": r["evidence_tier"], "evidence_level": r["evidence_level"],
            "source_locatable": locatable,
            "corpus_circular_source": "IndicRecipeNutri" in r["source"],
            "registry_note": note, "source_text_sha256": sha256_text(r["source"]),
            "source_reduced_to_citations": True, "label_status": "silver",
            "prov_source_repo": "internal source S1", "prov_source_path": OCC_REL,
            "prov_source_sha256": occ_prov["sha256"], "prov_source_commit": occ_prov["commit"],
            "prov_source_blob_id": occ_prov["blob"], "prov_source_locator": str(line),
            "prov_import_script": SCRIPT_ID, "prov_schema_version": SCHEMA_VERSION,
            "_line": line, "_n_sources_raw": n_src,
        })
        if n_src:
            check(float(n_src) == int(float(n_src)), f"n_sources {n_src!r} not integral at {where}")

    # ------------------------------------------------------------------ dietary_rules
    standing = meta.get("standing_rules") or {}
    standing_for: dict[str, list] = {}
    for rel, ent in standing.items():
        if ent and ent.get("rule"):
            standing_for.setdefault(ent["rule"], []).append(rel)
    rule_rows = []
    for r in rules:
        name = r["name"]
        src = r.get("source") or ""
        note_raw = r.get("note")
        note = note_raw
        edited = False
        if name in NOTE_EDITS:
            old, new = NOTE_EDITS[name]
            check(note is not None and old in note, f"reviewed note edit for {name} does not apply")
            note = note.replace(old, new)
            edited = True
            transformations.append({"id": "R-PCT", "table": "dietary_rules", "subject": f"rule::{name}",
                                    "field": "rule_note", "action": "survey_percentages_removed",
                                    "removed_sha256": sha256_text(old), "replacement": new})
        note, changed = scrub("rule_note", name, note, scrub_log)
        texts = {}
        for f_out, f_in in [("corpus_filter_text", "corpus_filter"), ("time_of_day_text", "time_of_day"),
                            ("time_of_day_absent_reason", "time_of_day_absent"),
                            ("variation_not_enumerable_reason", "variation_not_enumerable")]:
            texts[f_out], _ = scrub(f_out, name, r.get(f_in), scrub_log)
        # citations
        cites_specs = []
        if src.startswith("⟨unverified⟩") or not src.strip():
            tier = "unsourced"
            check(r.get("search_recorded") is not None, f"unsourced {name} lacks search_recorded")
            cites_specs.append(("rule_source", C("none_recorded"), "source", r.get("search_recorded")))
            check(name not in RULE_CITATIONS, f"{name} is unsourced but has curated citations")
        else:
            check(name in RULE_CITATIONS, f"no reviewed citation entry for {name}")
            for role, spec, origin in RULE_CITATIONS[name]:
                origin_text = r.get(origin) or ""
                verbatim(spec, origin_text, f"rules.yaml {name}.{origin}")
                cites_specs.append((role, spec, origin, None))
            locatable_kinds = {"standard", "scripture", "official_document"}
            rs = [s for role, s, _, _ in cites_specs if role == "rule_source"]
            tier = ("sourced" if any(s["kind"] in locatable_kinds or s["url"] or s["identifier"] for s in rs)
                    else "descriptive")
        for rel in standing_for.get(name, []):
            stext = standing[rel].get("source") or ""
            for spec in STANDING_CITATIONS[rel]:
                verbatim(spec, stext, f"rules.yaml meta.standing_rules.{rel}.source")
                cites_specs.append(("standing_rule_source", spec, f"standing:{rel}", None))
        cites_specs.sort(key=lambda t: ROLE_ORDER.index(t[0]))  # stable
        for seq, (role, spec, origin, srec) in enumerate(cites_specs, 1):
            if origin.startswith("standing:"):
                loc = standing_line[origin.split(":", 1)[1]]
            else:
                loc = field_line.get((name, origin), rule_line[name])
            cit_rows.append(cite_row("r", name, f"rule::{name}", role, seq, spec, rules_prov, loc, srec))
        sv = r.get("sect_variants")
        rule_rows.append({
            "rule_uid": f"rule::{name}", "source_rule_name": name, "rule_class": r["class"],
            "source_executable": bool(r["executable"]), "destination_executable": False,
            "certifies": bool(r["certifies"]), "verification": r["verification"], "evidence_tier": tier,
            "label_status": "silver", "excludes_tags": list(r.get("excludes") or []),
            "permits_tags": list(r["permits"]) if r.get("permits") is not None else None,
            "also_excludes_from_uids": ([f"rule::{x}" for x in r["also_excludes_from"]]
                                        if r.get("also_excludes_from") is not None else None),
            "standing_for_religions": sorted(standing_for[name]) if name in standing_for else None,
            **texts,
            "time_of_day_executable": (bool(r["time_of_day_executable"])
                                       if r.get("time_of_day_executable") is not None else None),
            "sect_variants_json": json.dumps(sv, ensure_ascii=False) if sv is not None else None,
            "search_recorded": d(r.get("search_recorded")),
            "rule_note": note, "rule_note_reduced": bool(edited or changed),
            "source_text_sha256": sha256_text(src),
            "note_text_sha256": sha256_text(note_raw) if note_raw is not None else None,
            "tag_vocabulary": TAG_VOCAB,
            "prov_source_repo": "internal source S1", "prov_source_path": RULES_REL,
            "prov_source_sha256": rules_prov["sha256"], "prov_source_commit": rules_prov["commit"],
            "prov_source_blob_id": None, "prov_source_locator": str(rule_line[name]),
            "prov_import_script": SCRIPT_ID, "prov_schema_version": SCHEMA_VERSION,
        })

    # ------------------------------------------------------------------ context_tag_links
    nodes_path = DEST / "data" / "kg" / "kg_nodes.parquet"
    nodes_sha = sha256_bytes(nodes_path.read_bytes())
    nodes = pq.read_table(nodes_path, columns=["node_id", "type"]).to_pandas()
    tag_nodes = nodes[nodes["type"].isin(["occasion", "context"])]
    check(all(n.startswith(("occasion::", "context::")) for n in tag_nodes["node_id"]), "node prefixes")
    occ_keys = {n.split("::", 1)[1]: n for n in tag_nodes.loc[tag_nodes.type == "occasion", "node_id"]}
    ctx_keys = {n.split("::", 1)[1]: n for n in tag_nodes.loc[tag_nodes.type == "context", "node_id"]}
    name_count = pd.Series([r["name"].lower() for r in reg_rows]).value_counts().to_dict()

    link_rows = []

    def add_link(subject, target, ltype, method, evidence):
        key = f"{subject}\n{target if target is not None else '<unmatched>'}\n{ltype}"
        link_rows.append({
            "link_uid": "link::" + sha256_text(key)[:16], "subject_uid": subject,
            "target_node_id": target, "link_type": ltype, "resolution_method": method,
            "link_evidence": evidence, "reviewed_by": None, "reviewed_on": None, "label_status": "silver",
            "prov_import_script": SCRIPT_ID, "prov_schema_version": SCHEMA_VERSION,
        })

    for r in reg_rows:
        cands = {}
        oid, nm = r["source_occasion_id"].lower(), r["name"].lower()
        if oid in occ_keys:
            cands.setdefault(occ_keys[oid], []).append("lower(source_occasion_id)")
        if nm in occ_keys:
            cands.setdefault(occ_keys[nm], []).append("lower(name)")
        subj = r["occasion_uid"]
        if not cands:
            add_link(subj, None, "unmatched", "unresolved", None)
        elif len(cands) == 1:
            (tgt, via), = cands.items()
            ev = f"exact_string: {' and '.join(via)} equals node key"
            if "lower(name)" in via and name_count[nm] > 1:
                ev += f"; name shared by {name_count[nm]} registry rows (name correspondence only)"
            add_link(subj, tgt, "exact", "exact_string", ev)
        else:
            for tgt, via in sorted(cands.items()):
                add_link(subj, tgt, "ambiguous", "unresolved",
                         f"candidate via {' and '.join(via)}; {len(cands)} candidates, none resolved")
    for rr in rule_rows:
        nm = rr["source_rule_name"].lower()
        subj = rr["rule_uid"]
        if nm in ctx_keys:
            add_link(subj, ctx_keys[nm], "exact", "exact_string",
                     "exact_string: lower(rule name) equals context node key; asserts name correspondence "
                     "only (corpus DietaryContext labels are silver/inferred)")
        else:
            add_link(subj, None, "unmatched", "unresolved", None)

    return (schema, occ, rules, meta, reg_rows, rule_rows, cit_rows, link_rows, scrub_log,
            reduction_log, transformations, nodes_sha, occ_keys, ctx_keys, rules_text)


# ============================================================================ arrow
ARROW = {"string": pa.string(), "bool": pa.bool_(), "int8": pa.int8(), "int16": pa.int16(),
         "date32": pa.date32(), "list<string>": pa.list_(pa.string())}


def table_spec(schema: dict, name: str) -> dict:
    cols = {}
    for c, spec in schema["tables"][name]["columns"].items():
        if "$ref" in spec:
            spec = schema["provenance_columns"][c]
        cols[c] = spec
    return cols


def to_arrow(schema: dict, name: str, rows: list[dict], pk: str) -> pa.Table:
    spec = table_spec(schema, name)
    rows = sorted(rows, key=lambda r: r[pk])
    fields, arrays = [], []
    for c, s in spec.items():
        t = ARROW[s["dtype"]]
        fields.append(pa.field(c, t, nullable=bool(s.get("nullable", False))))
        arrays.append(pa.array([r[c] for r in rows], type=t))
    return pa.Table.from_arrays(arrays, schema=pa.schema(fields))


def validate_table(schema: dict, name: str, tbl: pa.Table, errors: list):
    """G-03 on the staged table: exact columns, dtypes, nullability, allowed values, regex, lengths."""
    spec = table_spec(schema, name)
    if set(tbl.column_names) != set(spec):
        errors.append(f"{name}: columns differ {set(tbl.column_names) ^ set(spec)}")
    forbidden = set(schema["global_policy"]["forbidden_new_column_names"])
    if forbidden & set(tbl.column_names):
        errors.append(f"{name}: forbidden column {forbidden & set(tbl.column_names)}")
    limit = schema["global_policy"]["string_length_limit"]
    for c, s in spec.items():
        col = tbl.column(c).to_pylist()
        if tbl.schema.field(c).type != ARROW[s["dtype"]]:
            errors.append(f"{name}.{c}: dtype {tbl.schema.field(c).type}")
        if not s.get("nullable", False) and any(v is None for v in col):
            errors.append(f"{name}.{c}: null in non-nullable column")
        vals = [v for v in col if v is not None]
        if "allowed" in s:
            bad = {v for v in vals if v not in s["allowed"]}
            if bad:
                errors.append(f"{name}.{c}: values outside allowed {sorted(map(str, bad))[:5]}")
        if "regex" in s:
            rx = re.compile(s["regex"])
            bad = [v for v in vals if not rx.fullmatch(v)]
            if bad:
                errors.append(f"{name}.{c}: regex fails {bad[:3]}")
        if s["dtype"] == "string":
            mx = s.get("max_len", None if s.get("length_exempt_required") else limit)
            if mx is not None:
                over = [v for v in vals if len(v) > mx]
                if over:
                    errors.append(f"{name}.{c}: {len(over)} values over {mx} chars")


def parquet_bytes(tbl: pa.Table) -> bytes:
    sink = pa.BufferOutputStream()
    pq.write_table(tbl, sink, compression="zstd", compression_level=9, use_dictionary=True,
                   write_statistics=True, version="2.6", data_page_version="1.0")
    return sink.getvalue().to_pybytes()


# ============================================================================ withdrawn ids
def withdrawn_ids() -> set[int]:
    tree = ast.parse((DEST / "scripts" / "release_config.py").read_text(encoding="utf-8"))
    pii = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "EXCLUDED_RECIPE_IDS":
            pii = {ast.literal_eval(k) for k in node.value.keys}
    vend = json.loads((DEST / "data" / "provenance" / "withdrawn_ids.json").read_text(encoding="utf-8"))
    out = set(pii) | {int(k) for k in vend["v7_nonrecipe"]} | {int(k) for k in vend["v8_grihshobha"]}
    check({218869, 222341} <= out, "PII IDs missing from withdrawn set")
    return out


def all_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from all_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from all_strings(v)
    elif obj is not None:
        yield str(obj)


# ============================================================================ main
def main():
    (schema, occ, rules, meta, reg_rows, rule_rows, cit_rows, link_rows, scrub_log, reduction_log,
     transformations, nodes_sha, occ_keys, ctx_keys, rules_text) = build()
    errors: list[str] = []

    # status column is manifest-only; the frozen schema has no citation_status column.
    cit_status = {c["citation_uid"]: c["_status"] for c in cit_rows}
    cit_clean = [{k: v for k, v in c.items() if not k.startswith("_")} for c in cit_rows]
    reg_clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in reg_rows]

    tables = {
        "occasion_registry": to_arrow(schema, "occasion_registry", reg_clean, "occasion_uid"),
        "dietary_rules": to_arrow(schema, "dietary_rules", rule_rows, "rule_uid"),
        "context_citations": to_arrow(schema, "context_citations", cit_clean, "citation_uid"),
        "context_tag_links": to_arrow(schema, "context_tag_links", link_rows, "link_uid"),
    }
    for n, t in tables.items():
        validate_table(schema, n, t, errors)

    R = pd.DataFrame(reg_clean)
    D = pd.DataFrame(rule_rows)
    Ci = pd.DataFrame(cit_clean)
    L = pd.DataFrame(link_rows)

    # ---- OR-01..05
    if len(R) != 444 or not R.occasion_uid.is_unique or not R.source_occasion_id.is_unique:
        errors.append("OR-01")
    rule_uids = set(D.rule_uid)
    if not set(R.dietary_rule_uid.dropna()) <= rule_uids or R.dietary_rule_uid.notna().sum() != 178:
        errors.append(f"OR-02 dietary_rule_uid non-null={R.dietary_rule_uid.notna().sum()}")
    if not set(R.variant_of_uid.dropna()) <= set(R.occasion_uid) or R.variant_of_uid.notna().sum() != 11:
        errors.append("OR-02 variant_of_uid")
    if (R.source_text_sha256 != occ.source.map(sha256_text).values).any():
        errors.append("OR-03")
    if R.corpus_circular_source.sum() != 10:
        errors.append(f"OR-04 corpus_circular={R.corpus_circular_source.sum()}")
    unloc = R[~R.source_locatable]
    # OR-04 as amended by DATASET_INTEGRATION_SCOPE addendum 4: needs_gazette is accepted too.
    or04_violations = unloc[~unloc.verification_status.isin(["single_source", "needs_gazette"])]
    for col_out, col_in in [("kind", "kind"), ("religion", "religion"),
                            ("verification_status", "verification_status"),
                            ("dietary_status", "dietary_status"), ("registry_evidence_tier", "evidence_tier")]:
        if R[col_out].value_counts().to_dict() != occ[col_in].value_counts().to_dict():
            errors.append(f"OR-05 {col_out}")
    for b in ["gazetted_2026", "restricted_2026", "national_holiday", "compulsory_outside_delhi",
              "optional_outside_delhi", "moon_sighting_dependent"]:
        if int(R[b].sum()) != int((occ[b] == "True").sum()):
            errors.append(f"OR-05 {b}")

    # ---- DR-01..05
    if len(D) != 24 or set(D.source_rule_name) != {r["name"] for r in rules}:
        errors.append("DR-01")
    if D.destination_executable.any() or (D.label_status != "silver").any():
        errors.append("DR-02")
    tiers = D.evidence_tier.value_counts().to_dict()
    if tiers != EXPECTED_TIERS or set(D.loc[D.evidence_tier == "sourced", "source_rule_name"]) != EXPECTED_SOURCED:
        errors.append(f"DR-03 tiers={tiers}")
    for r in rules:
        row = D[D.source_rule_name == r["name"]].iloc[0]
        if (row.rule_class != r["class"] or list(row.excludes_tags) != list(r.get("excludes") or [])
                or (row.permits_tags is None) != (r.get("permits") is None)
                or (r.get("permits") is not None and list(row.permits_tags) != list(r["permits"]))):
            errors.append(f"DR-04 {r['name']}")
    lf = D[D.source_rule_name == "langar_feast"].iloc[0]
    if not (lf.rule_class == "narrowing" and list(lf.excludes_tags) == ["meat", "egg"]
            and list(lf.also_excludes_from_uids) == ["rule::khalsa_rehat"]):
        errors.append("DR-04 langar_feast")
    inv = {v["rule"]: k for k, v in (meta.get("standing_rules") or {}).items() if v and v.get("rule")}
    got = {r.source_rule_name: list(r.standing_for_religions) for r in D.itertuples()
           if r.standing_for_religions is not None}
    if got != {k: [v] for k, v in inv.items()}:
        errors.append(f"DR-05 {got}")

    # ---- CI-01/02
    subjects = set(R.occasion_uid) | rule_uids
    if not set(Ci.subject_uid) <= subjects or set(Ci.subject_uid) != subjects:
        errors.append("CI-01")
    if not Ci.set_index(["subject_uid", "citation_role", "citation_seq"]).index.is_unique:
        errors.append("CI-01 unique key")
    for name in D.loc[D.evidence_tier == "unsourced", "rule_uid"]:
        nr = Ci[(Ci.subject_uid == name) & (Ci.citation_kind == "none_recorded")]
        if len(nr) != 1 or nr.search_recorded.isna().any():
            errors.append(f"CI-02 {name}")

    # ---- TL-01..03
    if set(R.occasion_uid) - set(L.subject_uid):
        errors.append("TL-01")
    if ((L.target_node_id.isna()) != (L.link_type == "unmatched")).any():
        errors.append("TL-02 null iff unmatched")
    valid_targets = set(occ_keys.values()) | set(ctx_keys.values())
    if not set(L.target_node_id.dropna()) <= valid_targets:
        errors.append("TL-02 target exists")
    if (L.target_node_id.fillna("").str.startswith("context::") & ~L.subject_uid.str.startswith("rule::")).any():
        errors.append("TL-02 context target on non-rule")
    amb = set(L.loc[L.link_type == "ambiguous", "subject_uid"])
    if amb & set(L.loc[L.link_type.isin(["exact", "alias"]), "subject_uid"]):
        errors.append("TL-03 ambiguous also resolved")
    if (L.link_type == "alias").any():
        errors.append("alias rows are not generated by this script")
    if not L.link_uid.is_unique:
        errors.append("link_uid not unique")

    # ---- G-09: quotations, percentages, Pew in every string column of every new table
    src_spans, self_quotes = set(), []
    for s in occ.source:
        for q in quoted_spans(s):
            # A2 annotations quote the row's OWN note/date_rule ("own note: \"...\""): that is
            # source S1 text quoted back at itself, not third-party text, so it is not a G-09 span.
            if re.search(r"own (note|date_rule): " + re.escape(q), s):
                self_quotes.append(sha256_text(q))
                continue
            src_spans.add(q)
    for r in rules:
        for f in ("source", "certification_source", "time_of_day_source"):
            src_spans.update(quoted_spans(r.get(f) or ""))
    for ent in (meta.get("standing_rules") or {}).values():
        if ent:
            src_spans.update(quoted_spans(ent.get("source") or ""))
    src_spans.update(quoted_spans(meta.get("prevalence_source") or ""))
    inner = {s[1:-1] for s in src_spans}
    g09 = {"quoted_span_hits": [], "percent_hits": [], "pew_hits": [], "title_equals_quoted_title": []}
    for tname, df in [("occasion_registry", R), ("dietary_rules", D), ("context_citations", Ci),
                      ("context_tag_links", L)]:
        for c in df.columns:
            for i, v in df[c].items():
                vals = v if isinstance(v, list) else [v]
                for s in vals:
                    if not isinstance(s, str):
                        continue
                    if PCT.search(s):
                        if tname == "context_citations" and c == "url":
                            g09.setdefault("url_percent_encoding", []).append(df.at[i, "citation_uid"])
                        else:
                            g09["percent_hits"].append(f"{tname}.{c}")
                    if "Pew" in s and not (tname == "context_citations"
                                           and df.at[i, "citation_role"] == "prevalence_reference"):
                        g09["pew_hits"].append(f"{tname}.{c}")
                    for q in inner:
                        if q in s:
                            if tname == "context_citations" and c == "title" and s == q:
                                g09["title_equals_quoted_title"].append(df.at[i, "citation_uid"])
                            else:
                                g09["quoted_span_hits"].append(f"{tname}.{c}:{df.at[i, tables_pk[tname]]}")
    if g09["quoted_span_hits"] or g09["percent_hits"] or g09["pew_hits"]:
        errors.append("G-09 " + str({k: v[:5] for k, v in g09.items()}))

    # ---- G-05: withdrawn recipe IDs as integer tokens anywhere
    wd = withdrawn_ids()
    g05 = []
    for tname, t in tables.items():
        for s in all_strings(t.to_pylist()):
            for tok in re.findall(r"\d+", s):
                if int(tok) in wd:
                    g05.append(f"{tname}:{tok}")

    # ------------------------------------------------------------------ 81 vs 86
    first = {}
    for fam, lines in RIGHTS_REVIEW_LINES.items():
        for ln in lines:
            first[ln] = fam
    k82 = set(first)
    startswith86 = {r["_line"] for r in reg_rows
                    if any(occ.source[r["_line"] - 2].startswith(p) for p in RIGHTS_REVIEW_LINES)}
    strict = {r["_line"] for r in reg_rows if not r["source_locatable"]}
    by_base = {}
    for r in reg_rows:
        if not r["source_locatable"]:
            base = ANNOT.split(occ.source[r["_line"] - 2])[0].strip()
            by_base.setdefault(base[:60], []).append(r["_line"])

    def rowref(lines):
        return [{"csv_line": ln, "occasion_uid": f"occ::{occ.occasion_id[ln - 2]}",
                 "verification_status": occ.verification_status[ln - 2]} for ln in sorted(lines)]

    unlocatable = {
        "definition": "source_locatable=false when no registry_source citation names a work, site or "
                      "issuing body (every citation is descriptive_genre or corpus_self_reference); "
                      "annotation URLs count as locatable citations",
        "count_this_script": len(strict),
        "count_rights_review_list": len(k82),
        "count_schema_startswith_replay": len(startswith86),
        "rights_review_list_equals_strict_subset": sorted(k82 - strict) == [],
        "in_startswith_replay_but_locatable": rowref(startswith86 - strict),
        "in_rights_review_list_but_locatable": rowref(k82 - strict),
        "unlocatable_not_in_rights_review_list": rowref(strict - k82),
        "unlocatable_rows": rowref(strict),
        "unlocatable_by_base_clause": {k: sorted(v) for k, v in sorted(by_base.items())},
        "or_04_violations_not_single_source": rowref(set(or04_violations.prov_source_locator.astype(int))),
    }

    # ------------------------------------------------------------------ write
    files, blobs = {}, {}
    for n, t in tables.items():
        blobs[n] = parquet_bytes(t)
        files[f"data/cultural_context/{n}.parquet"] = sha256_bytes(blobs[n])

    st = pd.Series(cit_status).value_counts().to_dict()
    unresolved = sorted(k for k, v in cit_status.items() if v == "unresolved")
    script_sha = sha256_bytes(Path(__file__).read_bytes())
    lt = L.link_type.value_counts().to_dict()
    linked_nodes = set(L.target_node_id.dropna())
    manifest = {
        "schema_id": schema["schema_id"], "schema_version": schema["schema_version"],
        "tables": {n: f"data/cultural_context/{n}.parquet" for n in tables},
        "row_counts": {n: t.num_rows for n, t in tables.items()},
        "file_sha256": files,
        "input_sha256": {f"S1:{OCC_REL}": PIN[OCC_REL]["sha256"],
                         f"S1:{RULES_REL}": PIN[RULES_REL]["sha256"],
                         "IndicRecipeNutri-dataset@0.10.0:data/kg/kg_nodes.parquet": nodes_sha,
                         f"schema:{SCHEMA_JSON.name}": sha256_bytes(SCHEMA_JSON.read_bytes())},
        "input_hash_reverified_before_read": True,
        "source_commits": {f"S1:{OCC_REL}": {"commit": PIN[OCC_REL]["commit"], "blob": PIN[OCC_REL]["blob"],
                                                    "note": "worktree differs from HEAD by CRLF only"},
                           f"S1:{RULES_REL}": {"commit": PIN[RULES_REL]["commit"], "blob": None,
                                                      "note": "uncommitted working copy against HEAD 5d8d780"}},
        "source_rules_meta_version": str(meta["version"]),
        "evidence_tier_counts": {"dietary_rules": D.evidence_tier.value_counts().sort_index().to_dict(),
                                 "occasion_registry.registry_evidence_tier":
                                     R.registry_evidence_tier.value_counts().sort_index().to_dict()},
        "label_status_counts": {n: pd.Series(t.column("label_status").to_pylist()).value_counts().to_dict()
                                for n, t in tables.items() if "label_status" in t.column_names},
        "link_type_counts": {k: int(lt.get(k, 0)) for k in ["exact", "alias", "ambiguous", "unmatched"]},
        "link_counts_by_subject_kind": {
            "occasion_registry": L[L.subject_uid.str.startswith("occ::")].link_type.value_counts().to_dict(),
            "dietary_rules": L[L.subject_uid.str.startswith("rule::")].link_type.value_counts().to_dict()},
        "exact_links": sorted(f"{a} -> {b}" for a, b in
                              L.loc[L.link_type == "exact", ["subject_uid", "target_node_id"]].values),
        "existing_occasion_nodes_without_link": {
            "count": len(set(occ_keys.values()) - linked_nodes),
            "total_occasion_nodes": len(occ_keys),
            "node_ids": sorted(set(occ_keys.values()) - linked_nodes)},
        "existing_context_nodes_without_link": sorted(set(ctx_keys.values()) - linked_nodes),
        "link_policy": "exact = lower-cased source_occasion_id or name (registry) / rule name (rules) equals "
                       "the node key; no alias rows are generated (none reviewed); >1 candidate -> ambiguous, "
                       "unresolved; reviewed_by/reviewed_on are null because no human review was performed",
        "citation_status_counts": st,
        "citation_status_definition": {
            "resolved": "has a url, identifier or title taken verbatim from the upstream cell",
            "unresolved": "only a publisher/site is named; the specific work cannot be identified from the row",
            "descriptive_genre": "the upstream names a genre or gives its own descriptive basis; title holds that "
                                 "wording verbatim and is not a work title",
            "corpus_self_reference": "cites the IndicRecipeNutri KG itself (unstated pre-0.10.0 version)",
            "none_recorded": "unsourced rule; search_recorded preserves the upstream's failed search"},
        "unresolved_citation_uids": unresolved,
        "externally_verified_citations": [
            {"rule": n, "role": r, "fields": sp["external"]["fields"], "evidence": sp["external"]["evidence"],
             "verified_on": sp["external"]["verified_on"]}
            for n, lst in sorted(RULE_CITATIONS.items()) for r, sp, _ in lst if sp.get("external")],
        "citation_role_counts": Ci.citation_role.value_counts().sort_index().to_dict(),
        "unlocatable_source_rows": unlocatable,
        "dropped_fields": {
            "occasions.csv": schema["tables"]["occasion_registry"]["dropped_source_columns"],
            "rules.yaml": schema["tables"]["dietary_rules"]["dropped_source_fields"],
            "rules.yaml meta (not imported)": ["surveyed", "sourced", "sourcing_note", "time_of_day_recorded",
                                               "a11_note", "sect_variants_recorded", "a12_note",
                                               "standing_rules_recorded", "standing_rules_note", "classes",
                                               "n_rules", "prevalence_source"],
            "citation detail with no frozen column": ["author names (no author column)",
                                                      "document dates other than access date",
                                                      "schemeless web addresses are kept in `locator`, never "
                                                      "promoted to `url`"]},
        "transformations": sorted(transformations + [
            {"id": "T-SRC", "table": "occasion_registry", "action": "source cell reduced to context_citations "
             "(role registry_source) + source_text_sha256; A2/A4/A5/A6 annotation prose and every quoted span "
             "dropped; annotation URLs kept as web_page citations (access_date = annotation date)",
             "rows": len(R), "citations_written": int((Ci.citation_role == "registry_source").sum()),
             "quoted_spans_dropped_with_source": sum(len(quoted_spans(s)) for s in occ.source)},
            {"id": "T-RULESRC", "table": "dietary_rules", "action": "source, certification_source, "
             "time_of_day_source and meta.standing_rules.*.source reduced to context_citations; quotations dropped",
             "rows": len(D), "citations_written": int((~Ci.subject_uid.str.startswith("occ::")).sum())},
            {"id": "T-PREV", "action": "meta.prevalence_source dropped (Pew 2021 percentages); Pew kept only as "
             "a number-free prevalence_reference citation on rule::sattvic_vegetarian"},
            {"id": "T-RENAME", "action": "renamed columns", "map": {
                "occasion_id": "source_occasion_id", "evidence_tier": "registry_evidence_tier",
                "date_rule": "date_rule_text", "note": "registry_note / rule_note", "class": "rule_class",
                "executable": "source_executable", "excludes": "excludes_tags", "permits": "permits_tags",
                "corpus_filter": "corpus_filter_text", "time_of_day": "time_of_day_text",
                "time_of_day_absent": "time_of_day_absent_reason",
                "variation_not_enumerable": "variation_not_enumerable_reason",
                "sect_variants": "sect_variants_json (JSON text)"}},
            {"id": "T-NS", "action": "namespaced ids", "map": {
                "occasion_id": "occ::<id>", "dietary_context": "dietary_rule_uid = rule::<name>",
                "variant_of": "variant_of_uid = occ::<id>", "rules[].name": "rule::<name>",
                "also_excludes_from": "rule::<name>"}},
            {"id": "T-TYPES", "action": "types", "detail": "True/False strings -> bool; n_sources '2.0' -> int8 "
             f"({int(R.n_sources.notna().sum())} non-null); date_2026 -> date32 ({int(R.date_2026.notna().sum())} "
             "non-null); empty strings -> null; search_recorded -> date32"},
            {"id": "T-ADD", "action": "added columns", "detail": "destination_executable=false (all), "
             "evidence_tier, label_status=silver, source_locatable, corpus_circular_source, source_text_sha256, "
             "note_text_sha256, rule_note_reduced, source_reduced_to_citations, standing_for_religions "
             "(inverted meta.standing_rules), tag_vocabulary, prov_*"},
            {"id": "T-DROP", "action": "dropped corpus_recipe_count and in_corpus (corpus-circular, unstated version)"},
        ], key=lambda t: t["id"]),
        "quotation_review": sorted(scrub_log, key=lambda x: (x["field"], x["subject"], x["span_sha256"])),
        "registry_source_reduction": sorted(reduction_log, key=lambda x: x["occasion_uid"]),
        "g09_self_check": {"quoted_span_hits": len(g09["quoted_span_hits"]),
                           "percent_hits": len(g09["percent_hits"]), "pew_hits_outside_prevalence_reference":
                               len(g09["pew_hits"]),
                           "citation_titles_equal_to_a_quoted_span_in_source": sorted(g09["title_equals_quoted_title"]),
                           "urls_with_percent_encoding_not_counted_as_percentages":
                               sorted(g09.get("url_percent_encoding", [])),
                           "self_quotations_of_own_note_or_date_rule_exempted": len(self_quotes),
                           "note": "titles are quoted in their source cells as titles, not as text quotations; a "
                                   "literal G-09 will match them unless citation titles are exempted"},
        "g05_withdrawn_id_tokens": {"hits": len(g05), "withdrawn_set_size": len(wd)},
        "or_04_status": "PASS" if or04_violations.empty else
                        f"FAIL: {len(or04_violations)} unlocatable rows are neither single_source nor needs_gazette",
        "or_04_rule": "unlocatable rows must be single_source or needs_gazette (OR-04 as amended by "
                      "the dataset owner, 2026-09-23)",
        "self_check_errors": errors,
        "licence": schema["layer_manifests"]["data/cultural_context/CONTEXT_MANIFEST.json"]["licence"],
        "attribution": [
            "Badgujar, H. Y., Borde, S. P. and Gurav, Y. Occasion registry for constrained food recommendation "
            "(internal source S1, data/registry/occasions.csv, git blob e0f408d5); licensor H. Y. Badgujar; CC BY 4.0. "
            "https://creativecommons.org/licenses/by/4.0/ Modified for IndicRecipeNutri 0.11.0: see "
            "`transformations` in this manifest.",
            "Badgujar, H. Y., Borde, S. P. and Gurav, Y. Dietary-rule predicates (data/rules/rules.yaml, version "
            "0.2.0, internal source S1, uncommitted working copy of commit 5d8d780, SHA-256 b1ed03b0...952c9f); "
            "licensor H. Y. Badgujar; CC BY 4.0. https://creativecommons.org/licenses/by/4.0/ Modified for IndicRecipeNutri "
            "0.11.0: see `transformations` in this manifest."],
        "import_scripts": {SCRIPT_ID: script_sha},
        "not_executed": schema["layer_manifests"]["data/cultural_context/CONTEXT_MANIFEST.json"]["not_executed"],
        "personal_observance": "No column describes a person; religion/scope/states_observed/"
                               "standing_for_religions describe an occasion's or rule's tradition.",
    }
    mtext = json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n"
    # G-05 also over the manifest strings
    for tok in re.findall(r"\d+", mtext):
        if len(tok) <= 7 and int(tok) in wd:
            g05.append(f"manifest:{tok}")
    if g05:
        errors.append(f"G-05 {g05[:5]}")
        manifest["g05_withdrawn_id_tokens"]["hits"] = len(g05)
        manifest["self_check_errors"] = errors
        mtext = json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n"
    if errors:
        print("SELF-CHECK ERRORS (nothing written):", errors, file=sys.stderr)
        raise SystemExit(3)
    OUT.mkdir(parents=True, exist_ok=True)
    for n, b in blobs.items():
        (OUT / f"{n}.parquet").write_bytes(b)
    (OUT / "CONTEXT_MANIFEST.json").write_bytes(mtext.encode("utf-8"))
    files["data/cultural_context/CONTEXT_MANIFEST.json"] = sha256_bytes(mtext.encode("utf-8"))

    # ------------------------------------------------------------------ console summary
    print("row_counts", manifest["row_counts"])
    print("evidence_tiers", manifest["evidence_tier_counts"]["dietary_rules"])
    print("citation_status", st, "roles", manifest["citation_role_counts"])
    print("link_types", manifest["link_type_counts"], "occasion nodes without link",
          manifest["existing_occasion_nodes_without_link"]["count"], "/", len(occ_keys))
    print("unlocatable strict", len(strict), "rights review", len(k82), "startswith", len(startswith86),
          "| OR-04", manifest["or_04_status"])
    print("g09", manifest["g09_self_check"]["quoted_span_hits"], manifest["g09_self_check"]["percent_hits"],
          manifest["g09_self_check"]["pew_hits_outside_prevalence_reference"],
          "titles=quoted", len(g09["title_equals_quoted_title"]), "| g05 hits", len(g05))
    for k, v in sorted(files.items()):
        print("sha256", v, k)
    # OR-04 is reported in the manifest, not fatal: it is a data finding for the user.
    return 0


tables_pk = {"occasion_registry": "occasion_uid", "dietary_rules": "rule_uid",
             "context_citations": "citation_uid", "context_tag_links": "link_uid"}

if __name__ == "__main__":
    sys.exit(main())
