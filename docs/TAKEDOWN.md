# Takedown and opt-out

If you hold rights in content that appears in this dataset, or you are the operator of
a source site and do not want your recipes represented here, we will act on your
request. You do not need to prove ownership beyond a plausible claim, and we will not
ask you to justify the request.

## What is actually published

Before filing, it may help to know what this repository contains. Recipe prose —
headnotes, free-text instructions, the raw ingredient string, keywords — is **not**
redistributed. What is published for each recipe is a title, a parsed ingredient list,
nutrition estimates, typed attributes, and the URL of the source page.

## How to request removal

Open an issue titled `takedown: <site or recipe>` on the repository, or email
`hemprasad.badagujar@gmail.com` with subject line `IndicRecipeNutri takedown`.

Include whichever you have:

- the source site domain, to remove every recipe collected from it;
- specific `recipe_id` values or source URLs;
- a description sufficient to identify the rows.

## What we do

1. **Acknowledge within 7 days.**
2. **Remove the rows from the working master** and rebuild the affected artefacts —
   corpus, knowledge graph, enrichment tables and benchmark gold sets.
3. **Cut a new tagged release** with the rows absent, and record the removal in
   `CHANGELOG.md` as a count and a date, naming no individual.
4. **Request that the superseding version be the default on Zenodo.** Note the limit
   honestly: Zenodo records are designed to be permanent, and earlier version DOIs may
   remain resolvable. We can request restriction of a prior version but cannot promise
   its deletion. If that matters to your request, say so and we will raise it with
   Zenodo directly.

## Scope

This covers content in this repository. It does not extend to the source sites
themselves, to other copies made by third parties from earlier releases, or to
re-hydrated text a user fetched themselves under their own agreement with your site.
