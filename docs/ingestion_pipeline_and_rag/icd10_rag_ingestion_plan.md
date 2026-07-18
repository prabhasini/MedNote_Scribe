# ICD-10 (ClaML) → RAG Ingestion Design

**Source format:** WHO ClaML XML, `ClaML version="2.0.0"`, dataset `icd10_20210322`
**Goal:** Turn the flat `<Class>` record list into a retrieval corpus usable by an agent, with reliable code-level grounding.

---

## 1. Source Schema Recap

The file is **not** a nested ICD-10 tree — it's a flat list of `<Class>` elements under `<ClaML>`, with parent/child relationships expressed via `SuperClass`/`SubClass` code references rather than XML nesting.

```xml
<Class code="G44.2" kind="category">
    <SuperClass code="G44"/>
    <Rubric kind="preferred">
        <Label xml:lang="en">Tension-type headache</Label>
    </Rubric>
    <Rubric kind="inclusion">
        <Label xml:lang="en">Chronic tension-type headache</Label>
    </Rubric>
</Class>
```

| Element / attribute | Meaning |
|---|---|
| `Class@code` | ICD-10 identifier, e.g. `G44.2` |
| `Class@kind` | `chapter`, `block`, or `category` |
| `SuperClass@code` | Parent code |
| `SubClass@code` | Child code |
| `Rubric@kind` | `preferred`, `preferredLong`, `inclusion`, `exclusion`, `note`, `coding-hint`, `definition`, `introduction`, `footnote`, `text`, `modifierlink` |
| `Label` | Human-readable text (`xml:lang="en"`) |
| `Reference` | Cross-reference to another code/range |

Because hierarchy is reference-based, **the parser must do a two-pass resolution** before anything downstream (chunking, embedding) can happen correctly.

---

## 2. Pipeline Overview

```mermaid
flowchart TD
    A["ICD10.xml (ClaML)"] --> B["Pass 1: Parse\nBuild code -> Class dict"]
    B --> C["Pass 2: Resolve hierarchy\nAttach chapter/block/parent chain"]
    C --> D["Resolve cross-references\ncode -> (code, label) pairs"]
    D --> E["Normalize to JSONL\n(one record per Class)"]
    E --> F["Chunking\nbuild retrieval documents"]
    F --> G["Embedding\ndense vector per chunk"]
    G --> H1["Vector DB\n(dense search)"]
    G --> H2["Keyword / BM25 index\n(exact terminology)"]
    E --> H3["Relational / metadata store\n(exact code + prefix lookup)"]
    H1 --> I["Hybrid Retrieval Layer"]
    H2 --> I
    H3 --> I
    I --> J["RAG Agent"]
```

**Why the two-pass parse matters:** a leaf category's context (which chapter/block it belongs to) is what disambiguates it — the same term can appear under multiple chapters (e.g. "burn" under injury vs. late-effect chapters). Ancestor resolution has to happen before chunk text is generated, not at query time.

---

## 3. Hierarchy Resolution Example

```mermaid
graph TD
    Ch["Chapter VI\nDiseases of the nervous system"] --> Bl["Block G40-G47\nEpisodic and paroxysmal disorders"]
    Bl --> Cat["Category G44\nOther headache syndromes"]
    Cat --> Sub["Category G44.2\nTension-type headache"]
    Sub -->|Rubric: inclusion| Inc1["Chronic tension-type headache"]
    Sub -->|Rubric: inclusion| Inc2["Episodic tension-type headache"]
```

This resolved chain (`chapter → block → parent → self`) gets denormalized onto every leaf node's JSON record and, critically, into the **rendered chunk text itself** — not just metadata — because embedding models retrieve better when disambiguating context is inline rather than external.

---

## 4. Intermediate Format: JSONL

XML is a poor RAG substrate (relationships live in attributes, no natural chunk boundary). Convert once to JSONL — this becomes the **source of truth** you re-embed from whenever the embedding model or chunking strategy changes, without re-parsing XML.

```json
{
  "code": "G44.2",
  "kind": "category",
  "chapter": {"code": "VI", "label": "Diseases of the nervous system"},
  "block": {"code": "G40-G47", "label": "Episodic and paroxysmal disorders"},
  "parent": {"code": "G44", "label": "Other headache syndromes"},
  "preferred": "Tension-type headache",
  "inclusions": ["Chronic tension-type headache", "Episodic tension-type headache"],
  "exclusions": [],
  "notes": [],
  "definition": null,
  "cross_references": [],
  "children": []
}
```

---

## 5. Chunking Strategy

**Unit of chunking = one `Class` record**, rendered as structured text. ICD-10 doesn't benefit from token-window/sliding-window splitting — each code is already a self-contained semantic unit, and arbitrary splitting would sever the code↔label↔rubric relationship needed for grounding.

```mermaid
flowchart LR
    subgraph Record["Class Record: G44.2"]
        Code["code"]
        Anc["ancestor chain\n(chapter, block, parent)"]
        Pref["preferred label"]
        Inc["inclusions"]
        Exc["exclusions"]
        Note["notes / definitions"]
    end

    Code --> Embed["Embedded chunk text\n(code + ancestors + preferred + inclusions)"]
    Anc --> Embed
    Pref --> Embed
    Inc --> Embed

    Exc --> Payload["Metadata payload only\n(displayed, NOT embedded)"]
    Note --> LongCheck{"Unusually long\nfree text?"}
    LongCheck -->|No| Embed
    LongCheck -->|Yes| SubChunk["Separate child chunk\nG44.2#note-1\nlinked via parent_code metadata"]
```

