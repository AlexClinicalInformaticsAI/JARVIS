# MedMCQA

A large-scale, multi-subject, multiple-choice question answering dataset for medical domain question answering. Contains 194k+ real-world medical entrance exam MCQs from India's AIIMS and NEET PG examinations, spanning 2,400+ healthcare topics across 21 medical subjects.

## Overview

| Property | Value |
|----------|-------|
| **Full name** | MedMCQA: A Large-scale Multi-Subject Multi-Choice Dataset for Medical Domain Question Answering |
| **Size** | 194,000+ questions |
| **Subjects** | 21 medical subjects |
| **Topics** | 2,400+ healthcare topics |
| **Language** | English |
| **Avg. token length** | 12.77 tokens per question |
| **Format** | 4-option multiple choice with explanations |
| **License** | MIT |
| **Paper** | Pal, Umapathi & Sankarasubbu (2022), PMLR 174:248-260 |
| **Source exams** | AIIMS PG (1991-present), NEET PG (2001-present) |

## Source

- **Paper**: https://proceedings.mlr.press/v174/pal22a.html
- **GitHub**: https://github.com/medmcqa/medmcqa
- **HuggingFace**: https://huggingface.co/datasets/openlifescienceai/medmcqa
- **Homepage**: https://medmcqa.github.io/

## Dataset Splits

| Split | Questions | Source | Ground truth |
|-------|-----------|--------|--------------|
| **Train** | 182,822 | Mock & online test series | Released |
| **Validation** | 6,150 | NEET PG exams (2001-present) | Released |
| **Test** | 4,183 | AIIMS PG exams (1991-present) | Held out |

- Max question token length: 220 (train), 135 (validation), 88 (test)
- Similar questions between splits were removed based on similarity scoring
- Test set ground truth is not publicly released to preserve evaluation integrity

## Medical Subjects (21)

| Subject | Subject | Subject |
|---------|---------|---------|
| Anatomy | Biochemistry | Physiology |
| Pharmacology | Pathology | Microbiology |
| Forensic Medicine | Ophthalmology | ENT |
| Preventive & Social Medicine | Radiology | Surgery |
| Medicine | Obstetrics & Gynecology | Pediatrics |
| Psychiatry | Skin (Dermatology) | Anesthesia |
| Orthopaedics | Dental | Unknown |

## Data Schema

Each question record contains:

```json
{
  "id":           "string  — unique question identifier",
  "question":     "string  — the question stem",
  "opa":          "string  — option A",
  "opb":          "string  — option B",
  "opc":          "string  — option C",
  "opd":          "string  — option D",
  "cop":          "int     — correct option (0=A, 1=B, 2=C, 3=D)",
  "choice_type":  "string  — 'single' or 'multi'",
  "exp":          "string  — expert explanation / rationale",
  "subject_name": "string  — medical subject",
  "topic_name":   "string  — specific topic within subject"
}
```

## Example Question

```
Subject: Pharmacology
Topic: Cholinergic drugs

Question: Which of the following is a direct-acting cholinomimetic agent?

  A. Neostigmine
  B. Edrophonium
  C. Pilocarpine       ← correct
  D. Physostigmine

Explanation: Pilocarpine is a direct-acting cholinomimetic that binds
directly to muscarinic receptors. Neostigmine, Edrophonium, and
Physostigmine are all indirect-acting agents that inhibit
acetylcholinesterase.
```

## Benchmark Results

MedMCQA is a standard benchmark in the medical AI community, used alongside MedQA, PubMedQA, and MMLU clinical topics.

### Model Performance on MedMCQA (dev set, accuracy %)

| Model | Accuracy | Year | Notes |
|-------|----------|------|-------|
| Random baseline | 25.0% | — | 4-way MCQ |
| BioBERT | ~36% | 2022 | Fine-tuned |
| BioGPT / PaLM | 50-60% | 2022-23 | Zero-shot |
| GPT-4 | ~73% | 2023 | Zero-shot |
| Med-PaLM 2 | ~72% | 2023 | Domain fine-tuned |
| Yi-34B (OpenMedLM) | 68.3% | 2024 | Prompt engineering + voting, open-source SOTA |
| AMG-RAG (8B) | 66.3% | 2024 | Agentic RAG with KG |
| CURE (ensemble) | 78.0% | 2025 | Confidence-driven routing |
| TeamMedAgents (GPT-4o, n=3) | 82.4% | 2025 | Multi-agent teamwork |

### Key Findings

- Questions test 10+ reasoning abilities including recall, comprehension, application, analysis, and clinical judgment
- Even state-of-the-art LLMs score well below 100%, making MedMCQA a challenging and discriminative benchmark
- RAG-augmented open-source models can approach proprietary model performance
- Multi-agent ensemble approaches show the strongest recent results

## Usage in OpenJarvis

### Download and Index

```bash
# Download all subjects (182k+ questions)
python examples/medical_tutor/datasets.py medmcqa

# Filter by specific subjects
python examples/medical_tutor/datasets.py medmcqa --subjects Pharmacology,Pathology,Surgery

# Limit question count
python examples/medical_tutor/datasets.py medmcqa --max-questions 5000

# Download and index into OpenJarvis knowledge base
python examples/medical_tutor/datasets.py medmcqa --index --build-kg
```

### Load with HuggingFace datasets

```python
from datasets import load_dataset

ds = load_dataset("openlifescienceai/medmcqa", split="train")
print(f"Total questions: {len(ds)}")
print(ds[0])
```

### Output Format

The ingestion pipeline produces two files per subject:

- **`medmcqa_{subject}.jsonl`** — structured JSONL for programmatic access
- **`medmcqa_{subject}.txt`** — plain text for RAG indexing and jDocMunch

### Token-Efficient Access

After indexing, use jDocMunch MCP for section-level retrieval:

```bash
python examples/medical_tutor/setup_jdocmunch.py --install
```

Then query individual sections (~400 tokens) instead of loading entire files (~12k tokens).

## Use Cases

| Use Case | How |
|----------|-----|
| **Exam preparation** | Generate practice questions filtered by subject/topic |
| **Knowledge assessment** | Test understanding across all 21 medical subjects |
| **Model benchmarking** | Evaluate medical QA model accuracy on standardized questions |
| **Curriculum gap analysis** | Identify weak subjects by tracking question accuracy |
| **RAG evaluation** | Measure retrieval quality against known correct answers |
| **Knowledge graph seeding** | Extract medical entities and relationships from explanations |

## Citation

```bibtex
@InProceedings{pmlr-v174-pal22a,
  title     = {MedMCQA: A Large-scale Multi-Subject Multi-Choice Dataset
               for Medical domain Question Answering},
  author    = {Pal, Ankit and Umapathi, Logesh Kumar and
               Sankarasubbu, Malaikannan},
  booktitle = {Proceedings of the Conference on Health, Inference,
               and Learning},
  pages     = {248--260},
  year      = {2022},
  volume    = {174},
  series    = {Proceedings of Machine Learning Research},
  publisher = {PMLR},
}
```

## Authors

Ankit Pal, Logesh Kumar Umapathi, Malaikannan Sankarasubbu — Saama AI Research, Chennai, India.

## Related Datasets

- **MedQA** — USMLE-style medical questions (US/China/Taiwan exams)
- **PubMedQA** — Evidence-based yes/no/maybe reasoning from PubMed abstracts
- **MMLU (clinical topics)** — Medical subset of Massive Multitask Language Understanding
- **MIMIC-IV** — Real clinical notes for patient case scenarios
