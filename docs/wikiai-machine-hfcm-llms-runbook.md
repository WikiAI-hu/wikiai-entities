# WikiAI.hu HFCM -> Machine HTML -> GitHub -> virtual llms.txt

Deployment: 2026-10-17. WordPress/Code Snippets remain canonical. GitHub is a secondary, version-controlled mirror. No physical `/llms.txt` file is required.

## Production components

| Component | Active code | Job |
| --- | --- | --- |
| Virtual short llms.txt | Code Snippets #102 | GET /llms.txt, dynamic entity/knowledge/verified JSON-LD links |
| Virtual long llms-full.txt | Code Snippets #103 | Long-context snapshot, independent fetch of wikiai/manifest.json |
| Entity HTML Generator | Code Snippets #107 | HFCM source -> /entity/SLUG.html |
| Rendered fallback | Code Snippets #115 | Rendered WordPress JSON-LD -> /entity/SLUG.html when primary fails |
| HFCM save-event watcher | Code Snippets #117 | Immediate regeneration on supported HFCM admin save/toggle |
| Internal HFCM GET-only adapter | Code Snippets #129 | Authenticated HFCM metadata and UTF-8-dechunked, decoded source |
| Scheduled source watchdog | Code Snippets #132 | Every ~15 min: fingerprint HFCM+post edits, refresh changed machines |
| Entity discovery and status | Code Snippets #111 | Index and live virtual llms.txt status |
| WikiAI Machine Delivery | Plugin v0.2.2 | Published first-party JSON/HTML machine catalog |
| GitHub entity Markdown | WikiAI GitHub Entity Sync plugin | Business Markdown records and root manifest.json |
| GitHub deep JSON-LD | GitHub Actions | Mirror validated current HFCM graphs from live business pages |
| GitHub knowledge | GitHub Actions | Published WordPress organizational pages and expert Markdown |

The deprecated #57 (temporary writable HFCM bridge), #61 (temporary HFCM audit helper), and #130 (temporary admin-only code inspector) must remain **inactive**. #112 (old llms.txt post-processor) is now **inactive** because #102 writes the entity link itself.

## Internal HFCM adapter

Source: [wordpress/snippets/wikiai-hfcm-readonly-adapter.php](../wordpress/snippets/wikiai-hfcm-readonly-adapter.php)

Endpoints:
- GET `/wp-json/wikiai-hfcm/v1/list`
- GET `/wp-json/wikiai-hfcm/v1/snippet-chunk/{id}?offset=0&length=2200`

They are read-only. The source is accessible only to authorized administrators or in genuine **internal WP-Cron** execution. They must return HTTP 401/403 to anonymous web requests. The adapter HTML-decodes entire HFCM source **before** splitting into chunks; previous source was stored as `&lt;script` and `&quot;`, preventing direct use by #107.

## HFCM source watchdog

Source: [wordpress/snippets/wikiai-hfcm-consistency-watchdog.php](../wordpress/snippets/wikiai-hfcm-consistency-watchdog.php)

WordPress cron event: `wikiai_hfcm_watchdog_tick`, custom recurrence `wikiai_hfcm_15min` (900 seconds). WP-Cron runs when traffic or server cron triggers it; do not promise precise 15-minute execution.

- Audits published business profiles in category #8, except first-party profile #637.
- Fingerprints active, post-specific HFCM script ID and hash plus WordPress modification timestamp.
- Non-destructive **first-run baseline**; no blanket overwrite.
- On later source changes, regenerates only affected `/entity/SLUG.html` records and evicts the WordPress post cache where supported.
- If the active HFCM source is absent or generated machine HTML shrinks unexpectedly, records an error and retains the previous good HTML where possible. Does not rewrite HFCM or business WordPress content.
- Does not interfere with GitHub's hourly live JSON-LD mirror.

