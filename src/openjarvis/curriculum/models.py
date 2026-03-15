"""Data models for medical school curriculum tracking.

Maps to AAMC 2024 Foundational Competencies and xAPI statements.
Red / Yellow / Green represents the learner's progression:
  - Red    = Exposure    (has seen the material)
  - Yellow = Practice    (has applied / rehearsed)
  - Green  = Competency  (has demonstrated mastery)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional


# ── AAMC 2024 Foundational Competency Domains ───────────────────────────

class AAMCDomain(str, enum.Enum):
    """Six core AAMC / ACGME / AACOM competency domains (Dec 2024)."""

    PROFESSIONALISM = "professionalism"
    PATIENT_CARE = "patient_care_and_procedural_skills"
    MEDICAL_KNOWLEDGE = "medical_knowledge"
    PRACTICE_BASED_LEARNING = "practice_based_learning_and_improvement"
    INTERPERSONAL_COMMUNICATION = "interpersonal_and_communication_skills"
    SYSTEMS_BASED_PRACTICE = "systems_based_practice"


# ── Competency progression (R / Y / G) ──────────────────────────────────

class CompetencyLevel(str, enum.Enum):
    """Three-tier colour-coded competency progression."""

    NONE = "none"          # not yet encountered
    EXPOSURE = "red"       # has been exposed to the content
    PRACTICE = "yellow"    # has practised / applied
    COMPETENCY = "green"   # demonstrated mastery via assessment


# ── Learning Objective ───────────────────────────────────────────────────

@dataclass
class LearningObjective:
    """A single measurable objective attached to a curriculum event."""

    id: str
    description: str
    aamc_domain: AAMCDomain
    bloom_level: str = "recall"          # recall | understand | apply | analyze | evaluate | create
    epa_mapping: Optional[str] = None    # e.g. "EPA-1", "EPA-6"
    tags: List[str] = field(default_factory=list)


# ── Curriculum Event (lecture / lab / clinical) ──────────────────────────

class EventType(str, enum.Enum):
    LECTURE = "lecture"
    LAB = "lab"
    CLINICAL = "clinical"
    SMALL_GROUP = "small_group"
    SIMULATION = "simulation"
    EXAM = "exam"
    QUIZ = "quiz"
    ASSIGNMENT = "assignment"
    SELF_STUDY = "self_study"


@dataclass
class CurriculumEvent:
    """One calendar entry in the medical school curriculum."""

    id: str
    title: str
    event_type: EventType
    subject: str                         # e.g. "Anatomy", "Pharmacology"
    topic: str                           # more specific: "Brachial Plexus"
    date: date
    start_time: time
    end_time: time
    year: int                            # M1 / M2 / M3 / M4
    block: str = ""                      # e.g. "Block 3 — Cardiovascular"
    location: str = ""
    instructor: str = ""
    description: str = ""
    learning_objectives: List[LearningObjective] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)   # event IDs
    resources: List[str] = field(default_factory=list)       # URLs / file paths
    metadata: Dict[str, Any] = field(default_factory=dict)


# ── Student Progress on an Event ─────────────────────────────────────────

@dataclass
class StudentProgress:
    """Tracks a learner's engagement and competency for one event."""

    event_id: str
    student_id: str
    attended: bool = False
    lecture_listened: bool = False        # completed recording / live
    assignment_completed: bool = False
    quiz_score: Optional[float] = None   # 0.0 – 1.0
    exam_score: Optional[float] = None   # 0.0 – 1.0
    competency_level: CompetencyLevel = CompetencyLevel.NONE
    experiential_notes: str = ""         # clinical / lived experience journal
    updated_at: Optional[datetime] = None
    xapi_statements: List[Dict[str, Any]] = field(default_factory=list)


# ── Helpers ──────────────────────────────────────────────────────────────

AAMC_DOMAIN_LABELS: Dict[AAMCDomain, str] = {
    AAMCDomain.PROFESSIONALISM: "Professionalism",
    AAMCDomain.PATIENT_CARE: "Patient Care & Procedural Skills",
    AAMCDomain.MEDICAL_KNOWLEDGE: "Medical Knowledge",
    AAMCDomain.PRACTICE_BASED_LEARNING: "Practice-Based Learning & Improvement",
    AAMCDomain.INTERPERSONAL_COMMUNICATION: "Interpersonal & Communication Skills",
    AAMCDomain.SYSTEMS_BASED_PRACTICE: "Systems-Based Practice",
}
