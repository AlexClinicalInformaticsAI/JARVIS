#!/usr/bin/env python3
"""Medical dataset ingestion — PubMed OA, MedMCQA, MIMIC, PubMedQA.

Downloads and indexes four major medical datasets into OpenJarvis
for use as a medical education knowledge base.

Datasets:
    pubmed-oa   — PubMed Central Open Access articles → knowledge base
    medmcqa     — 194k medical MCQs (AIIMS/NEET PG) → exam questions
    mimic       — MIMIC-IV clinical notes → patient scenarios
    pubmedqa    — 211k evidence-based QA pairs → reasoning training

Usage:
    python examples/medical_tutor/datasets.py --help
    python examples/medical_tutor/datasets.py pubmed-oa --topic cardiology --max-articles 500
    python examples/medical_tutor/datasets.py medmcqa --subjects Pharmacology,Pathology
    python examples/medical_tutor/datasets.py pubmedqa --split labeled
    python examples/medical_tutor/datasets.py mimic --data-path /path/to/mimic-iv-note/
    python examples/medical_tutor/datasets.py all --max-articles 200

Prerequisites:
    pip install datasets requests lxml
    # For MIMIC: requires PhysioNet credentialed access
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path.home() / ".openjarvis" / "medical_data"

PUBMED_OA_API = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
PUBMED_BIOC_API = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json"
PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

MEDMCQA_HF = "openlifescienceai/medmcqa"
PUBMEDQA_HF = "qiaojin/PubMedQA"

# Medical subjects in MedMCQA
MEDMCQA_SUBJECTS = [
    "Anatomy", "Biochemistry", "Physiology", "Pharmacology",
    "Pathology", "Microbiology", "Forensic Medicine",
    "Ophthalmology", "ENT", "Preventive Medicine",
    "Radiology", "Surgery", "Medicine", "Obstetrics & Gynecology",
    "Pediatrics", "Psychiatry", "Skin", "Anesthesia",
    "Orthopaedics", "Dental", "Unknown",
]


# ---------------------------------------------------------------------------
# PubMed Open Access → Knowledge Base
# ---------------------------------------------------------------------------


def fetch_pubmed_oa(
    topic: str = "nursing education",
    max_articles: int = 100,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Fetch PubMed Central Open Access articles via E-utilities + BioC API.

    Downloads article abstracts and full text (when available) for a given
    medical topic and stores them as text files for indexing.

    Parameters
    ----------
    topic : str
        Search query (e.g., "heart failure pathophysiology", "pharmacology").
    max_articles : int
        Maximum number of articles to fetch.
    output_dir : Path, optional
        Directory to save articles. Defaults to ~/.openjarvis/medical_data/pubmed_oa/.

    Returns
    -------
    dict with keys: articles_fetched, output_dir, errors
    """
    dest = output_dir or DATA_DIR / "pubmed_oa" / topic.replace(" ", "_")
    dest.mkdir(parents=True, exist_ok=True)

    stats = {"articles_fetched": 0, "output_dir": str(dest), "errors": []}

    print(f"  Searching PubMed for: {topic}")
    print(f"  Max articles: {max_articles}")

    # Step 1: Search for PMC IDs via E-utilities
    try:
        search_url = (
            f"{PUBMED_ESEARCH}?db=pmc&term={urllib.parse.quote(topic)}"
            f"+AND+open+access[filter]&retmax={max_articles}&retmode=json"
        )
        with urllib.request.urlopen(search_url, timeout=30) as resp:
            search_data = json.loads(resp.read().decode())

        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        total_found = search_data.get("esearchresult", {}).get("count", "0")
        print(f"  Found {total_found} articles, fetching {len(id_list)}")

    except Exception as exc:
        print(f"  Search error: {exc}", file=sys.stderr)
        stats["errors"].append(f"Search failed: {exc}")
        return stats

    # Step 2: Fetch abstracts and metadata via E-fetch
    if not id_list:
        print("  No articles found.")
        return stats

    batch_size = 50
    for i in range(0, len(id_list), batch_size):
        batch = id_list[i:i + batch_size]
        batch_ids = ",".join(batch)

        try:
            fetch_url = (
                f"{PUBMED_EFETCH}?db=pmc&id={batch_ids}"
                f"&rettype=abstract&retmode=xml"
            )
            with urllib.request.urlopen(fetch_url, timeout=60) as resp:
                xml_data = resp.read().decode()

            # Parse XML and extract articles
            root = ET.fromstring(xml_data)
            for article_el in root.iter("article"):
                try:
                    article = _parse_pmc_article(article_el)
                    if article and article.get("text"):
                        pmc_id = article.get("pmc_id", f"unknown_{stats['articles_fetched']}")
                        filepath = dest / f"{pmc_id}.txt"

                        content_parts = []
                        if article.get("title"):
                            content_parts.append(f"# {article['title']}")
                        if article.get("journal"):
                            content_parts.append(f"Journal: {article['journal']}")
                        if article.get("authors"):
                            content_parts.append(f"Authors: {article['authors']}")
                        content_parts.append("")
                        content_parts.append(article["text"])

                        if article.get("keywords"):
                            content_parts.append(f"\nKeywords: {article['keywords']}")

                        filepath.write_text("\n".join(content_parts), encoding="utf-8")
                        stats["articles_fetched"] += 1

                except Exception as exc:
                    stats["errors"].append(f"Parse error: {exc}")

            # Rate limit: NCBI requires max 3 requests/second without API key
            time.sleep(0.5)

        except Exception as exc:
            stats["errors"].append(f"Fetch batch error: {exc}")
            time.sleep(1)

        print(f"  Progress: {min(i + batch_size, len(id_list))}/{len(id_list)} articles")

    print(f"  Saved {stats['articles_fetched']} articles to {dest}")
    return stats


