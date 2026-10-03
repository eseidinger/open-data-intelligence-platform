# Open Data Intelligence Platform

## 1. Overview

The **Open Data Intelligence Platform (ODIP)** is an experimental software and data engineering platform for ingesting, transforming, storing, analyzing, and exploring heterogeneous public datasets.

The project provides a domain-independent architecture for experimenting with modern data engineering technologies and AI-assisted analytics.

Instead of focusing on a single database, processing framework, or AI technology, the platform provides common abstractions that allow different technical approaches to be implemented and compared.

The platform is designed around four major concerns:

1. **Data Engineering** – ingestion, validation, transformation, enrichment, and historization of heterogeneous datasets.
2. **Data Architecture** – evaluation of relational, document, graph, search, vector, and analytical storage technologies.
3. **Data Intelligence** – analytical services for querying, correlating, and exploring datasets.
4. **AI Integration** – semantic search, RAG, tool-enabled LLMs, and agentic data analysis.

Concrete datasets and domains are implemented as **use cases on top of the generic platform** rather than being embedded into the core architecture.

---

# 2. Project Goals

The project has several goals.

### Build a reusable data engineering architecture

The platform should support heterogeneous data sources such as:

- REST APIs
- CSV
- JSON
- XML
- Parquet
- streaming data
- documents
- external databases

The internal architecture should remain independent from specific data providers.

### Compare alternative data architectures

Different storage and processing technologies can be evaluated using identical or comparable datasets.

Examples include:

- PostgreSQL vs. document databases
- PostgreSQL JSONB vs. MongoDB
- PostgreSQL FTS vs. OpenSearch
- pgvector vs. dedicated vector databases
- PostgreSQL/Apache AGE vs. Neo4j
- PostgreSQL analytics vs. DuckDB
- database storage vs. Parquet-based analytical storage

### Explore AI-assisted data engineering

AI should not merely provide a chatbot interface.

LLMs and agents can participate in several stages of the data lifecycle:

- dataset discovery
- schema interpretation
- metadata generation
- data quality analysis
- schema drift detection
- semantic enrichment
- query generation
- analytical reasoning
- report generation

### Provide reproducible experiments

Architectural decisions should be backed by reproducible experiments.

The platform therefore serves both as an application and as an **experimental environment for data architecture research**.

---

# 3. Conceptual Architecture

The platform follows a layered architecture.

```text
                         ┌───────────────────────────┐
                         │          Users            │
                         └─────────────┬─────────────┘
                                       │
                         ┌─────────────▼─────────────┐
                         │     Web / API Clients     │
                         └─────────────┬─────────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │       Intelligence Services         │
                    │                                     │
                    │ Search │ Analytics │ AI │ Reporting │
                    └───────────────┬─────────────────────┘
                                    │
                    ┌───────────────▼─────────────────────┐
                    │        Data Access Layer            │
                    │                                     │
                    │ SQL │ Graph │ Search │ Vector │ OLAP│
                    └───────────────┬─────────────────────┘
                                    │
        ┌───────────────────────────▼───────────────────────────┐
        │                    Data Platform                      │
        │                                                       │
        │ PostgreSQL │ Object Storage │ Search │ Graph │ Vector │
        └───────────────────────────┬───────────────────────────┘
                                    │
                    ┌───────────────▼─────────────────────┐
                    │      Transformation Pipeline        │
                    │                                     │
                    │ Validate → Normalize → Enrich       │
                    │              → Curate               │
                    └───────────────┬─────────────────────┘
                                    │
                    ┌───────────────▼─────────────────────┐
                    │          Ingestion Layer            │
                    │                                     │
                    │ Batch │ Streaming │ Files │ APIs    │
                    └───────────────┬─────────────────────┘
                                    │
              ┌─────────────────────▼─────────────────────┐
              │              External Sources             │
              │                                           │
              │ APIs │ Open Data │ Files │ Documents      │
              └───────────────────────────────────────────┘
```

---

# 4. Core Architecture

## 4.1 Data Source

A `DataSource` describes an external source of information.

It contains information such as:

- source type
- location
- access mechanism
- update frequency
- schema information
- licensing
- ownership
- metadata

The abstraction should not assume whether the source provides CSV files, REST APIs, streaming events, or another mechanism.

---

## 4.2 Dataset

A `Dataset` represents a logical collection of information inside the platform.

A dataset may have multiple physical representations.

For example:

```text
EnergyPriceDataset

Raw:
    JSON objects

Normalized:
    relational records

Analytical:
    Parquet files

Search:
    OpenSearch documents

AI:
    vector embeddings
```

This distinction is important because the platform deliberately avoids assuming that every workload should be served by the same storage technology.

---

## 4.3 Data Pipeline

Data pipelines transform external data into usable datasets.

