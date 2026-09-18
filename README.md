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
        └── molnar-andras.md
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
