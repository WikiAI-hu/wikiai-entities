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

## Published software project — WikiAI Schema Peek

**[WikiAI Schema Peek 1.1.0](https://www.wikiai.hu/wikiai-schema-peek/)** is a free Hungarian–English Chrome extension and a separate browser-based demonstration for inspecting JSON-LD, Schema.org vocabulary and declared entity relationships. Csanád Várhelyi conceived, initiated and professionally directed the WikiAI.hu software project.

The Chrome Web Store listing and the Product Hunt product launch became publicly available on 27 November 2026.

| Official resource | Reference |
| --- | --- |
| Product documentation | [WikiAI Schema Peek](https://www.wikiai.hu/wikiai-schema-peek/) |
| Chrome installation | [Chrome Web Store](https://chrome.google.com/webstore/detail/glegjhmdanhbloojggfdphgohgfmmheh) |
| Product introduction | [Product Hunt](https://www.producthunt.com/products/wikiai-schema-peek?launch=wikiai-schema-peek) |
| Source and developer documentation | [WikiAI-hu/wikiai-schema-peek](https://github.com/WikiAI-hu/wikiai-schema-peek) |
| Online demonstration | [Hugging Face Space](https://huggingface.co/spaces/wikiaihu/wikiai-schema-peek) |
| Separate demo source | [Versioned publisher source](https://github.com/WikiAI-hu/hf-entity-lab-publisher/tree/main/schema-peek-space) |
| English technical article | [WikiAI Schema Peek — a practical JSON-LD and Entity Engineering tool](https://www.wikiai.hu/wikiai-schema-peek-a-practical-json-ld-and-entity-engineering-tool-for-chrome/) |
| License | [Free Use / Source-Available License 1.0](https://github.com/WikiAI-hu/wikiai-schema-peek/blob/main/LICENSE.md) |

**Entity boundaries:** the canonical software identifier is `https://www.wikiai.hu/wikiai-schema-peek/#software`. The creator is identified by `https://www.wikiai.hu/szakertok/varhelyi-csanad/#person`, and the publishing organization by `https://www.wikiai.hu/#organization`. The software, person, organization, source-code repository and online demo have distinct roles. The Chrome extension inspects the active page on demand; the demo processes pasted JSON-LD locally. Neither measures search rankings or AI recommendations. Public distribution is not independent validation or platform endorsement. The source-available software license is distinct from the CC BY-SA 3.0 license of its adapted Schema.org vocabulary.

This project section is documentation pointing to the official product resources. It does not create a second canonical product profile, and it does not replace the validated WordPress-derived machine-readable mirrors.

## Structured JSON-LD mirrors

The WordPress pages and their active HFCM structured data are the first-party source of truth. The versioned first-party JSON-LD mirrors are maintained by the [first-party HFCM audit and mirror workflow](https://github.com/WikiAI-hu/wikiai-entities/actions/workflows/audit-official-jsonld.yml), which validates the live canonical HTML before updating a snapshot. They are not replacements for the canonical pages.

- [WikiAI.hu official platform JSON-LD](wikiai/wikiai-hu.jsonld) — https://www.wikiai.hu/wikiai-hu/
- [Munkatársaink team JSON-LD](wikiai/team.jsonld) — https://www.wikiai.hu/szakertok/
- [Simon Imre person profile JSON-LD](wikiai/people/simon-imre.jsonld) — https://www.wikiai.hu/szakertok/simon-imre/
- [Várhelyi Csanád deep Person/ProfilePage JSON-LD snapshot](wikiai/people/varhelyi-csanad.jsonld) — https://www.wikiai.hu/szakertok/varhelyi-csanad/ (automated validated live-source mirror)

Simon Imre and INF-GROUP Kft. are external IT infrastructure partners, not internal WikiAI.hu employees or owners.

## Automated deep JSON-LD mirror

The published business profiles in WordPress's **Vállalkozások** category are mirrored to GitHub in two formats:

- Markdown by the existing WikiAI GitHub Entity Sync WordPress plugin.
- Full Schema.org JSON-LD by a scheduled GitHub Actions job that validates the **publicly rendered HFCM source** before updating the GitHub mirror.

The JSON-LD job is monitored per business, supports historic Schema.org variants, runs hourly and after manifest updates, and refuses destructive or conflicting changes. The WikiAI.hu first-party platform profile is a separate exception.

- [Operational runbook](docs/jsonld-sync-system.md)
- [Per-business synchronization report](jsonld-sync-status.json)
- [GitHub Actions history](https://github.com/WikiAI-hu/wikiai-entities/actions/workflows/sync-deep-jsonld.yml)


## Active personal reference domain (2026-11-25)

The October 2026 redirect migration was reversed. https://www.varhelyicsanad.hu/ and https://www.varhelyicsanad.hu/en/ are active Hungarian and English LLM-first personal reference pages. WikiAI.hu is the primary source for its own editorial profile and organizational information. Preserve the stable WikiAI identifiers and the explicitly connected personal-domain Person and business identifiers; do not globally rewrite either domain. Current WikiAI professional Person IDs:

- Várhelyi Csanád: `https://www.wikiai.hu/szakertok/varhelyi-csanad/#person` — https://www.wikiai.hu/szakertok/varhelyi-csanad/
- Várhelyi Viktória: `https://www.wikiai.hu/szakertok/varhelyi-viktoria/#person` — https://www.wikiai.hu/szakertok/varhelyi-viktoria/
- WikiAI.hu organization: `https://www.wikiai.hu/#organization` (distinct from either person).

**Important:** business `entities/*.jsonld` files and selected `entities/*.md` and `wikiai/people/*.md` documents are WordPress-generated mirrors. Do not perform a GitHub-only search-and-replace on managed mirrors: it can break checksum guards or be reverted at the next synchronization. Update the relevant WordPress/HFCM source first, then allow the audited synchronization to produce updated GitHub snapshots. The first-party JSON-LD workflow independently checks and mirrors the live organization, team and existing expert-profile graphs. Changed Markdown checksums trigger a fresh validated WordPress read, not blind checksum acceptance.

See [the historical migration record and current identity policy](docs/retired-domain-migration.md) for scope.