```text
Source
   │
   ▼
Extract
   │
   ▼
Raw Storage
   │
   ▼
Validate
   │
   ▼
Normalize
   │
   ▼
Enrich
   │
   ▼
Curated Dataset
   │
   ├──► Operational Store
   ├──► Analytical Store
   ├──► Search Index
   ├──► Graph Projection
   └──► Vector Index
```

Every transformation should be observable and reproducible.

Pipeline executions therefore produce metadata describing:

- execution time
- source version
- input records
- output records
- rejected records
- validation errors
- transformations
- data quality metrics

---

# 5. Data Architecture

The initial implementation should deliberately use a small number of technologies.

## PostgreSQL

PostgreSQL acts as the primary operational data store.

It stores:

- dataset metadata
- source metadata
- pipeline metadata
- normalized datasets
- experiment definitions
- experiment results

PostgreSQL extensions can subsequently provide additional capabilities:

- JSONB
- full-text search
- pgvector
- Apache AGE
- time-series extensions

This establishes PostgreSQL as the baseline against which specialized technologies can be evaluated.

## Object Storage

An S3-compatible object store stores immutable or analytical data artifacts.

Examples:

```text
/raw
/normalized
/curated
/analytics
/exports
```

Typical formats include:

- JSON
- CSV
- Parquet

This allows experiments with data lake and lakehouse concepts without requiring a large distributed infrastructure.

## DuckDB

DuckDB provides an analytical execution environment.

It can directly query Parquet datasets stored in object storage.

This enables an interesting comparison:

```text
PostgreSQL
    vs.
PostgreSQL + DuckDB
    vs.
Parquet + DuckDB
```

for analytical workloads.

---

# 6. Optional Specialized Data Stores

Specialized technologies should be introduced through adapters rather than becoming mandatory platform dependencies.

```text
             Data Access API
                    │
          ┌─────────┴─────────┐
          │                   │
    StorageAdapter      QueryAdapter
          │                   │
    ┌─────┼─────┐       ┌─────┼─────┐
    │     │     │       │     │     │
   PG   Mongo  S3      SQL  Graph Search
```

Possible implementations include:

### MongoDB

Used for experiments involving highly variable document structures.

### OpenSearch

Used for search-oriented workloads.

### Neo4j / Apache AGE

Used for relationship-heavy datasets and graph analytics.

### Vector Stores

Used for semantic retrieval and RAG.

The architecture therefore separates the **logical dataset model from its physical representation**.

---

# 7. AI Architecture

AI functionality is provided through a separate intelligence layer.

```text
                     User
                       │
                       ▼
                Analytics Agent
                       │
               ┌───────┴────────┐
               │                │
         Planning / LLM     Data Catalog
               │
      ┌────────┼──────────┐
      │        │          │
      ▼        ▼          ▼
   SQL Tool  Search    Vector Search
      │       Tool         Tool
      │        │           │
      └────────┼───────────┘
               │
               ▼
         Data Platform
```

The AI system should interact with the platform through explicit tools rather than receiving unrestricted database access.

Possible tools include:

```text
listDatasets()

describeDataset()

getDatasetSchema()

queryDataset()

searchDocuments()

semanticSearch()

executeAnalytics()

getDataQualityReport()

getDatasetLineage()
```

These tools can later be exposed through **MCP servers**, allowing different agents and AI clients to interact with the platform.

---

# 8. AI-Assisted Data Engineering

AI can also operate on the ingestion side.

For example, when a new dataset is registered:

```text
New Data Source
       │
       ▼
Schema Inspection
       │
       ▼
AI Metadata Generation
       │
       ├──► field descriptions
       ├──► semantic types
       ├──► relationships
       └──► quality expectations
       │
       ▼
Human Review
       │
       ▼
Pipeline Configuration
```

The important design principle is that AI-generated configurations remain explicit artifacts.

AI therefore assists data engineering instead of hiding it.

---

# 9. Technology Architecture

The project can deliberately use several languages, with each language having a clearly defined responsibility.

## Kotlin / Spring Boot

Kotlin and Spring Boot provide the main application and platform services.

Responsibilities:

- dataset catalog
- metadata management
- APIs
- pipeline orchestration
- experiment management
- authorization
- storage abstractions

This provides a substantial Kotlin/Spring component instead of using Spring merely for demonstration purposes.

## Python

Python provides data engineering, analytics, ML, and AI functionality.

Responsibilities:

- transformations
- data profiling
- statistical analysis
- ML experiments
- embeddings
- RAG
- agent implementations
- AI-assisted data engineering

Typical libraries could include:

```text
Pandas
Polars
PyArrow
DuckDB
scikit-learn
LangChain / alternative agent frameworks
```

## TypeScript

TypeScript is used for the user-facing application.

Angular can initially provide the main frontend.

Responsibilities:

- dataset browser
- pipeline monitoring
- data quality visualization
- experiment comparison
- interactive analytics
- AI interface

