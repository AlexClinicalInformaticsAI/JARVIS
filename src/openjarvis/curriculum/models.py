"""Data models for medical school curriculum tracking.

Maps to AAMC 2024 Foundational Competencies and xAPI statements.

Two independent colour axes — exposure is NOT competency:

Exposure state (how many times / modalities encountered):
  - Red    = not yet encountered or minimal
  - Yellow = exposed once or inconsistently
  - Green  = repeatedly encountered in multiple modalities

Competency state (evidence of mastery from assessment):
  - Red    = below expected performance
  - Yellow = developing / partial mastery
  - Green  = demonstrated competence

Longitudinal objective lifecycle:
  1. Introduced → 2. Revisited → 3. Practised → 4. Assessed
  → 5. Applied in real/simulated care → 6. Mastered → 7. Revalidated
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


# ── Dual-layer colour states ────────────────────────────────────────────

class ExposureLevel(str, enum.Enum):
    """How much the learner has been *exposed* to a topic."""

    NONE = "none"
    RED = "red"        # not yet encountered or minimal
    YELLOW = "yellow"  # exposed once or inconsistently
    GREEN = "green"    # repeatedly encountered in multiple modalities


class CompetencyLevel(str, enum.Enum):
    """Assessment-backed evidence of *mastery*."""

    NONE = "none"
    RED = "red"        # below expected performance
    YELLOW = "yellow"  # developing / partial mastery
    GREEN = "green"    # demonstrated competence


# ── Objective lifecycle stage ────────────────────────────────────────────

class ObjectiveStage(str, enum.Enum):
    """Longitudinal stage of a learning objective for a learner."""

    NOT_STARTED = "not_started"
    INTRODUCED = "introduced"
    REVISITED = "revisited"
    PRACTISED = "practised"
    ASSESSED = "assessed"
    APPLIED = "applied"          # real or simulated clinical care
    MASTERED = "mastered"
    REVALIDATED = "revalidated"  # refreshed after gap
    STALE = "stale"              # competence decay — needs refresh


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
    # AAMC CI keywords for Curriculum Inventory reporting
    aamc_ci_keywords: List[str] = field(default_factory=list)


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
    OSCE = "osce"
    PATIENT_ENCOUNTER = "patient_encounter"
    REFLECTION = "reflection"


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
    course: str = ""                     # e.g. "Foundations of Clinical Medicine"
    clerkship: str = ""                  # e.g. "Internal Medicine Clerkship"
    location: str = ""
    instructor: str = ""
    description: str = ""
    learning_objectives: List[LearningObjective] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)   # event IDs
    resources: List[str] = field(default_factory=list)       # URLs / file paths
    recording_url: str = ""              # lecture recording link
    metadata: Dict[str, Any] = field(default_factory=dict)


# ── Student Progress on an Event ─────────────────────────────────────────

@dataclass
class StudentProgress:
    """Tracks a learner's engagement and competency for one event.

    Separates *exposure* (did they encounter it?) from *competency*
    (can they demonstrate mastery?).
    """

    event_id: str
    student_id: str
    # ── engagement tracking ──
    attended: bool = False
    lecture_listened: bool = False        # completed recording / live
    recording_watched: bool = False      # viewed the recording
    assignment_completed: bool = False
    reading_completed: bool = False
    simulation_completed: bool = False
    patient_encounter_logged: bool = False
    # ── assessment ──
    quiz_score: Optional[float] = None   # 0.0 – 1.0
    exam_score: Optional[float] = None   # 0.0 – 1.0
    osce_score: Optional[float] = None   # 0.0 – 1.0
    faculty_observation: Optional[str] = None  # free-text clinical eval
    # ── dual-layer R/Y/G ──
    exposure_level: ExposureLevel = ExposureLevel.NONE
    competency_level: CompetencyLevel = CompetencyLevel.NONE
    # ── experiential ──
    experiential_notes: str = ""         # clinical / lived experience journal
    clinical_encounters: List[Dict[str, Any]] = field(default_factory=list)
    # ── meta ──
    updated_at: Optional[datetime] = None
    xapi_statements: List[Dict[str, Any]] = field(default_factory=list)


# ── Learner-Objective longitudinal record ────────────────────────────────

@dataclass
class ObjectiveProgress:
    """Longitudinal tracking of one learner × one learning objective.

    This is the core of the competency engine — it tracks every
    encounter with an objective across the entire curriculum.
    """

    objective_id: str
    student_id: str
    stage: ObjectiveStage = ObjectiveStage.NOT_STARTED
    exposure_level: ExposureLevel = ExposureLevel.NONE
    competency_level: CompetencyLevel = CompetencyLevel.NONE
    # Evidence trail
    encounter_count: int = 0             # total times encountered
    modalities_seen: List[str] = field(default_factory=list)  # lecture, lab, clinical, sim…
    first_exposure: Optional[date] = None
    last_exposure: Optional[date] = None
    last_assessed: Optional[date] = None
    last_applied: Optional[date] = None  # clinical / simulation
    assessment_scores: List[float] = field(default_factory=list)
    # Computed
    trend: str = "stable"                # improving | stable | declining | stale
    days_since_last_exposure: Optional[int] = None
    recommended_action: str = ""         # e.g. "review", "practice", "assess"
    updated_at: Optional[datetime] = None


# ── Helpers ──────────────────────────────────────────────────────────────

AAMC_DOMAIN_LABELS: Dict[AAMCDomain, str] = {
    AAMCDomain.PROFESSIONALISM: "Professionalism",
    AAMCDomain.PATIENT_CARE: "Patient Care & Procedural Skills",
    AAMCDomain.MEDICAL_KNOWLEDGE: "Medical Knowledge",
    AAMCDomain.PRACTICE_BASED_LEARNING: "Practice-Based Learning & Improvement",
    AAMCDomain.INTERPERSONAL_COMMUNICATION: "Interpersonal & Communication Skills",
    AAMCDomain.SYSTEMS_BASED_PRACTICE: "Systems-Based Practice",
}

EXPOSURE_LABELS: Dict[ExposureLevel, str] = {
    ExposureLevel.NONE: "Not Encountered",
    ExposureLevel.RED: "Minimal Exposure",
    ExposureLevel.YELLOW: "Partial Exposure",
    ExposureLevel.GREEN: "Full Exposure",
}

COMPETENCY_LABELS: Dict[CompetencyLevel, str] = {
    CompetencyLevel.NONE: "Not Assessed",
    CompetencyLevel.RED: "Below Expected",
    CompetencyLevel.YELLOW: "Developing",
    CompetencyLevel.GREEN: "Competent",
}

STAGE_LABELS: Dict[ObjectiveStage, str] = {
    ObjectiveStage.NOT_STARTED: "Not Started",
    ObjectiveStage.INTRODUCED: "Introduced",
    ObjectiveStage.REVISITED: "Revisited",
    ObjectiveStage.PRACTISED: "Practised",
    ObjectiveStage.ASSESSED: "Assessed",
    ObjectiveStage.APPLIED: "Applied",
    ObjectiveStage.MASTERED: "Mastered",
    ObjectiveStage.REVALIDATED: "Revalidated",
    ObjectiveStage.STALE: "Stale — Needs Refresh",
}

# Staleness threshold (days since last exposure before flagging)
STALE_THRESHOLD_DAYS = 90
