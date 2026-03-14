#!/usr/bin/env python3
"""Interactive Medical Education Tutor — powered by OpenJarvis.

An interactive CLI tutor that uses your locally-indexed medical/nursing
curriculum with RAG retrieval, a medical knowledge graph, and custom
clinical reasoning tools to provide precision medical education.

Usage:
    python examples/medical_tutor/tutor.py
    python examples/medical_tutor/tutor.py --model qwen3.5:latest
    python examples/medical_tutor/tutor.py --mode exam --subject pharmacology

Modes:
    tutor  — Interactive Q&A with Socratic teaching (default)
    exam   — NCLEX/USMLE practice exam mode
    case   — Clinical case study with guided reasoning
    review — Concept review with knowledge graph exploration

Prerequisites:
    1. Ollama running with your model: ollama serve && ollama pull qwen3.5
    2. Curriculum indexed: python examples/medical_tutor/ingest_curriculum.py \
           --docs-path ./curriculum/ --build-kg
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Dict, List, Optional


BANNER = r"""
 ╔══════════════════════════════════════════════════════════╗
 ║       Medical Education Tutor — OpenJarvis               ║
 ║                                                          ║
 ║  Precision education powered by your curriculum          ║
 ║  with RAG + Knowledge Graph + Clinical Reasoning         ║
 ║                                                          ║
 ║  Commands:                                               ║
 ║    /mode <tutor|exam|case|review>  Switch mode            ║
 ║    /exam <topic>                   Generate practice Qs   ║
 ║    /case <scenario>                Clinical case study    ║
 ║    /drug <med1, med2, ...>         Drug interaction check  ║
 ║    /concept <term>                 Knowledge graph lookup  ║
 ║    /stats                          Memory & KG statistics  ║
 ║    /help                           Show this help          ║
 ║    /quit                           Exit                    ║
 ╚══════════════════════════════════════════════════════════╝