def _parse_pmc_article(article_el: ET.Element) -> Optional[Dict[str, str]]:
    """Extract text content from a PMC XML article element."""
    result: Dict[str, str] = {}

    # Title
    title_el = article_el.find(".//article-title")
    if title_el is not None:
        result["title"] = "".join(title_el.itertext()).strip()

    # PMC ID
    for id_el in article_el.iter("article-id"):
        if id_el.get("pub-id-type") == "pmc":
            result["pmc_id"] = f"PMC{id_el.text}"
            break

    # Journal
    journal_el = article_el.find(".//journal-title")
    if journal_el is not None:
        result["journal"] = journal_el.text or ""

    # Authors
    authors = []
    for name_el in article_el.iter("name"):
        surname = name_el.findtext("surname", "")
        given = name_el.findtext("given-names", "")
        if surname:
            authors.append(f"{given} {surname}".strip())
    result["authors"] = ", ".join(authors[:5])
    if len(authors) > 5:
        result["authors"] += f" et al. ({len(authors)} total)"

    # Abstract
    abstract_parts: List[str] = []
    for abstract_el in article_el.iter("abstract"):
        for p in abstract_el.iter("p"):
            text = "".join(p.itertext()).strip()
            if text:
                abstract_parts.append(text)

    # Body text (if available)
    body_parts: List[str] = []
    body_el = article_el.find(".//body")
    if body_el is not None:
        for sec in body_el.iter("sec"):
            sec_title = sec.findtext("title", "")
            if sec_title:
                body_parts.append(f"\n## {sec_title}\n")
            for p in sec.findall("p"):
                text = "".join(p.itertext()).strip()
                if text:
                    body_parts.append(text)

    # Keywords
    keywords = []
    for kwd in article_el.iter("kwd"):
        if kwd.text:
            keywords.append(kwd.text.strip())
    result["keywords"] = ", ".join(keywords)

    # Combine text
    text_parts = []
    if abstract_parts:
        text_parts.append("## Abstract\n")
        text_parts.extend(abstract_parts)
    if body_parts:
        text_parts.extend(body_parts)
    elif abstract_parts:
        pass  # abstract only is fine
    else:
        return None  # no usable text

    result["text"] = "\n\n".join(text_parts)
    return result


# ---------------------------------------------------------------------------
# MedMCQA → Exam-Style Questions
# ---------------------------------------------------------------------------