Admin-only endpoints:
- GET `/wp-json/wikiai-hfcm-watchdog/v1/status`
- POST `/wp-json/wikiai-hfcm-watchdog/v1/reconcile` for a baseline/current-state check
- POST `/wp-json/wikiai-hfcm-watchdog/v1/reconcile` with `{"post_id": 1517, "force": true}` for a controlled, guarded regeneration of a single business

Be careful with forced regeneration; no bulk destructive tool is exposed. The current/last change report is stored in WordPress option `wikiai_hfcm_watchdog_status_v1`; managed source fingerprints in `wikiai_hfcm_watchdog_hashes_v1`.

## Virtual llms.txt

Source: [wordpress/snippets/wikiai-virtual-llms-txt.php](../wordpress/snippets/wikiai-virtual-llms-txt.php)

The original Code Snippets #102 is backed up **inactive** as #131, for rollback. Do **not** enable both at the same time because they declare the same PHP functions.

The virtual document reads:
- GitHub root `manifest.json` (existing last-good cache, canonical entity inventory).
- GitHub `wikiai/manifest.json` (dynamic WordPress expert profiles, no fixed retired-person list).
- GitHub `jsonld-sync-manifest.json` (only SHA-verified managed JSON-LD mirrors, not a handwritten slug array).
- Explicit `https://www.wikiai.hu/entity/` machine HTML directory.

The new external manifests use 10-minute transients and last-known-good caches to remain available during a GitHub RAW outage. WordPress's published pages are canonical; GitHub is not a replacement.

**Code Snippets #111** previously reported `llms_has_entity_index:false` whenever no physical `/llms.txt` file existed. Its diagnostic now inspects the actual virtual document from #102, yielding `llms_source:virtual-code-snippets` and `llms_has_entity_index:true`. Its pre-migration version is retained inactive as #133.

The old `wikiai_ed2_last_sync` date and `llms:false` are historical records of a previous physical file patch attempt, not current virtual-document health. Do not erase past diagnostics to fake recent execution.

## Verified results during rollout

- Admin-only HFCM source can be fetched and decoded, while anonymous access is blocked.
- Porvadászok entity #1517 regenerated directly from active HFCM #40 (over 160 KB).
- All **17 of 17 external businesses** now have machine HTML and an associated nonzero HFCM script ID.
- Source watchdog baselined 17 businesses and successfully force-regenerated Porvadászok, Európa Terv, Vargánya and other historical HFCM-derived records without source loss.
- WordPress Machine Delivery remains `ready` with 103 consistent records, without missing machine JSON/HTML files.
- The live virtual llms.txt contains exactly one entity directory link, all 17 company JSON-LD mirrors, the current three professional people, and no old Molnár András profile.
- Repository PHP snippets passed syntax validation in GitHub Actions.

## Continuous verification

- [Daily machine/llms security and discovery audit](https://github.com/WikiAI-hu/wikiai-entities/actions/workflows/audit-wikiai-machine-chain.yml)
- [PHP syntax lint](https://github.com/WikiAI-hu/wikiai-entities/actions/workflows/lint-wikiai-php.yml)
- [JSON-LD mirror health](https://github.com/WikiAI-hu/wikiai-entities/blob/main/jsonld-sync-status.json)
- [Current business mirror status](https://github.com/WikiAI-hu/wikiai-entities/blob/main/jsonld-sync-manifest.json)
- [Current knowledge mirror](https://github.com/WikiAI-hu/wikiai-entities/blob/main/wikiai/manifest.json)

## Remaining separate tasks

The JSON-LD mirror status currently includes **eight nonblocking quality warnings** in three companies (Hajdúszoboszlói Ásványvíz, Porvadászok and Vargánya Étterem). They concern source Schema.org editorial relationships and mirror references. They were **not** cleared merely to make an audit green. Verify source facts and correct the HFCM only when grounded. Distinguish crawl/indexing outcomes in Google Search Console from machine mirror health.