"""

MODE_PROMPTS = {
    "tutor": (
        "You are in TUTOR mode. Use the Socratic method — ask guiding "
        "questions, explain concepts in layers, and connect theory to "
        "clinical practice. Search the indexed curriculum for relevant "
        "content before answering."
    ),
    "exam": (
        "You are in EXAM mode. Generate NCLEX-RN style practice questions "
        "on the topic the student asks about. Use the exam_generator tool, "
        "then present questions one at a time. After the student answers, "
        "provide detailed rationales for correct and incorrect options."
    ),
    "case": (
        "You are in CASE STUDY mode. Present clinical scenarios and guide "
        "the student through clinical reasoning using the ADPIE nursing "
        "process or CJMM framework. Use the clinical_reasoning tool to "
        "structure the case. Ask the student what they would do at each step "
        "before revealing the expected response."
    ),
    "review": (
        "You are in CONCEPT REVIEW mode. When the student asks about a "
        "topic, use the medical_concept_lookup and kg_neighbors tools to "
        "explore the knowledge graph. Present concept maps showing how "
        "diseases, medications, symptoms, and interventions connect."
    ),
}

TOOLS_BY_MODE = {
    "tutor": [
        "think", "memory_search", "memory_store",
        "kg_query", "kg_neighbors",
        "medical_concept_lookup", "clinical_reasoning",
        "exam_generator",
    ],
    "exam": [
        "think", "memory_search", "exam_generator",
        "medical_concept_lookup",
    ],
    "case": [
        "think", "memory_search", "clinical_reasoning",
        "medical_concept_lookup", "drug_interaction_check",
        "kg_query", "kg_neighbors",
    ],
    "review": [
        "think", "memory_search",
        "medical_concept_lookup", "kg_query", "kg_neighbors",
        "kg_add_entity", "kg_add_relation",
    ],
}


def _print_stats(j: Any) -> None:
    """Print memory and knowledge graph statistics."""
    print("\n--- Memory & Knowledge Graph Statistics ---")
    try:
        mem_stats = j.memory.stats()
        print(f"  Memory backend: {mem_stats.get('backend', 'unknown')}")
        if "count" in mem_stats:
            print(f"  Indexed chunks: {mem_stats['count']}")
    except Exception as exc:
        print(f"  Memory stats error: {exc}")

    try:
        from openjarvis.tools.storage.knowledge_graph import KnowledgeGraphMemory
        kg = KnowledgeGraphMemory()
        print(f"  KG entities:    {kg.entity_count()}")
        print(f"  KG relations:   {kg.relation_count()}")
        kg.close()
    except Exception:
        print("  Knowledge graph: not initialized")
    print()


def _handle_command(
    cmd: str, args_str: str, j: Any, state: Dict[str, Any],
) -> bool:
    """Handle slash commands. Returns True if handled."""
    if cmd == "/quit" or cmd == "/exit":
        print("\nGoodbye! Keep studying!")
        return True

    if cmd == "/help":
        print(BANNER)
        return False

    if cmd == "/stats":
        _print_stats(j)
        return False

    if cmd == "/mode":
        mode = args_str.strip().lower()
        if mode in MODE_PROMPTS:
            state["mode"] = mode
            print(f"\n  Switched to {mode.upper()} mode.\n")
        else:
            print(f"  Unknown mode '{mode}'. Use: tutor, exam, case, review")
        return False

    if cmd == "/exam":
        topic = args_str.strip() or "general nursing"
        state["pending_input"] = (
            f"Generate 3 NCLEX-RN practice questions on: {topic}"
        )
        state["mode"] = "exam"
        return False

    if cmd == "/case":
        scenario = args_str.strip() or (
            "A 68-year-old male presents to the ED with chest pain, "
            "diaphoresis, and shortness of breath."
        )
        state["pending_input"] = (
            f"Present a clinical case study and guide me through "
            f"clinical reasoning for this scenario: {scenario}"
        )
        state["mode"] = "case"
        return False

    if cmd == "/drug":
        meds = [m.strip() for m in args_str.split(",") if m.strip()]
        if not meds:
            print("  Usage: /drug warfarin, aspirin, metoprolol")
            return False
        state["pending_input"] = (
            f"Check for drug interactions between: {', '.join(meds)}"
        )
        return False

    if cmd == "/concept":
        concept = args_str.strip()
        if not concept:
            print("  Usage: /concept heart failure")
            return False
        state["pending_input"] = (
            f"Look up the concept '{concept}' in the knowledge graph "
            f"and explain it with related concepts, pathophysiology, "
            f"nursing interventions, and medications."
        )
        state["mode"] = "review"
        return False

    print(f"  Unknown command: {cmd}. Type /help for available commands.")
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactive Medical Education Tutor",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="qwen3.5:latest",
        help="Model to use (default: qwen3.5:latest).",
    )
    parser.add_argument(
        "--engine",
        type=str,
        default="ollama",
        help="Engine backend (default: ollama).",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="tutor",
        choices=["tutor", "exam", "case", "review"],
        help="Starting mode (default: tutor).",
    )
    parser.add_argument(
        "--subject",
        type=str,
        default="",
        help="Focus on a specific subject area.",
    )
    args = parser.parse_args()

    try:
        from openjarvis import Jarvis
    except ImportError:
        print(
            "Error: openjarvis is not installed. "
            "Install with: uv sync --extra dev",
            file=sys.stderr,
        )
        sys.exit(1)

    # Register medical tools
    try:
        import examples.medical_tutor.medical_tools  # noqa: F401
    except ImportError:
        # Try relative import for running from project root
        sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))
        try:
            import examples.medical_tutor.medical_tools  # noqa: F401
        except ImportError:
            print(
                "Warning: Could not import medical_tools. "
                "Custom tools may not be available.",
                file=sys.stderr,
            )

    print(BANNER)
    print(f"  Model:   {args.model}")
    print(f"  Engine:  {args.engine}")
    print(f"  Mode:    {args.mode.upper()}")
    if args.subject:
        print(f"  Subject: {args.subject}")
    print()

    try:
        j = Jarvis(model=args.model, engine_key=args.engine)
    except Exception as exc:
        print(f"Error initializing Jarvis: {exc}", file=sys.stderr)
        print(
            "\nMake sure your engine is running:\n"
            "  ollama serve\n"
            "  ollama pull qwen3.5\n",
            file=sys.stderr,
        )
        sys.exit(1)

    state: Dict[str, Any] = {
        "mode": args.mode,
        "subject": args.subject,
        "pending_input": None,
        "history": [],
    }

    # Show initial stats
    _print_stats(j)

    try:
        while True:
            mode = state["mode"]
            prompt_prefix = f"[{mode.upper()}]"

            if state["pending_input"]:
                user_input = state["pending_input"]
                state["pending_input"] = None
                print(f"{prompt_prefix} > {user_input}")
            else:
                try:
                    user_input = input(f"{prompt_prefix} > ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n\nGoodbye! Keep studying!")
                    break

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()
                cmd_args = parts[1] if len(parts) > 1 else ""
                should_exit = _handle_command(cmd, cmd_args, j, state)
                if should_exit:
                    break
                if state["pending_input"]:
                    continue
                continue

            # Build the full prompt with mode context
            mode_context = MODE_PROMPTS.get(mode, MODE_PROMPTS["tutor"])
            subject_context = ""
            if state["subject"]:
                subject_context = (
                    f"\nThe student is studying {state['subject']}. "
                    f"Relate all answers to this subject area."
                )

            full_query = (
                f"[Mode: {mode}] {mode_context}{subject_context}\n\n"
                f"Student question: {user_input}"
            )

            # Get response with context from indexed curriculum
            try:
                tools = TOOLS_BY_MODE.get(mode, TOOLS_BY_MODE["tutor"])
                response = j.ask(
                    full_query,
                    agent="orchestrator",
                    tools=tools,
                    context=True,
                )

                print()
                print(response)
                print()

                state["history"].append({
                    "mode": mode,
                    "question": user_input,
                    "response_length": len(response),
                })

            except Exception as exc:
                print(f"\nError: {exc}\n", file=sys.stderr)

    finally:
        j.close()
        print(f"\nSession summary: {len(state['history'])} interactions.")


if __name__ == "__main__":
    main()
