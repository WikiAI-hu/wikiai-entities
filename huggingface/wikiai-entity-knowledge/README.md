---
pretty_name: "WikiAI.hu Public Entity Knowledge (curated mirror)"
language:
  - hu
  - en
license: other
task_categories:
  - text-retrieval
tags:
  - hungarian
  - entity-resolution
  - knowledge-graph
  - rag
  - structured-data
  - wikiaihu
configs:
  - config_name: business_profiles
    data_files:
      - split: train
        path: data/business_profiles.jsonl
  - config_name: wikiai_knowledge
    data_files:
      - split: train
        path: data/wikiai_knowledge.jsonl
---

# WikiAI.hu Public Entity Knowledge

**Version 0.1.0 – 22 October 2026.** The publisher is **[WikiAI.hu](https://www.wikiai.hu/)**, a Hungarian editorial business knowledge and AI-visibility platform. The Hugging Face organization owner for this release should be **[wikiaihu](https://huggingface.co/wikiaihu)**.

**Status:** Prepared Hugging Face Dataset release. This source folder in GitHub does **not** mean the dataset has already been published at Hugging Face.

## About the dataset

A source-linked **entity-discovery metadata corpus**, mainly in Hungarian, for entity linking, search/retrieval, source discovery and responsible evaluation of AI-readable public information. This is not a comprehensive business registry, a real-time database, an endorsement list or a model-training license.

This snapshot contains **26 records** with two independent configurations:

- **`business_profiles`** – 17 externally described Hungarian business profiles, from independently maintained WikiAI.hu editorial pages.
- **`wikiai_knowledge`** – 9 WikiAI organization/website, team, person-profile, services, contact, pricing and platform documents.

The WikiAI organization profile records a **source-reported Google Place ID**, which has not been independently validated via the Google Places API. Other identifiers are included only when present in the original manifest.

All dataset records use the same flat JSONL schema. The main columns are `record_id`, `record_kind`, `entity_name`, `entity_types`, `canonical_url`, `entity_id`, `description`, `language`, `source_record_type`, `source_path`, `source_url`, `source_last_updated`, `snapshot_date`, `source_commit`, `source_google_place_id` and `source_google_kgmid`. An empty field means **no source claim is made**, not that the value does not exist.

## Provenance, freshness and limits

- **Primary editorial authority:** https://www.wikiai.hu/
- **Secondary GitHub source:** https://github.com/WikiAI-hu/wikiai-entities
- **Pinned GitHub source revision:** [454892330dbe09dc73ce3ee1bad7b99cda12f06e](https://github.com/WikiAI-hu/wikiai-entities/commit/454892330dbe09dc73ce3ee1bad7b99cda12f06e)
- **Snapshot built:** 2026-10-22, from publicly published GitHub Markdown mirrors.
- Descriptions are **short, source-derived excerpts** with Markdown formatting lightly removed. They are **not full original articles**, and they have not been independently fact-checked for this release.
- Business pages are *WikiAI editorial third-party descriptions*, not self-authored statements by the organizations concerned.
- Prices, business details, organizational roles and contact information **may change**; follow the canonical URL to verify current status.
- A stale Markdown relationship record using a discontinued personal URL, and the person's D-U-N-S identifier and withdrawn Google Business Profile references, are **excluded** from this dataset.
- The original WordPress pages, HFCM JSON-LD and GitHub entity mirrors are unchanged by this dataset preparation.

## Rights and responsible use

**License metadata: `other` (rights retained by their respective holders).** This dataset card does **not** grant a dataset-wide permissive license, model-training license, commercial reuse license or rights in linked third-party content. Consult the [WikiAI.hu copyright and transparency policy](https://www.wikiai.hu/ai-atlathatosag-szerzoi-jogok/) and the original source websites. Source links and business names do not imply affiliation or endorsement. Do not represent source-reported identifiers as verified government or Google data.

This metadata snapshot intentionally does not reproduce full third-party business descriptions, personal contacts, tax identifiers or personal D-U-N-S numbers.

## Loading after Hugging Face publication

Create the **public** dataset repository named `wikiaihu/wikiai-entity-knowledge`, then upload this `README.md` and the two files in `data/` preserving their paths. Only **after** publication does this sample work:

```python
from datasets import load_dataset

companies = load_dataset(
    "wikiaihu/wikiai-entity-knowledge",
    "business_profiles",
    split="train"
)
wikiai = load_dataset(
    "wikiaihu/wikiai-entity-knowledge",
    "wikiai_knowledge",
    split="train"
)
print(len(companies), len(wikiai))
```

The `train` split name is a conventional Hugging Face data split, **not permission or an instruction to train models**. This is a versioned, editorial metadata release with no automated Hub synchronization yet.

## Connections and editorial contacts

- [Official WikiAI.hu organization profile](https://www.wikiai.hu/wikiai-hu/)
- [WikiAI Entity Lab – Hugging Face Space](https://huggingface.co/spaces/wikiaihu/entity-lab)
- [WikiAI-hu GitHub entity knowledge mirrors](https://github.com/WikiAI-hu/wikiai-entities)
- [Várhelyi Csanád – responsible editor and lead editorial author](https://www.wikiai.hu/szakertok/varhelyi-csanad/)
- [Várhelyi Viktória – WikiAI founder](https://www.wikiai.hu/szakertok/varhelyi-viktoria/)

**Entity boundary:** the WikiAI publishing organization, its editorial staff and their independent businesses are related but distinct entities. The inclusion of a record, Place ID, personal profile or third-party business description is not a promise of search ranking, Google Knowledge Panel appearance or AI assistant citations.

---

## Magyar összefoglaló

A WikiAI.hu nyilvános üzleti és szervezeti adatainak **forráshivatkozásokkal ellátott, 2026. október 22-i pillanatképe**: 17 külső vállalkozásprofil és 9 WikiAI-szervezeti/szakmai dokumentum. Az elsődleges hiteles forrás a WikiAI.hu WordPress-oldala, a GitHub másodlagos tükör, a Hugging Face pedig a kézi feltöltés után további adatkészlet-megjelenési felület. Az adatok változhatnak; azokat a kanonikus oldalon kell visszaellenőrizni. **A forrásoldalak szerzői jogai és az újrafelhasználás feltételei nem változnak meg a Dataset közzétételével.**