def fetch_medmcqa(
    subjects: Optional[List[str]] = None,
    max_questions: int = 10000,
    output_dir: Optional[Path] = None,
    split: str = "train",
) -> Dict[str, Any]:
    """Download MedMCQA dataset from HuggingFace and convert to
    structured exam question files for the knowledge base.

    Each question includes: stem, 4 options, correct answer,
    explanation, subject, and topic.

    Parameters
    ----------
    subjects : list of str, optional
        Filter by medical subjects (e.g., ["Pharmacology", "Pathology"]).
        None means all subjects.
    max_questions : int
        Maximum questions to index.
    output_dir : Path, optional
        Output directory.
    split : str
        Dataset split: "train", "validation", or "test".
    """
    try:
        from datasets import load_dataset
    except ImportError:
        print(
            "  Error: 'datasets' library required. Install with:\n"
            "    pip install datasets",
            file=sys.stderr,
        )
        return {"questions_fetched": 0, "errors": ["datasets library not installed"]}

    dest = output_dir or DATA_DIR / "medmcqa"
    dest.mkdir(parents=True, exist_ok=True)

    stats: Dict[str, Any] = {
        "questions_fetched": 0,
        "output_dir": str(dest),
        "subjects": {},
        "errors": [],
    }

    print(f"  Loading MedMCQA {split} split from HuggingFace...")
    try:
        ds = load_dataset(MEDMCQA_HF, split=split)
    except Exception as exc:
        print(f"  Download error: {exc}", file=sys.stderr)
        stats["errors"].append(str(exc))
        return stats

    print(f"  Total questions in {split}: {len(ds)}")

    option_map = {0: "A", 1: "B", 2: "C", 3: "D"}
    count = 0
    subject_questions: Dict[str, List[Dict[str, Any]]] = {}

    for item in ds:
        subject = item.get("subject_name", "Unknown")

        # Filter by subject if specified
        if subjects and subject not in subjects:
            continue

        if count >= max_questions:
            break

        question_data = {
            "id": item.get("id", str(count)),
            "question": item.get("question", ""),
            "options": {
                "A": item.get("opa", ""),
                "B": item.get("opb", ""),
                "C": item.get("opc", ""),
                "D": item.get("opd", ""),
            },
            "correct_answer": option_map.get(item.get("cop", -1), "?"),
            "explanation": item.get("exp", ""),
            "subject": subject,
            "topic": item.get("topic_name", ""),
        }

        if subject not in subject_questions:
            subject_questions[subject] = []
        subject_questions[subject].append(question_data)
        count += 1

    # Write questions grouped by subject
    for subject, questions in subject_questions.items():
        safe_name = subject.lower().replace(" ", "_").replace("&", "and")
        filepath = dest / f"medmcqa_{safe_name}.jsonl"

        with open(filepath, "w", encoding="utf-8") as f:
            for q in questions:
                f.write(json.dumps(q, ensure_ascii=False) + "\n")

        stats["subjects"][subject] = len(questions)
        stats["questions_fetched"] += len(questions)

        # Also create a text version for RAG indexing
        txt_path = dest / f"medmcqa_{safe_name}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"# MedMCQA — {subject}\n\n")
            for q in questions:
                f.write(f"## Question ({q['topic']})\n\n")
                f.write(f"{q['question']}\n\n")
                for opt_key, opt_val in q["options"].items():
                    marker = "**" if opt_key == q["correct_answer"] else ""
                    f.write(f"  {opt_key}. {marker}{opt_val}{marker}\n")
                f.write(f"\nCorrect: {q['correct_answer']}\n")
                if q["explanation"]:
                    f.write(f"Explanation: {q['explanation']}\n")
                f.write("\n---\n\n")

    print(f"  Saved {stats['questions_fetched']} questions across {len(subject_questions)} subjects")
    return stats


# ---------------------------------------------------------------------------
# MIMIC-IV Notes → Clinical Case Scenarios
# ---------------------------------------------------------------------------


