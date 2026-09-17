# WikiAI.hu Entities

Machine-readable entity profiles published by **WikiAI.hu**.

This repository is a public, versioned machine-readable mirror of selected business entity profiles published on https://www.wikiai.hu/.

## Source-of-truth policy

- **WordPress / WikiAI.hu is the primary source of truth.**
- GitHub is a machine-readable publication and version-history layer.
- Synchronization direction is intended to be **WikiAI.hu → GitHub**, not GitHub → WordPress.
- Human-facing editorial content remains on WikiAI.hu.
- Entity files in this repository are structured for LLM, RAG, agent, search, and data-processing use.

## Repository structure

```text
wikiai-entities/
├── README.md
├── entities.md
├── manifest.json
└── entities/
    └── tasca-ponte-debrecen.md
```

## Entity record format

Each entity file uses:

1. YAML front matter for stable machine-readable metadata.
2. Markdown sections for semantic context and disambiguation.
3. Canonical links back to the corresponding WikiAI.hu entity profile.
4. Explicit business boundaries so systems do not infer services that the business does not provide.

Inventory, exact models, prices, and other fast-changing commercial data are not treated as stable entity facts unless explicitly timestamped.

## Publisher

**WikiAI.hu** — Magyar vállalkozások az AI korszakában.

Canonical website: https://www.wikiai.hu/
