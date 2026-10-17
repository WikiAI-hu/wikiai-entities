# WikiAI.hu - dynamic organizational knowledge mirror

**Source of truth:** published WordPress pages at https://www.wikiai.hu/.
**GitHub:** secondary public Markdown and knowledge indexes.

## Why this exists

The older WordPress plugin **WikiAI GitHub Knowledge Sync 0.1.3** had an obsolete fixed staff mapping: former WordPress page #145 remained in its admin list and generated knowledge manifest after the page no longer existed. It did not dynamically add the published Simon Imre profile (#1334) to its person list.

The replacement GitHub Actions job reads the public WordPress REST list of **published pages** and derives its roster from actual published /szakertok/SLUG/ person pages. Person IDs are not hardcoded as a permanent allow-list. New profiles appear when published; unpublished or deleted profiles disappear from index and manifest. It never invents nonpublic people.

## Mirrored content

Core organizational Markdown (5 published pages):

- wikiai/services.md - WordPress #101
- wikiai/pricing.md - WordPress #202
- wikiai/about.md - WordPress #21
- wikiai/team.md - WordPress #22
- wikiai/contact.md - WordPress #23

Dynamic people:

- wikiai/people/SLUG.md for each published expert profile at /szakertok/SLUG/
- wikiai/manifest.json - dynamically derived published pages/person list
- wikiai/index.md - dynamically derived staff/partner links
- wikiai/knowledge-sync-state.json - tracked SHA-256 checksums
- wikiai/knowledge-sync-status.json - audit and orphan report

Existing Markdown stays byte-for-byte if its WordPress modified timestamp is unchanged. Updated pages are converted from current rendered WordPress HTML, using a pinned HTML-to-Markdown library. Git history retains older versions. Out-of-band changes to an enrolled managed mirror block overwrite.

## Scheduling

- Every hour at approximately minute 15 (GitHub Actions timing may be delayed).
- On pushes to main affecting the script, workflow, knowledge manifest/index, or person Markdown.
- Manually via Actions -> Mirror WikiAI organizational knowledge from WordPress -> Run workflow.

No WordPress-to-GitHub write token is stored in this job. GitHub Actions uses the scoped repository token.

## Separation and safety

- **Do not deactivate WikiAI GitHub Entity Sync**: it publishes the separate business Markdown records in entities/ and maintains the root business manifest used by JSON-LD automation.
- **WikiAI GitHub Knowledge Sync is a different plugin.** Its WordPress-side HTML/Markdown link discovery and root-manifest repair are not recreated by the GitHub-only job. Evaluate these features before deactivation.
- The new job never modifies the business entities/ folder.
- It does **not** overwrite manually maintained wikiai/team.jsonld, wikiai/wikiai-hu.jsonld, or wikiai/people/*.jsonld.
- Missing core WordPress pages and incomplete REST inventories cause an error rather than incomplete publication.
- Unpublished/deleted people are removed from index/manifest; orphan Markdown is flagged instead of being deleted silently.

## Verified migration (2026-10-17)

The 5 core pages and all 3 then-published expert profiles were confirmed. Knowledge manifest/index include Várhelyi Csanád, Várhelyi Viktória and Simon Imre. The former page #145 is absent from the published WordPress inventory and from the current knowledge manifest/index.

The legacy plugin was **not** deactivated by the repository migration; this runbook does not claim replacement of WordPress-side HTML discovery.

## Monitoring

- [Actions](https://github.com/WikiAI-hu/wikiai-entities/actions/workflows/sync-wikiai-knowledge.yml)
- [Knowledge audit](https://github.com/WikiAI-hu/wikiai-entities/blob/main/wikiai/knowledge-sync-status.json)
- [Knowledge manifest](https://github.com/WikiAI-hu/wikiai-entities/blob/main/wikiai/manifest.json)
- [Knowledge index](https://github.com/WikiAI-hu/wikiai-entities/blob/main/wikiai/index.md)

Canonical search-engine URLs remain the live WordPress pages, not GitHub Markdown links.