React implementations can later be added for selected reusable visualization components if comparing frontend approaches remains useful.

---

# 10. Service Architecture

The initial system should **not** start as a large microservice landscape.

A reasonable first architecture is:

```text
┌───────────────────────┐
│      Angular UI       │
└───────────┬───────────┘
            │
┌───────────▼───────────┐
│ Kotlin / Spring API   │
│                       │
│ Catalog               │
│ Dataset Management    │
│ Pipeline Management   │
│ Experiment Management │
└───────┬─────────┬─────┘
        │         │
        │         ▼
        │   ┌──────────────┐
        │   │ Python Worker│
        │   │              │
        │   │ ETL          │
        │   │ Analytics    │
        │   │ AI           │
        │   └──────┬───────┘
        │          │
        ▼          ▼
┌────────────────────────┐
│      Data Platform     │
│                        │
│ PostgreSQL             │
│ Object Storage         │
│ DuckDB                 │
└────────────────────────┘
```

Kafka or another event broker can be introduced later when experiments require asynchronous processing or streaming.

---

# 11. Experiment Framework

A central feature of the project is an explicit experiment model.

An experiment describes:

```yaml
name: analytical-query-comparison

dataset: energy-data

implementations:
  - postgres
  - duckdb-parquet

workload:
  query-set: analytics-v1

metrics:
  - execution-time
  - memory
  - storage-size
  - ingestion-time
```

The platform executes the workload against different implementations and stores the results.

This turns technology comparisons into reproducible experiments rather than informal benchmarks.

---

# 12. Initial Use Case: Energy Intelligence

The first reference implementation could combine public datasets concerning:

- electricity generation
- renewable energy
- electricity prices
- weather
- energy consumption

This creates interesting correlations between independent datasets.

Example questions include:

> How does renewable generation correlate with electricity prices?

> How strongly does temperature correlate with energy consumption?

> Which periods contain unusual combinations of weather, generation, and prices?

> Find historical situations similar to a given energy market event.

The use case naturally combines:

- time-series data
- relational data
- external APIs
- analytical workloads
- anomaly detection
- semantic metadata
- AI-assisted analysis

The energy domain is nevertheless only a demonstrator. The platform architecture itself remains domain-independent.

---

# 13. Relationship to the Developer Platform

The two portfolio projects address complementary concerns.

```text
Developer Platform
        │
        │ provides
        ▼
Compute / Deployment / Persistence
Monitoring / Security / Operations
        │
        ▼
Open Data Intelligence Platform
        │
        │ provides
        ▼
Data Engineering / Analytics
Data Architecture / AI
```

The Developer Platform answers:

> **How can applications and their infrastructure be provisioned and operated?**

The Open Data Intelligence Platform answers:

> **How can heterogeneous data be transformed into reliable, searchable, analytical, and AI-accessible information?**

The Open Data Intelligence Platform can eventually become one of the first substantial applications deployed and operated through the Developer Platform.

---

# 14. Development Roadmap

## Phase 1 – Data Foundation

Implement:

- Spring Boot/Kotlin backend
- PostgreSQL
- object storage
- dataset catalog
- source registration
- Python ingestion worker
- basic pipelines
- first public dataset
- Angular dataset browser

Goal:

**Source → ingestion → transformation → storage → API → UI**

## Phase 2 – Analytical Platform

Add:

- Parquet
- DuckDB
- data profiling
- quality metrics
- historical datasets
- analytical queries
- visualization

## Phase 3 – Architecture Experiments

Introduce the experiment framework and compare:

- PostgreSQL vs. DuckDB
- JSONB vs. document-oriented storage
- PostgreSQL FTS vs. OpenSearch
- pgvector vs. specialized vector storage
- relational vs. graph representations

## Phase 4 – AI Intelligence

Add:

- embeddings
- semantic dataset search
- RAG
- natural-language analytics
- tool-enabled analytics agent
- MCP interfaces

## Phase 5 – AI Data Engineering

Add:

- automatic metadata generation
- schema interpretation
- data quality suggestions
- schema drift analysis
- relationship discovery
- AI-assisted pipeline creation

---

# 15. Portfolio Value

The project demonstrates several engineering disciplines within one coherent architecture:

**Software Engineering**

Kotlin, Spring Boot, Python, TypeScript, APIs, modular architecture and testing.

**Data Engineering**

ETL/ELT, pipelines, schemas, data quality, lineage, historization, Parquet and object storage.

**Data Architecture**

Relational, document, search, graph, vector and analytical architectures.

**AI Engineering**

RAG, embeddings, agents, tool use, MCP and AI-assisted data engineering.

**Platform Engineering**

Containers, Kubernetes, observability, CI/CD and integration with the Developer Platform.

The result is therefore not simply an AI application or a collection of database benchmarks.

It is a **reference architecture for exploring how modern software engineering, data engineering, data architecture, and AI engineering interact in a real application.**