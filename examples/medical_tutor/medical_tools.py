"""Custom medical education tools for OpenJarvis.

Registers four domain-specific tools:
- medical_concept_lookup: Structured concept retrieval from knowledge graph
- clinical_reasoning: Step-by-step clinical reasoning chains
- exam_generator: NCLEX-RN / USMLE style question generation
- drug_interaction_check: Medication safety verification

These tools follow the OpenJarvis BaseTool pattern and are registered
via @ToolRegistry.register() for automatic discovery.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from openjarvis.core.registry import ToolRegistry
from openjarvis.core.types import ToolResult
from openjarvis.tools._stubs import BaseTool, ToolSpec


# ---------------------------------------------------------------------------
# Tool 1: Medical Concept Lookup
# ---------------------------------------------------------------------------


@ToolRegistry.register("medical_concept_lookup")
class MedicalConceptLookupTool(BaseTool):
    """Look up a medical or nursing concept in the knowledge graph and
    return its definition, related concepts, and clinical significance."""

    tool_id = "medical_concept_lookup"

    def __init__(self, kg_backend: Optional[Any] = None) -> None:
        self._kg = kg_backend

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="medical_concept_lookup",
            description=(
                "Look up a medical or nursing concept and return its "
                "definition, body system, related conditions, medications, "
                "and nursing interventions from the knowledge graph."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "concept": {
                        "type": "string",
                        "description": (
                            "The medical concept to look up "
                            "(e.g., 'heart_failure', 'hypokalemia', "
                            "'metoprolol')."
                        ),
                    },
                    "include_relations": {
                        "type": "boolean",
                        "description": (
                            "Include related concepts and their "
                            "relationships (default: true)."
                        ),
                    },
                },
                "required": ["concept"],
            },
            category="medical_education",
            cost_estimate=0.001,
            latency_estimate=0.5,
        )

    def execute(self, **params: Any) -> ToolResult:
        concept = params["concept"].lower().replace(" ", "_")
        include_relations = params.get("include_relations", True)

        if self._kg is None:
            return ToolResult(
                tool_name="medical_concept_lookup",
                content=(
                    "Knowledge graph not initialized. "
                    "Run ingest_curriculum.py with --build-kg first."
                ),
                success=False,
            )

        # Look up the entity
        entity = self._kg.get_entity(concept)

        if entity is None:
            # Try searching by name
            results = self._kg.search(concept, top_k=5)
            if results:
                matches = [
                    {
                        "id": r["key"],
                        "name": r.get("metadata", {}).get("name", r["key"]),
                        "type": r.get("metadata", {}).get("entity_type", ""),
                    }
                    for r in results
                ]
                return ToolResult(
                    tool_name="medical_concept_lookup",
                    content=json.dumps({
                        "status": "not_found",
                        "message": f"Exact match for '{concept}' not found.",
                        "similar_concepts": matches,
                    }, indent=2),
                    success=True,
                )
            return ToolResult(
                tool_name="medical_concept_lookup",
                content=f"Concept '{concept}' not found in knowledge graph.",
                success=False,
            )

        result: Dict[str, Any] = {
            "concept": entity.name,
            "type": entity.entity_type,
            "properties": entity.properties,
        }

        if include_relations:
            neighbors = self._kg.neighbors(concept, limit=20)
            related: List[Dict[str, str]] = []
            for n in neighbors:
                related.append({
                    "name": n.name,
                    "type": n.entity_type,
                    "id": n.entity_id,
                })
            result["related_concepts"] = related

            # Get specific relation types
            for rel_type in [
                "treats", "causes", "manifests_as",
                "nursing_intervention_for", "side_effect_of",
            ]:
                query_result = self._kg.query_pattern(
                    relation_type=rel_type, limit=10,
                )
                relevant = [
                    r for r in query_result.relations
                    if r.source_id == concept or r.target_id == concept
                ]
                if relevant:
                    result[rel_type] = [
                        {
                            "from": r.source_id,
                            "to": r.target_id,
                            "weight": r.weight,
                        }
                        for r in relevant
                    ]

        return ToolResult(
            tool_name="medical_concept_lookup",
            content=json.dumps(result, indent=2),
            success=True,
        )


# ---------------------------------------------------------------------------
# Tool 2: Clinical Reasoning
# ---------------------------------------------------------------------------


@ToolRegistry.register("clinical_reasoning")
class ClinicalReasoningTool(BaseTool):
    """Walk through a clinical scenario using structured reasoning
    frameworks (ADPIE, SBAR, clinical judgment model)."""

    tool_id = "clinical_reasoning"

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="clinical_reasoning",
            description=(
                "Generate a structured clinical reasoning chain for a "
                "patient scenario using nursing frameworks. Supports "
                "ADPIE (nursing process), SBAR (communication), and "
                "CJMM (clinical judgment measurement model)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "scenario": {
                        "type": "string",
                        "description": (
                            "The clinical scenario or patient "
                            "presentation to analyze."
                        ),
                    },
                    "framework": {
                        "type": "string",
                        "description": (
                            "Reasoning framework: 'adpie' (nursing "
                            "process), 'sbar' (communication), or "
                            "'cjmm' (clinical judgment). "
                            "Default: 'adpie'."
                        ),
                    },
                    "focus_area": {
                        "type": "string",
                        "description": (
                            "Optional area to focus on "
                            "(e.g., 'cardiac', 'respiratory', "
                            "'medication_safety')."
                        ),
                    },
                },
                "required": ["scenario"],
            },
            category="medical_education",
            cost_estimate=0.002,
            latency_estimate=1.0,
        )

    def execute(self, **params: Any) -> ToolResult:
        scenario = params["scenario"]
        framework = params.get("framework", "adpie").lower()
        focus = params.get("focus_area", "")

        if framework == "adpie":
            template = self._adpie_template(scenario, focus)
        elif framework == "sbar":
            template = self._sbar_template(scenario, focus)
        elif framework == "cjmm":
            template = self._cjmm_template(scenario, focus)
        else:
            return ToolResult(
                tool_name="clinical_reasoning",
                content=(
                    f"Unknown framework '{framework}'. "
                    "Use 'adpie', 'sbar', or 'cjmm'."
                ),
                success=False,
            )

        return ToolResult(
            tool_name="clinical_reasoning",
            content=json.dumps(template, indent=2),
            success=True,
        )

    def _adpie_template(
        self, scenario: str, focus: str,
    ) -> Dict[str, Any]:
        return {
            "framework": "ADPIE (Nursing Process)",
            "scenario": scenario,
            "focus": focus or "comprehensive",
            "steps": {
                "assessment": {
                    "description": "Collect subjective and objective data",
                    "prompts": [
                        "What subjective data does the patient report?",
                        "What objective data can be observed or measured?",
                        "What are the relevant vital signs?",
                        "What laboratory values are significant?",
                        "What is the patient's medical/surgical history?",
                    ],
                },
                "diagnosis": {
                    "description": "Identify priority nursing diagnoses",
                    "prompts": [
                        "What are the actual nursing diagnoses?",
                        "What are the risk nursing diagnoses?",
                        "Which diagnosis has the highest priority and why?",
                        "What is the related factor (etiology)?",
                        "What are the defining characteristics (evidence)?",
                    ],
                },
                "planning": {
                    "description": "Set SMART goals and expected outcomes",
                    "prompts": [
                        "What are the short-term goals (within shift)?",
                        "What are the long-term goals (by discharge)?",
                        "Are the goals Specific, Measurable, Achievable, "
                        "Relevant, and Time-bound?",
                        "What are the expected outcomes?",
                    ],
                },
                "implementation": {
                    "description": "Nursing interventions with rationales",
                    "prompts": [
                        "What independent nursing interventions are needed?",
                        "What collaborative interventions are needed?",
                        "What patient education should be provided?",
                        "What is the rationale for each intervention?",
                        "What safety considerations apply?",
                    ],
                },
                "evaluation": {
                    "description": "Determine if goals were met",
                    "prompts": [
                        "Were the expected outcomes achieved?",
                        "What data supports the evaluation?",
                        "Does the care plan need revision?",
                        "What follow-up is needed?",
                    ],
                },
            },
        }

    def _sbar_template(
        self, scenario: str, focus: str,
    ) -> Dict[str, Any]:
        return {
            "framework": "SBAR (Situation-Background-Assessment-Recommendation)",
            "scenario": scenario,
            "focus": focus or "provider communication",
            "steps": {
                "situation": {
                    "description": "What is happening right now?",
                    "prompts": [
                        "Patient name, location, and code status",
                        "What is the current concern or change in condition?",
                        "What are the current vital signs?",
                    ],
                },
                "background": {
                    "description": "What is the clinical context?",
                    "prompts": [
                        "Admitting diagnosis and date of admission",
                        "Relevant medical/surgical history",
                        "Current medications and recent changes",
                        "Recent lab results and procedures",
                        "Allergies",
                    ],
                },
                "assessment": {
                    "description": "What do you think is going on?",
                    "prompts": [
                        "What is your clinical assessment?",
                        "Is the patient's condition improving, stable, "
                        "or deteriorating?",
                        "What is the severity level?",
                    ],
                },
                "recommendation": {
                    "description": "What do you need?",
                    "prompts": [
                        "What action do you recommend?",
                        "Do you need new orders or medications?",
                        "Does the patient need to be seen now?",
                        "Are there any tests that should be ordered?",
                    ],
                },
            },
        }

    def _cjmm_template(
        self, scenario: str, focus: str,
    ) -> Dict[str, Any]:
        return {
            "framework": "NCSBN Clinical Judgment Measurement Model (CJMM)",
            "scenario": scenario,
            "focus": focus or "clinical judgment development",
            "layers": {
                "layer_0_environment": {
                    "description": "Environmental and individual factors",
                    "components": [
                        "Client complexity and acuity",
                        "Environmental context (setting, resources)",
                        "Nurse experience level and knowledge",
                        "Time pressure and cognitive load",
                    ],
                },
                "layer_1_recognize_cues": {
                    "description": "Identify relevant information",
                    "prompts": [
                        "What relevant cues are present in the data?",
                        "What deviations from expected findings exist?",
                        "What data is most clinically significant?",
                    ],
                },
                "layer_2_analyze_cues": {
                    "description": "Link cues to conditions",
                    "prompts": [
                        "How do the cues relate to each other?",
                        "What patterns or clusters emerge?",
                        "What conditions could explain these cues?",
                        "What are the most likely vs. most dangerous "
                        "explanations?",
                    ],
                },
                "layer_3_prioritize_hypotheses": {
                    "description": "Rank by urgency and likelihood",
                    "prompts": [
                        "Which hypothesis is most likely?",
                        "Which is most urgent/life-threatening?",
                        "What additional data would confirm or rule out "
                        "each hypothesis?",
                    ],
                },
                "layer_4_generate_solutions": {
                    "description": "Identify interventions",
                    "prompts": [
                        "What nursing interventions address the "
                        "priority hypothesis?",
                        "What are the expected outcomes of each "
                        "intervention?",
                        "What are potential complications?",
                    ],
                },
                "layer_5_take_actions": {
                    "description": "Implement with appropriate timing",
                    "prompts": [
                        "What actions should be taken first?",
                        "What is the correct sequence of actions?",
                        "What safety checks are needed before and "
                        "during the action?",
                    ],
                },
                "layer_6_evaluate_outcomes": {
                    "description": "Compare actual vs. expected",
                    "prompts": [
                        "Did the interventions achieve the expected "
                        "outcomes?",
                        "What follow-up assessment is needed?",
                        "Does the plan need to be modified?",
                    ],
                },
            },
        }


# ---------------------------------------------------------------------------
# Tool 3: Exam Question Generator
# ---------------------------------------------------------------------------


@ToolRegistry.register("exam_generator")
class ExamGeneratorTool(BaseTool):
    """Generate NCLEX-RN or USMLE style practice questions based on
    a given topic, with answer explanations and rationales."""

    tool_id = "exam_generator"

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="exam_generator",
            description=(
                "Generate NCLEX-RN or USMLE style practice exam "
                "questions on a given medical/nursing topic. Returns "
                "multiple-choice questions with detailed rationales "
                "for correct and incorrect answers."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": (
                            "The clinical topic to generate questions "
                            "about (e.g., 'heart failure nursing care', "
                            "'insulin administration', "
                            "'postoperative assessment')."
                        ),
                    },
                    "exam_type": {
                        "type": "string",
                        "description": (
                            "Type of exam: 'nclex' for NCLEX-RN style "
                            "or 'usmle' for USMLE style. "
                            "Default: 'nclex'."
                        ),
                    },
                    "difficulty": {
                        "type": "string",
                        "description": (
                            "Difficulty level: 'recall' (knowledge), "
                            "'application' (apply concepts), or "
                            "'analysis' (critical thinking). "
                            "Maps to Bloom's taxonomy. "
                            "Default: 'application'."
                        ),
                    },
                    "count": {
                        "type": "integer",
                        "description": (
                            "Number of questions to generate "
                            "(1-5, default: 3)."
                        ),
                    },
                    "question_format": {
                        "type": "string",
                        "description": (
                            "Format: 'multiple_choice', "
                            "'select_all_that_apply', or 'ordered_response'. "
                            "Default: 'multiple_choice'."
                        ),
                    },
                },
                "required": ["topic"],
            },
            category="medical_education",
            cost_estimate=0.003,
            latency_estimate=2.0,
        )

    def execute(self, **params: Any) -> ToolResult:
        topic = params["topic"]
        exam_type = params.get("exam_type", "nclex").lower()
        difficulty = params.get("difficulty", "application").lower()
        count = min(params.get("count", 3), 5)
        question_format = params.get(
            "question_format", "multiple_choice",
        ).lower()

        # Build question template
        template = {
            "exam_type": exam_type.upper(),
            "topic": topic,
            "difficulty": difficulty,
            "bloom_level": {
                "recall": "Remember/Understand",
                "application": "Apply/Analyze",
                "analysis": "Analyze/Evaluate/Create",
            }.get(difficulty, "Apply/Analyze"),
            "format": question_format,
            "question_count": count,
            "instructions": self._get_instructions(
                exam_type, difficulty, question_format, count,
            ),
        }

        return ToolResult(
            tool_name="exam_generator",
            content=json.dumps(template, indent=2),
            success=True,
        )

    def _get_instructions(
        self,
        exam_type: str,
        difficulty: str,
        question_format: str,
        count: int,
    ) -> str:
        if exam_type == "nclex":
            return (
                f"Generate {count} NCLEX-RN style {question_format.replace('_', ' ')} "
                f"question(s) at the '{difficulty}' level. "
                "Each question MUST include:\n"
                "1. A clinical scenario/stem (2-3 sentences with patient context)\n"
                "2. The question (what is the PRIORITY action, BEST response, etc.)\n"
                "3. Four answer options (A-D) — one correct, three plausible distractors\n"
                "4. The correct answer with detailed rationale\n"
                "5. Why each incorrect answer is wrong\n"
                "6. The NCLEX client needs category "
                "(Safe/Effective Care, Health Promotion, Psychosocial Integrity, "
                "Physiological Integrity)\n"
                "7. The cognitive level (Bloom's taxonomy)\n\n"
                "For Select All That Apply (SATA): provide 5-6 options with "
                "multiple correct answers.\n"
                "For Ordered Response: provide steps that must be placed in "
                "correct sequence."
            )
        else:  # USMLE
            return (
                f"Generate {count} USMLE-style vignette question(s) at "
                f"the '{difficulty}' level. "
                "Each question MUST include:\n"
                "1. A detailed clinical vignette (age, sex, presenting "
                "complaint, history, physical exam findings, lab values)\n"
                "2. The question stem\n"
                "3. Five answer options (A-E)\n"
                "4. The correct answer with pathophysiological explanation\n"
                "5. Why each incorrect answer is wrong\n"
                "6. The relevant organ system and discipline\n"
                "7. Key concept being tested"
            )


# ---------------------------------------------------------------------------
# Tool 4: Drug Interaction Checker
# ---------------------------------------------------------------------------


@ToolRegistry.register("drug_interaction_check")
class DrugInteractionCheckTool(BaseTool):
    """Check for potential drug interactions, contraindications,
    and nursing implications for medications."""

    tool_id = "drug_interaction_check"

    def __init__(self, kg_backend: Optional[Any] = None) -> None:
        self._kg = kg_backend

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="drug_interaction_check",
            description=(
                "Check for drug interactions, contraindications, and "
                "nursing implications between medications. Queries the "
                "knowledge graph for known interactions and provides "
                "safety guidance."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "medications": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "List of medication names to check "
                            "(e.g., ['warfarin', 'aspirin', 'metoprolol'])."
                        ),
                    },
                    "patient_context": {
                        "type": "string",
                        "description": (
                            "Optional patient context "
                            "(e.g., 'elderly female with renal impairment')."
                        ),
                    },
                },
                "required": ["medications"],
            },
            category="medical_education",
            cost_estimate=0.002,
            latency_estimate=1.0,
        )

    def execute(self, **params: Any) -> ToolResult:
        medications = params["medications"]
        patient_context = params.get("patient_context", "")

        if not medications or len(medications) < 1:
            return ToolResult(
                tool_name="drug_interaction_check",
                content="At least one medication is required.",
                success=False,
            )

        result: Dict[str, Any] = {
            "medications": medications,
            "patient_context": patient_context or "not specified",
            "interactions": [],
            "nursing_considerations": [],
            "safety_template": self._safety_template(medications),
        }

        # Query knowledge graph if available
        if self._kg is not None:
            for med in medications:
                med_id = med.lower().replace(" ", "_")
                entity = self._kg.get_entity(med_id)
                if entity:
                    result["known_entities"] = result.get(
                        "known_entities", [],
                    )
                    result["known_entities"].append({
                        "medication": med,
                        "type": entity.entity_type,
                        "properties": entity.properties,
                    })

                # Check for interaction relations
                neighbors = self._kg.neighbors(
                    med_id, relation_type="interacts_with", limit=10,
                )
                for neighbor in neighbors:
                    if neighbor.entity_id in [
                        m.lower().replace(" ", "_")
                        for m in medications
                    ]:
                        result["interactions"].append({
                            "drug_a": med,
                            "drug_b": neighbor.name,
                            "source": "knowledge_graph",
                        })

                contraindicated = self._kg.neighbors(
                    med_id,
                    relation_type="contraindicated_with",
                    limit=10,
                )
                for c in contraindicated:
                    result["nursing_considerations"].append({
                        "medication": med,
                        "contraindicated_with": c.name,
                        "source": "knowledge_graph",
                    })

        return ToolResult(
            tool_name="drug_interaction_check",
            content=json.dumps(result, indent=2),
            success=True,
        )

    def _safety_template(
        self, medications: List[str],
    ) -> Dict[str, Any]:
        """Return a medication safety assessment template."""
        return {
            "rights_of_medication_administration": [
                "Right patient",
                "Right medication",
                "Right dose",
                "Right route",
                "Right time",
                "Right documentation",
                "Right reason",
                "Right response",
            ],
            "assessment_checklist": [
                f"Verify allergies before administering {', '.join(medications)}",
                "Check renal and hepatic function for dose adjustments",
                "Review current lab values (especially for narrow "
                "therapeutic index drugs)",
                "Assess for pregnancy/lactation",
                "Check for duplicate therapy",
                "Verify compatibility if IV medications",
            ],
            "monitoring_parameters": (
                "Review peak/trough levels, vital signs, "
                "intake/output, and relevant lab values per "
                "medication protocol."
            ),
        }


__all__ = [
    "ClinicalReasoningTool",
    "DrugInteractionCheckTool",
    "ExamGeneratorTool",
    "MedicalConceptLookupTool",
]