def ingest_mimic_notes(
    data_path: str,
    max_notes: int = 5000,
    note_types: Optional[List[str]] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Ingest MIMIC-IV-Note discharge summaries and radiology reports.

    MIMIC-IV requires credentialed access via PhysioNet. This function
    reads the CSV files after you've downloaded them.

    Access:
        1. Complete CITI training: https://physionet.org/about/citi-course/
        2. Request access: https://physionet.org/content/mimic-iv-note/2.2/
        3. Download and extract to a local directory
        4. Point --data-path to the extracted directory

    Demo (no notes, but structured data):
        https://physionet.org/content/mimic-iv-demo/2.2/

    Parameters
    ----------
    data_path : str
        Path to extracted MIMIC-IV-Note directory (contains discharge.csv.gz).
    max_notes : int
        Maximum notes to process.
    note_types : list, optional
        Types: ["discharge", "radiology"]. Default: ["discharge"].
    output_dir : Path, optional
        Output directory.
    """
    import csv
    import io

    dest = output_dir or DATA_DIR / "mimic"
    dest.mkdir(parents=True, exist_ok=True)

    if note_types is None:
        note_types = ["discharge"]

    root = Path(data_path)
    stats: Dict[str, Any] = {
        "notes_processed": 0,
        "output_dir": str(dest),
        "note_types": {},
        "errors": [],
    }

    for note_type in note_types:
        # MIMIC-IV-Note stores files as discharge.csv.gz, radiology.csv.gz
        gz_path = root / f"{note_type}.csv.gz"
        csv_path = root / f"{note_type}.csv"

        if gz_path.exists():
            reader_path = gz_path
            is_gz = True
        elif csv_path.exists():
            reader_path = csv_path
            is_gz = False
        else:
            # Try nested paths
            for candidate in root.rglob(f"{note_type}.csv*"):
                reader_path = candidate
                is_gz = candidate.suffix == ".gz"
                break
            else:
                stats["errors"].append(
                    f"{note_type}.csv(.gz) not found in {data_path}. "
                    f"Download from: https://physionet.org/content/mimic-iv-note/2.2/"
                )
                print(f"  {note_type}: NOT FOUND")
                continue

        print(f"  Processing {note_type} notes from {reader_path.name}...")

        type_dest = dest / note_type
        type_dest.mkdir(exist_ok=True)
        type_count = 0

        try:
            if is_gz:
                fh = gzip.open(str(reader_path), "rt", encoding="utf-8")
            else:
                fh = open(str(reader_path), "r", encoding="utf-8")

            with fh:
                reader = csv.DictReader(fh)

                for row in reader:
                    if type_count >= max_notes:
                        break

                    note_text = row.get("text", "")
                    if not note_text or len(note_text) < 100:
                        continue

                    # Build case file
                    note_id = row.get("note_id", str(type_count))
                    subject_id = row.get("subject_id", "unknown")
                    hadm_id = row.get("hadm_id", "unknown")
                    charttime = row.get("charttime", row.get("chartdate", ""))

                    content_parts = [
                        f"# Clinical Note — {note_type.title()}",
                        f"Note ID: {note_id}",
                        f"Patient ID: {subject_id} | Admission: {hadm_id}",
                    ]
                    if charttime:
                        content_parts.append(f"Date: {charttime}")
                    content_parts.append("")
                    content_parts.append(note_text)

                    filepath = type_dest / f"{note_type}_{note_id}.txt"
                    filepath.write_text(
                        "\n".join(content_parts), encoding="utf-8",
                    )
                    type_count += 1

                    if type_count % 500 == 0:
                        print(f"    {type_count} notes processed...")

        except Exception as exc:
            stats["errors"].append(f"{note_type} processing error: {exc}")
            print(f"  Error: {exc}", file=sys.stderr)

        stats["note_types"][note_type] = type_count
        stats["notes_processed"] += type_count
        print(f"  {note_type}: {type_count} notes saved")

    return stats


# ---------------------------------------------------------------------------
# PubMedQA → Evidence-Based Reasoning
# ---------------------------------------------------------------------------


def fetch_pubmedqa(
    split: str = "pqa_labeled",
    max_questions: int = 50000,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Download PubMedQA dataset for evidence-based reasoning training.

    Splits available:
        pqa_labeled    — 1,000 expert-annotated yes/no/maybe QA pairs
        pqa_artificial — 211,300 auto-generated QA pairs
        pqa_unlabeled  — 61,200 unlabeled context-question pairs

    Each instance contains: question (from paper title), context
    (abstract without conclusion), long_answer (conclusion), and
    yes/no/maybe decision.

    Parameters
    ----------
    split : str
        One of "pqa_labeled", "pqa_artificial", "pqa_unlabeled".
    max_questions : int
        Maximum questions to process.
    output_dir : Path, optional
        Output directory.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        print(
            "  Error: 'datasets' library required. Install with:\n"
            "    pip install datasets",
            file=sys.stderr,
        )
        return {"questions_fetched": 0, "errors": ["datasets library not installed"]}

    dest = output_dir or DATA_DIR / "pubmedqa"
    dest.mkdir(parents=True, exist_ok=True)

    stats: Dict[str, Any] = {
        "questions_fetched": 0,
        "output_dir": str(dest),
        "split": split,
        "answer_distribution": {"yes": 0, "no": 0, "maybe": 0},
        "errors": [],
    }

    print(f"  Loading PubMedQA ({split}) from HuggingFace...")
    try:
        # PubMedQA uses config names, not split names
        ds = load_dataset(PUBMEDQA_HF, split, split="train")
    except Exception as exc:
        print(f"  Download error: {exc}", file=sys.stderr)
        stats["errors"].append(str(exc))
        return stats

    print(f"  Total questions in {split}: {len(ds)}")

    # Write as JSONL for structured access + text for RAG
    jsonl_path = dest / f"pubmedqa_{split}.jsonl"
    txt_path = dest / f"pubmedqa_{split}.txt"

    count = 0
    with (
        open(jsonl_path, "w", encoding="utf-8") as jf,
        open(txt_path, "w", encoding="utf-8") as tf,
    ):
        tf.write(f"# PubMedQA — {split}\n")
        tf.write(f"# Evidence-Based Medical Reasoning Dataset\n\n")

        for item in ds:
            if count >= max_questions:
                break

            question = item.get("question", "")
            if not question:
                continue

            # Extract context (abstract sections)
            context_data = item.get("context", {})
            contexts = context_data.get("contexts", []) if isinstance(context_data, dict) else []
            labels = context_data.get("labels", []) if isinstance(context_data, dict) else []
            meshes = context_data.get("meshes", []) if isinstance(context_data, dict) else []

            long_answer = item.get("long_answer", "")
            decision = item.get("final_decision", "")
            pubid = item.get("pubid", count)

            qa_entry = {
                "pubid": pubid,
                "question": question,
                "context_sections": [
                    {"label": labels[i] if i < len(labels) else "",
                     "text": contexts[i] if i < len(contexts) else ""}
                    for i in range(len(contexts))
                ] if contexts else [],
                "long_answer": long_answer,
                "decision": decision,
                "mesh_terms": meshes if isinstance(meshes, list) else [],
            }

            jf.write(json.dumps(qa_entry, ensure_ascii=False) + "\n")

            # Text version for RAG
            tf.write(f"## PubMed {pubid}\n\n")
            tf.write(f"**Question:** {question}\n\n")
            if contexts:
                tf.write("**Evidence:**\n")
                for j, ctx in enumerate(contexts):
                    label = labels[j] if j < len(labels) else ""
                    if label:
                        tf.write(f"_{label}:_ ")
                    tf.write(f"{ctx}\n\n")
            if long_answer:
                tf.write(f"**Conclusion:** {long_answer}\n\n")
            if decision:
                tf.write(f"**Answer:** {decision}\n\n")
                stats["answer_distribution"][decision] = (
                    stats["answer_distribution"].get(decision, 0) + 1
                )
            tf.write("---\n\n")

            count += 1

            if count % 5000 == 0:
                print(f"    {count} questions processed...")

    stats["questions_fetched"] = count
    print(f"  Saved {count} QA pairs to {dest}")
    return stats


# ---------------------------------------------------------------------------
# Index into OpenJarvis
# ---------------------------------------------------------------------------


def index_dataset_into_jarvis(
    data_dir: str,
    subject: str,
    chunk_size: int = 512,
    model: str = "qwen3.5:latest",
    engine: str = "ollama",
    build_kg: bool = False,
) -> Dict[str, Any]:
    """Index downloaded dataset files into OpenJarvis memory + knowledge graph."""
    try:
        # Re-use the existing ingestion pipeline
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from examples.medical_tutor.ingest_curriculum import index_documents

        return index_documents(
            data_dir,
            chunk_size=chunk_size,
            subject=subject,
            build_kg=build_kg,
            model=model,
            engine_key=engine,
        )
    except ImportError:
        print(
            "  Error: Could not import ingest_curriculum. "
            "Run from the project root directory.",
            file=sys.stderr,
        )
        return {"error": "import failed"}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and index medical datasets into OpenJarvis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Datasets:
  pubmed-oa   PubMed Central Open Access articles → knowledge base
  medmcqa     194k medical MCQs (AIIMS/NEET PG) → exam questions
  mimic       MIMIC-IV clinical notes → patient case scenarios
  pubmedqa    211k evidence-based QA pairs → reasoning
  all         Download pubmed-oa + medmcqa + pubmedqa (not MIMIC)

Examples:
  %(prog)s pubmed-oa --topic "heart failure nursing" --max-articles 200
  %(prog)s medmcqa --subjects Pharmacology,Pathology --max-questions 5000
  %(prog)s pubmedqa --split pqa_artificial --max-questions 50000
  %(prog)s mimic --data-path /data/mimic-iv-note/
  %(prog)s all --index --build-kg
        """,
    )
    parser.add_argument(
        "dataset",
        choices=["pubmed-oa", "medmcqa", "mimic", "pubmedqa", "all"],
        help="Dataset to download.",
    )

    # Common options
    parser.add_argument("--output-dir", type=str, help="Output directory override.")
    parser.add_argument(
        "--index", action="store_true",
        help="Index downloaded data into OpenJarvis after download.",
    )
    parser.add_argument(
        "--build-kg", action="store_true",
        help="Build knowledge graph during indexing.",
    )
    parser.add_argument(
        "--model", type=str, default="qwen3.5:latest",
        help="Model for KG extraction (default: qwen3.5:latest).",
    )
    parser.add_argument(
        "--engine", type=str, default="ollama",
        help="Inference engine (default: ollama).",
    )

    # PubMed OA options
    parser.add_argument(
        "--topic", type=str, default="nursing medical education",
        help="PubMed search topic (default: 'nursing medical education').",
    )
    parser.add_argument(
        "--max-articles", type=int, default=200,
        help="Max PubMed articles (default: 200).",
    )

    # MedMCQA options
    parser.add_argument(
        "--subjects", type=str, default=None,
        help="Comma-separated MedMCQA subjects (e.g., Pharmacology,Pathology).",
    )
    parser.add_argument(
        "--max-questions", type=int, default=10000,
        help="Max questions per dataset (default: 10000).",
    )

    # PubMedQA options
    parser.add_argument(
        "--split", type=str, default="pqa_labeled",
        choices=["pqa_labeled", "pqa_artificial", "pqa_unlabeled"],
        help="PubMedQA split (default: pqa_labeled).",
    )

    # MIMIC options
    parser.add_argument(
        "--data-path", type=str,
        help="Path to downloaded MIMIC-IV-Note data.",
    )
    parser.add_argument(
        "--max-notes", type=int, default=5000,
        help="Max MIMIC notes to process (default: 5000).",
    )

    args = parser.parse_args()

    import urllib.parse  # noqa: F811 — needed for URL encoding

    print("=" * 60)
    print("  Medical Dataset Ingestion Pipeline")
    print("=" * 60)
    print()

    output_dir = Path(args.output_dir) if args.output_dir else None
    all_stats: Dict[str, Any] = {}
    t0 = time.time()

    # --- PubMed OA ---
    if args.dataset in ("pubmed-oa", "all"):
        print("[1/4] PubMed Open Access → Knowledge Base")
        print("-" * 40)
        pubmed_stats = fetch_pubmed_oa(
            topic=args.topic,
            max_articles=args.max_articles,
            output_dir=output_dir / "pubmed_oa" if output_dir else None,
        )
        all_stats["pubmed_oa"] = pubmed_stats

        if args.index and pubmed_stats.get("articles_fetched", 0) > 0:
            print("  Indexing into OpenJarvis...")
            index_dataset_into_jarvis(
                pubmed_stats["output_dir"],
                subject="pubmed_literature",
                model=args.model,
                engine=args.engine,
                build_kg=args.build_kg,
            )
        print()

    # --- MedMCQA ---
    if args.dataset in ("medmcqa", "all"):
        print("[2/4] MedMCQA → Exam-Style Questions")
        print("-" * 40)
        subjects = args.subjects.split(",") if args.subjects else None
        medmcqa_stats = fetch_medmcqa(
            subjects=subjects,
            max_questions=args.max_questions,
            output_dir=output_dir / "medmcqa" if output_dir else None,
        )
        all_stats["medmcqa"] = medmcqa_stats

        if args.index and medmcqa_stats.get("questions_fetched", 0) > 0:
            print("  Indexing into OpenJarvis...")
            index_dataset_into_jarvis(
                medmcqa_stats["output_dir"],
                subject="exam_questions",
                model=args.model,
                engine=args.engine,
                build_kg=args.build_kg,
            )
        print()

    # --- MIMIC ---
    if args.dataset == "mimic":
        print("[3/4] MIMIC-IV Notes → Clinical Case Scenarios")
        print("-" * 40)
        if not args.data_path:
            print()
            print("  MIMIC-IV requires credentialed access via PhysioNet.")
            print()
            print("  Steps to get access:")
            print("    1. Create PhysioNet account: https://physionet.org/register/")
            print("    2. Complete CITI training:    https://physionet.org/about/citi-course/")
            print("    3. Sign data use agreement:   https://physionet.org/content/mimic-iv-note/2.2/")
            print("    4. Download and extract the data")
            print("    5. Run: python datasets.py mimic --data-path /path/to/mimic-iv-note/")
            print()
            print("  Demo dataset (structured data, no notes):")
            print("    https://physionet.org/content/mimic-iv-demo/2.2/")
            print()
            print("  MIMIC-IV-Note v2.2:")
            print("    - 331,794 discharge summaries (145,915 patients)")
            print("    - 2,321,355 radiology reports (237,427 patients)")
            print()
        else:
            mimic_stats = ingest_mimic_notes(
                data_path=args.data_path,
                max_notes=args.max_notes,
                output_dir=output_dir / "mimic" if output_dir else None,
            )
            all_stats["mimic"] = mimic_stats

            if args.index and mimic_stats.get("notes_processed", 0) > 0:
                print("  Indexing into OpenJarvis...")
                index_dataset_into_jarvis(
                    mimic_stats["output_dir"],
                    subject="clinical_cases",
                    model=args.model,
                    engine=args.engine,
                    build_kg=args.build_kg,
                )
        print()

    # --- PubMedQA ---
    if args.dataset in ("pubmedqa", "all"):
        print("[4/4] PubMedQA → Evidence-Based Reasoning")
        print("-" * 40)
        pubmedqa_stats = fetch_pubmedqa(
            split=args.split,
            max_questions=args.max_questions,
            output_dir=output_dir / "pubmedqa" if output_dir else None,
        )
        all_stats["pubmedqa"] = pubmedqa_stats

        if args.index and pubmedqa_stats.get("questions_fetched", 0) > 0:
            print("  Indexing into OpenJarvis...")
            index_dataset_into_jarvis(
                pubmedqa_stats["output_dir"],
                subject="evidence_reasoning",
                model=args.model,
                engine=args.engine,
                build_kg=args.build_kg,
            )
        print()

    elapsed = time.time() - t0

    # Summary
    print("=" * 60)
    print("  Download Complete")
    print("=" * 60)
    for name, s in all_stats.items():
        if name == "pubmed_oa":
            print(f"  PubMed OA:  {s.get('articles_fetched', 0)} articles")
        elif name == "medmcqa":
            print(f"  MedMCQA:    {s.get('questions_fetched', 0)} questions")
            if s.get("subjects"):
                for subj, cnt in sorted(s["subjects"].items()):
                    print(f"              - {subj}: {cnt}")
        elif name == "mimic":
            print(f"  MIMIC:      {s.get('notes_processed', 0)} clinical notes")
        elif name == "pubmedqa":
            print(f"  PubMedQA:   {s.get('questions_fetched', 0)} QA pairs")
            if s.get("answer_distribution"):
                dist = s["answer_distribution"]
                print(f"              yes: {dist.get('yes', 0)}, "
                      f"no: {dist.get('no', 0)}, "
                      f"maybe: {dist.get('maybe', 0)}")

    total_errors = sum(len(s.get("errors", [])) for s in all_stats.values())
    print(f"  Errors:     {total_errors}")
    print(f"  Time:       {elapsed:.1f}s")
    print(f"  Data dir:   {DATA_DIR}")
    print()

    if not args.index:
        print("  To index into OpenJarvis, re-run with --index:")
        print(f"    python datasets.py {args.dataset} --index --build-kg")
    print()


if __name__ == "__main__":
    main()
