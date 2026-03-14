# Medical Education Tutor

A precision medical and nursing education agent powered by OpenJarvis. Uses RAG retrieval over your indexed curriculum, a structured medical knowledge graph, and custom clinical reasoning tools to provide personalized medical education.

## Features

- **RAG-powered curriculum Q&A** — index entire textbooks and get cited answers
- **Medical knowledge graph** — structured entity-relation graph for diseases, medications, symptoms, and interventions
- **NCLEX-RN / USMLE exam generation** — practice questions with detailed rationales
- **Clinical reasoning frameworks** — ADPIE, SBAR, and CJMM guided reasoning
- **Drug interaction checking** — medication safety verification
- **Multiple teaching modes** — tutor, exam, case study, and concept review

## Quick Start

```bash
# 1. Start Ollama with your model
ollama serve
ollama pull qwen3.5

# 2. Get curriculum content (Open RN — free, CC-BY 4.0)
python examples/medical_tutor/ingest_curriculum.py --fetch-open-rn

# 3. Index your curriculum with knowledge graph extraction
python examples/medical_tutor/ingest_curriculum.py \
    --docs-path ./curriculum/ \
    --build-kg \
    --subject nursing_fundamentals

# 4. Launch the interactive tutor
python examples/medical_tutor/tutor.py
```

## Curriculum Sources

### Open Educational Resources (Free)

- **Open RN** (CC-BY 4.0) — Nursing fundamentals, pharmacology, skills, mental health
  - NCBI Bookshelf: https://www.ncbi.nlm.nih.gov/books/NBK590025/
  - WisTech Open: https://www.wistechopen.org/open-rn-details
- **University of Michigan Medical OER**
  - https://open.umich.edu/find/open-educational-resources/medical-resources

### Supported Formats

PDF, DOCX, PPTX, Markdown, plain text, HTML, JSON

## Usage Modes

### Tutor Mode (default)
Socratic method teaching with curriculum-grounded answers.
```
[TUTOR] > Explain the renin-angiotensin-aldosterone system
```

### Exam Mode
NCLEX-RN or USMLE practice question generation.
```
[TUTOR] > /exam heart failure nursing care
[EXAM] > /mode exam
```

### Case Study Mode
Clinical case analysis with guided reasoning.
```
[TUTOR] > /case 72-year-old with acute dyspnea and crackles
```

### Concept Review Mode
Knowledge graph exploration and concept mapping.
```
[TUTOR] > /concept metoprolol
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Medical Tutor                     │
├────────────┬────────────┬───────────┬───────────────┤
│  RAG       │ Knowledge  │ Clinical  │ Exam          │
│  Memory    │ Graph      │ Reasoning │ Generator     │
│  (hybrid)  │ (SQLite)   │ (ADPIE/   │ (NCLEX/       │
│            │            │  SBAR/    │  USMLE)       │
│            │            │  CJMM)    │               │
├────────────┴────────────┴───────────┴───────────────┤
│              OpenJarvis Orchestrator Agent           │
├─────────────────────────────────────────────────────┤
│         Qwen 3.5 (local via Ollama)                 │
└─────────────────────────────────────────────────────┘
```

## Files

| File | Description |
|------|-------------|
| `medical_tutor.toml` | Recipe config for the medical tutor agent |
| `ingest_curriculum.py` | Curriculum ingestion pipeline (RAG + KG) |
| `medical_tools.py` | Custom medical tools (concept lookup, clinical reasoning, exam gen, drug interactions) |
| `tutor.py` | Interactive CLI tutor application |
