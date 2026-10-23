# WikiAI.hu Entities

Machine-readable entity and public knowledge records published by **WikiAI.hu**.

This repository is a public, versioned machine-readable mirror of selected business entity profiles and selected WikiAI.hu organizational knowledge published on https://www.wikiai.hu/.

## Source-of-truth policy

- **WordPress / WikiAI.hu is the primary source of truth.**
- GitHub is a machine-readable publication and version-history layer.
- Synchronization direction is intended to be **WikiAI.hu → GitHub**, not GitHub → WordPress.
- Human-facing editorial content remains on WikiAI.hu.
- Repository records are structured for LLM, RAG, agent, search, and data-processing use.

## Repository structure

```text
wikiai-entities/
├── README.md
├── entities.md
├── manifest.json
├── entities/
│   ├── tasca-ponte-debrecen.md
│   └── ...
└── wikiai/
    ├── index.md
    ├── manifest.json
    ├── services.md
    ├── pricing.md
    ├── about.md
    ├── team.md
    ├── contact.md
    └── people/
        ├── varhelyi-csanad.md
        ├── varhelyi-viktoria.md
        └── simon-imre.md
```

## Two machine-readable knowledge layers

### `entities/`

Business entities presented by WikiAI.hu.

Each entity file uses:

1. YAML front matter for stable machine-readable metadata.
2. Markdown sections for semantic context and disambiguation.
3. Canonical links back to the corresponding WikiAI.hu entity profile.
4. Explicit business boundaries so systems do not infer services that the business does not provide.

### `wikiai/`

Machine-readable organizational knowledge about WikiAI.hu itself.

This layer currently contains:

- services;
- current pricing and commercial packages;
- about / mission;
- team and professional-partner relationships;
- contact information;
- individual professional profiles.

Pricing and other fast-changing commercial data must be interpreted together with their explicit `valid_as_of` or freshness metadata.

## Publisher

**WikiAI.hu** — Magyar vállalkozások az AI korszakában.

Canonical website: https://www.wikiai.hu/

## Structured JSON-LD mirrors

The WordPress pages and their active HFCM structured data are the first-party source of truth. These versioned JSON-LD snapshots were verified against the live WikiAI.hu frontend on 2026-10-09. They are not a replacement for the canonical site and need re-synchronization after future WordPress/HFCM changes.

- [WikiAI.hu official platform JSON-LD](wikiai/wikiai-hu.jsonld) — https://www.wikiai.hu/wikiai-hu/
- [Munkatársaink team JSON-LD](wikiai/team.jsonld) — https://www.wikiai.hu/szakertok/
- [Simon Imre person profile JSON-LD](wikiai/people/simon-imre.jsonld) — https://www.wikiai.hu/szakertok/simon-imre/
- [Várhelyi Csanád deep Person/ProfilePage JSON-LD snapshot](wikiai/people/varhelyi-csanad.jsonld) — https://www.wikiai.hu/szakertok/varhelyi-csanad/ (2026-10-22, active HFCM #42; manual snapshot, WordPress is canonical)

Simon Imre and INF-GROUP Kft. are external IT infrastructure partners, not internal WikiAI.hu employees or owners.

## Automated deep JSON-LD mirror

The published business profiles in WordPress's **Vállalkozások** category are mirrored to GitHub in two formats:

- Markdown by the existing WikiAI GitHub Entity Sync WordPress plugin.
- Full Schema.org JSON-LD by a scheduled GitHub Actions job that validates the **publicly rendered HFCM source** before updating the GitHub mirror.

The JSON-LD job is monitored per business, supports historic Schema.org variants, runs hourly and after manifest updates, and refuses destructive or conflicting changes. The WikiAI.hu first-party platform profile is a separate exception.

- [Operational runbook](docs/jsonld-sync-system.md)
- [Per-business synchronization report](jsonld-sync-status.json)
- [GitHub Actions history](https://github.com/WikiAI-hu/wikiai-entities/actions/workflows/sync-deep-jsonld.yml)


## Retired personal-domain migration (2026-10-23)

The former personal domain `varhelyicsanad.hu` has been retired and redirected. Current public professional Person IDs:

- Várhelyi Csanád: `https://www.wikiai.hu/szakertok/varhelyi-csanad/#person` — https://www.wikiai.hu/szakertok/varhelyi-csanad/
- Várhelyi Viktória: `https://www.wikiai.hu/szakertok/varhelyi-viktoria/#person` — https://www.wikiai.hu/szakertok/varhelyi-viktoria/
- WikiAI.hu organization: `https://www.wikiai.hu/#organization` (distinct from either person).

**Important:** business `entities/*.jsonld` files and selected `entities/*.md` and `wikiai/people/*.md` documents are WordPress-generated mirrors. Do not perform a GitHub-only search-and-replace on managed mirrors: it can break checksum guards or be reverted at the next synchronization. Update the relevant WordPress/HFCM source first, then allow the audited synchronization to produce updated GitHub snapshots. The first-party `wikiai/wikiai-hu.jsonld` snapshot is likewise checked against the live HFCM graph.

See [the migration runbook](docs/retired-domain-migration.md) for exact scope and next steps.