**Rendered chunk template:**

```
Code: G44.2
Category: Other headache syndromes (G44)
Block: Episodic and paroxysmal disorders (G40-G47)
Chapter: Diseases of the nervous system (VI)

Tension-type headache

Includes: Chronic tension-type headache; Episodic tension-type headache
```

Key rules:

- **Prepend ancestor context** into the embedded text itself, not just metadata.
- **Exclude `exclusion` rubrics from the embedding text.** Embedding "Excludes: migraine" into the same vector as "Tension-type headache" risks pulling that chunk toward migraine-related queries. Keep exclusions in the payload for display only.
- **Embed chapters and blocks too**, tagged with `kind: chapter` / `kind: block` in metadata — so a query like "what falls under episodic and paroxysmal disorders" can hit the block chunk, then fan out to children via metadata filter rather than semantic search alone.
- **Split only unusually long rubrics** (rare chapter-level notes/definitions) into their own linked sub-chunk; don't apply a blanket splitter to the whole corpus.
- **One vector per chunk**, roughly one per code — the corpus stays small (tens of thousands of vectors), so this is cheap regardless of DB choice.

---

## 6. Embedding Model

| Option | Trade-off |
|---|---|
| Domain-tuned (SapBERT, PubMedBERT, BioLORD-style) | Better at matching lay symptom phrasing to formal diagnostic terms — worth it since ICD-10 retrieval is fundamentally an entity-linking problem. |
| General-purpose (OpenAI text-embedding-3, Voyage-3, Cohere embed-v4) | Simpler ops, weaker on subtle clinical synonymy. Gap narrows if you exploit `inclusion` rubrics already in the corpus as pseudo-synonyms. |

---

## 7. Vector Database Choice

Constraints that matter more than raw ANN benchmarks at this scale:
- **Small corpus** (tens of thousands of vectors) — nearly any DB is fast enough.
- **Heavy metadata filtering** — chapter, block, code prefix, kind.
- **Exact/prefix lookup is a large fraction of real traffic** ("what is code X", "codes starting with G44") — this is not a vector problem, so pure-vector-only DBs are the wrong sole tool.

| Option | Fit |
|---|---|
| **Qdrant** *(top pick)* | Strong payload/metadata filtering, native hybrid (dense + BM25/sparse) support, easy self-host or cloud, comfortable at this scale. |
| **pgvector (Postgres)** *(top pick)* | Everything in one system: exact/prefix code lookup via SQL, relational joins for ancestor chains, transactional re-ingestion, and vector search together. Best if you don't want a separate vector service. |
| **Weaviate** | Good native hybrid (BM25 + vector fusion), schema-based, similar filtering story to Qdrant. |
| **Chroma** | Great for fast prototyping, weaker for production-grade filtering/scale. |
| **Pinecone / managed** | Fine if you don't want to operate infra; loses SQL-join convenience for hierarchy traversal. |

**Recommendation:** Qdrant or pgvector, paired with a hybrid retrieval layer — pure semantic-only search will underperform on a controlled vocabulary like ICD-10.

```mermaid
flowchart TD
    Q["User Query"] --> R1{"Looks like a code\nor code prefix?"}
    R1 -->|Yes| Exact["Exact / prefix match\n(SQL LIKE or regex)"]
    R1 -->|No| Fan["Fan out in parallel"]
    Fan --> BM25["Keyword / BM25 search\n(preferred + inclusions)"]
    Fan --> Dense["Dense vector search"]
    Exact --> Merge["Merge results"]
    BM25 --> Merge
    Dense --> Merge
    Merge --> Rerank["Rerank\n(RRF or cross-encoder)"]
    Rerank --> Out["Top-k chunks -> Agent context"]
```

---

## 8. Storage Schema (per vector record)

```json
{
  "id": "G44.2",
  "vector": [ ... ],
  "payload": {
    "code": "G44.2",
    "kind": "category",
    "preferred": "Tension-type headache",
    "chapter_code": "VI",
    "chapter_label": "Diseases of the nervous system",
    "block_code": "G40-G47",
    "parent_code": "G44",
    "inclusions": ["Chronic tension-type headache", "..."],
    "exclusions": [],
    "has_children": false,
    "source_version": "icd10_20210322"
  }
}
```

Index as filterable fields: `code`, `kind`, `chapter_code`, `block_code`, `parent_code`.

---

## 9. Versioning & Re-ingestion

WHO revises ICD-10 periodically (this file itself carries `icd10_20210322`, `2019-covid-expanded`). Practices:

- Store `source_version` on every record.
- Make ingestion **idempotent and diffable**: re-parse XML → regenerate JSONL → diff against the previous JSONL by `code` → upsert only changed records into the vector DB, rather than a full reload each time.

---

## 10. Summary

```mermaid
flowchart LR
    XML["ClaML XML"] -->|two-pass parse| JSONL["JSONL\n(1 record / Class)"]
    JSONL -->|render + chunk| Chunks["Chunk text\n(code + ancestors + preferred + inclusions)"]
    Chunks -->|embed| Vec["Dense vectors"]
    Vec --> DB[("Qdrant / pgvector")]
    JSONL --> Meta[("Metadata / exact-match store")]
    DB --> Hybrid["Hybrid Retrieval\n(exact + BM25 + dense + rerank)"]
    Meta --> Hybrid
    Hybrid --> Agent["RAG Agent"]
```