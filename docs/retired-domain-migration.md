# Retired varhelyicsanad.hu domain – source-of-truth migration

Date: 2026-10-23

## Current public identifiers

- Várhelyi Csanád, Person: https://www.wikiai.hu/szakertok/varhelyi-csanad/#person
- Várhelyi Csanád, expert profile: https://www.wikiai.hu/szakertok/varhelyi-csanad/
- Várhelyi Viktória, Person: https://www.wikiai.hu/szakertok/varhelyi-viktoria/#person
- Várhelyi Viktória, expert profile: https://www.wikiai.hu/szakertok/varhelyi-viktoria/
- WikiAI.hu, Organization: https://www.wikiai.hu/#organization
- WikiAI.hu, WebSite: https://www.wikiai.hu/#website

The two professionals are separate people. Várhelyi Viktória founded and operates the platform; Várhelyi Csanád is its responsible editor and lead editorial author, and has a separate independent professional-services role.

## Updated directly in GitHub

- Manual public editor/platform relationship record.
- Manual team JSON-LD identity references.
- Documentation and compatibility-oriented audit/test expectations.

## Must be corrected upstream in WordPress/HFCM

1. Find active WordPress HFCM scripts that still declare `varhelyicsanad.hu` for the above people; replace entity IDs and related public profile URLs in the **source** while retaining the actual business-specific entity IDs.
2. Update WordPress page content links, including the Várhelyi Viktória profile and existing business article bylines.
3. Verify that the published rendered Schema.org graph still has unique resolved `@id` values, consistent `author`, `editor`, `accountablePerson`, `founder` references, and unchanged legal owner/operator identity.
4. For `wikiai/wikiai-hu.jsonld`, update the manually versioned snapshot only after its live WordPress/HFCM graph has been updated. The official-graph audit enforces exact equality.
5. Let the business JSON-LD GitHub Actions mirror and the WordPress Markdown/organizational-knowledge mirrors refresh naturally. Review their sync status, error logs, and checksum state. Avoid direct edits to checksum-managed mirror files.
6. Confirm redirects, canonical tags, structured data and accessible images on the live site. The GitHub changes alone do not change WordPress pages, HFCM source, or the domain redirect configuration.

## Transitional legacy identifiers

The following historical URLs may still legitimately be present in live-source mirrors, tests and compatibility validators **until the source changes**:

- `https://www.varhelyicsanad.hu/#person`
- `https://www.varhelyicsanad.hu/varhelyi-viktoria.html#person`

These are **deprecated legacy references**, not the preferred person identifiers. Intentional handling in tests does not mean the retired domain remains a canonical website. This document tracks the upstream dependency; it is not a claim that a WordPress migration is already complete.
