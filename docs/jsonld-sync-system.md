# WikiAI.hu – automatic HFCM JSON-LD mirror (v2)

**Source of truth:** publicly rendered Schema.org JSON-LD in the live WordPress business profile's HEAD, configured through HFCM. GitHub is a mirror, not a separate authority.

**Scope:** all published business profiles in **manifest.json**, including new profiles. The WikiAI.hu first-party publisher profile at /wikiai-hu/ is excluded because it follows a separate publisher schema.

## Components

- **.github/scripts/sync-deep-jsonld.py** – validation and one-way synchronization
- **.github/scripts/test_sync_deep_jsonld.py** – automated regression tests
- **.github/workflows/sync-deep-jsonld.yml** – recurring runner
- **manifest.json** – published company inventory from WordPress
- **entities/SLUG.md** – existing Markdown mirror published by the WordPress plugin
- **entities/SLUG.jsonld** – exact deep graph mirrored from live HFCM HTML
- **jsonld-sync-manifest.json** – tracked mirror checksums and migration history
- **jsonld-sync-status.json** – per-company health report and warnings

## Scheduling

- Every hour, at approximately minute 17.
- Immediately following main-branch pushes updating the WordPress manifest, company Markdown files, sync script, tests, or workflow.
- On demand: GitHub → Actions → Mirror all WikiAI business HFCM JSON-LD → Run workflow.

**HFCM-only edits do not dispatch an immediate webhook:** they are detected on the next hourly check or manual run. No WordPress credentials are needed to read public website content. GitHub Actions writes with its scoped repository token.

## Publishing a new company

1. Publish a post in the **Vállalkozások** WordPress category using its stable canonical HTTPS URL.
2. Allow WikiAI GitHub Entity Sync to create the company Markdown file and add it to **manifest.json**.
3. Activate one company-specific HFCM deep JSON-LD script in the WordPress HEAD, restricted to that post.
4. The automatic job reads the **rendered public WordPress page**, validates the deep graph and creates or updates the JSON-LD mirror.
5. Check **jsonld-sync-status.json**: the company should have status **ok**. Review its warnings if any.
6. Submit the **canonical WikiAI.hu WordPress URL**, not GitHub mirror URLs, to Google Search Console when appropriate.

Do not invent CID, KGMID, Place IDs, third-party authority, prices, ratings or certifications to pass checks.

## Old profiles and compatible identity formats

Legacy graphs may use own-domain IDs, on-site business IDs, restaurant IDs, or short JSON-LD prefixes explicitly defined in their context. The validator follows actual Article → business relationships, expanding declared prefixes rather than assuming the Porvadászok schema is universal.

A historical Article without a WebPage may be accepted only when it has the matching canonical mainEntityOfPage URL and its about field uniquely points to a named business. A one-time historic identity-ID change requires the **same business name**, a complete valid source graph, and no existing managed-state conflict.

Existing mirrors are enrolled after checking the current live graph. Earlier versions remain in GitHub history. For managed files, unexpected edits or major content shrinkage fail closed.

## Safety and reporting

The workflow reports failure when any company cannot be mirrored, while still saving successful company updates and an audit report. Problems never delete or overwrite an existing validated mirror.

Checks: correct HTTPS canonical host, successful HTTP response, public rendered HEAD, valid JSON-LD, exactly one matching deep graph, consistency between Article and business entity, WikiAI publisher, unique node IDs, minimum graph depth, and checksum guard.

- [Actions run history](https://github.com/WikiAI-hu/wikiai-entities/actions/workflows/sync-deep-jsonld.yml)
- [Current per-company report](https://github.com/WikiAI-hu/wikiai-entities/blob/main/jsonld-sync-status.json)
- [Tracked mirror state](https://github.com/WikiAI-hu/wikiai-entities/blob/main/jsonld-sync-manifest.json)

Warnings can identify missing DigitalDocument mirror references, older editorial author/editor roles, legacy entity IDs, or problematic Article relationships. **Fix warnings at the WordPress/HFCM source**, not by making a disconnected GitHub-only edit.

If a previously published company disappears from the manifest, the mirror is flagged for review, not silently deleted. The first-party WikiAI.hu publisher profile remains outside business-profile synchronization.

## Initial deployment

2026-10-17: all **17 published external business profiles** reached a mirrored state with **0 blocking synchronization errors**. Non-blocking source-quality warnings are shown independently in the audit report.

## Retired personal-domain identity transition (2026-10-23)

The preferred editor identity is `https://www.wikiai.hu/szakertok/varhelyi-csanad/#person`, replacing historical `https://www.varhelyicsanad.hu/#person`. The validator treats the old form as a **deprecated source warning**, not as a different person; it never silently rewrites authoritative WordPress/HFCM JSON-LD. Update active HFCM source graphs to use the current Person ID, then let the hourly audited mirror synchronize. For any graph with a compact `vc:person` reference, update both the prefix mapping and the actual source identifier, preserving Schema.org graph identity consistency.

Do not directly patch checksum-managed `entities/*.jsonld` snapshots to hide source-level inconsistencies. The unchanged legacy URLs remaining in these mirrors represent WordPress-originated data awaiting an upstream update.
