"""xAPI (Experience API / Tin Can) statement builder for medical education.

Generates JSON-LD statements conforming to xAPI 1.0.3 for any Learning
Record Store (LRS).

Statement pattern:  Actor  +  Verb  +  Object  (+  Result  +  Context)

Verb coverage:
  - attended       lecture / session
  - completed      assignment / module
  - viewed         recording / media
  - passed / failed  quiz / exam / OSCE
  - experienced    first exposure to topic
  - progressed     advancing competency
  - mastered       demonstrated competence
  - performed      simulation task
  - encountered    patient / clinical diagnosis
  - reflected      experiential reflection / journal

References
----------
- xAPI spec: https://github.com/adlnet/xAPI-Spec
- ADL verb registry: https://registry.tincanapi.com/
- MedBiquitous activity types for CI mapping
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from openjarvis.curriculum.models import (
    AAMCDomain,
    CompetencyLevel,
    CurriculumEvent,
    ExposureLevel,
    StudentProgress,
)

# ── ADL / community verb IRIs ────────────────────────────────────────────

VERBS = {
    "attended": {
        "id": "http://adlnet.gov/expapi/verbs/attended",
        "display": {"en-US": "attended"},
    },
    "completed": {
        "id": "http://adlnet.gov/expapi/verbs/completed",
        "display": {"en-US": "completed"},
    },
    "viewed": {
        "id": "http://id.tincanapi.com/verb/viewed",
        "display": {"en-US": "viewed"},
    },
    "passed": {
        "id": "http://adlnet.gov/expapi/verbs/passed",
        "display": {"en-US": "passed"},
    },
    "failed": {
        "id": "http://adlnet.gov/expapi/verbs/failed",
        "display": {"en-US": "failed"},
    },
    "experienced": {
        "id": "http://adlnet.gov/expapi/verbs/experienced",
        "display": {"en-US": "experienced"},
    },
    "progressed": {
        "id": "http://adlnet.gov/expapi/verbs/progressed",
        "display": {"en-US": "progressed"},
    },
    "scored": {
        "id": "http://adlnet.gov/expapi/verbs/scored",
        "display": {"en-US": "scored"},
    },
    "mastered": {
        "id": "https://w3id.org/xapi/dod-isd/verbs/mastered",
        "display": {"en-US": "mastered"},
    },
    "performed": {
        "id": "https://w3id.org/xapi/dod-isd/verbs/performed",
        "display": {"en-US": "performed"},
    },
    "encountered": {
        "id": "https://w3id.org/xapi/medbiq/verbs/encountered",
        "display": {"en-US": "encountered"},
    },
    "reflected": {
        "id": "https://w3id.org/xapi/dod-isd/verbs/reflected",
        "display": {"en-US": "reflected"},
    },
    "read": {
        "id": "https://w3id.org/xapi/adb/verbs/read",
        "display": {"en-US": "read"},
    },
}

# ── Activity type IRIs ───────────────────────────────────────────────────

ACTIVITY_TYPES = {
    "lecture": "http://adlnet.gov/expapi/activities/lesson",
    "lab": "http://adlnet.gov/expapi/activities/simulation",
    "clinical": "https://w3id.org/xapi/medbiq/activity-types/clinical-rotation",
    "small_group": "http://adlnet.gov/expapi/activities/meeting",
    "simulation": "http://adlnet.gov/expapi/activities/simulation",
    "exam": "http://adlnet.gov/expapi/activities/assessment",
    "quiz": "http://adlnet.gov/expapi/activities/assessment",
    "assignment": "http://adlnet.gov/expapi/activities/assessment",
    "self_study": "http://adlnet.gov/expapi/activities/media",
    "osce": "https://w3id.org/xapi/medbiq/activity-types/performance-assessment",
    "patient_encounter": "https://w3id.org/xapi/medbiq/activity-types/clinical-encounter",
    "reflection": "https://w3id.org/xapi/medbiq/activity-types/reflective-journal",
}


class XAPIStatementBuilder:
    """Builds xAPI 1.0.3 statements for curriculum events."""

    def __init__(
        self,
        institution_iri: str = "https://openjarvis.stanford.edu",
        homepage: str = "https://openjarvis.stanford.edu/students",
    ) -> None:
        self.institution_iri = institution_iri
        self.homepage = homepage

    # ── Public API ───────────────────────────────────────────────────────

    def from_progress(
        self,
        event: CurriculumEvent,
        progress: StudentProgress,
    ) -> List[Dict[str, Any]]:
        """Generate xAPI statements from a progress record.

        Emits one statement per meaningful verb (attendance, viewing,
        reading, assessment, simulation, encounter, reflection, mastery).
        """
        statements: List[Dict[str, Any]] = []

        if progress.attended:
            statements.append(self._build(event, progress, "attended"))

        if progress.lecture_listened:
            statements.append(self._build(event, progress, "completed"))

        if progress.recording_watched:
            statements.append(self._build(event, progress, "viewed"))

        if progress.reading_completed:
            statements.append(self._build(event, progress, "read"))

        if progress.assignment_completed:
            statements.append(
                self._build(event, progress, "completed", extra_ext={
                    f"{self.institution_iri}/result/item_type": "assignment",
                })
            )

        if progress.simulation_completed:
            statements.append(self._build(event, progress, "performed"))

        if progress.patient_encounter_logged:
            statements.append(self._build(event, progress, "encountered"))

        if progress.experiential_notes:
            statements.append(self._build(event, progress, "reflected"))

        # Assessment scores
        if progress.quiz_score is not None:
            verb = "passed" if progress.quiz_score >= 0.7 else "failed"
            statements.append(
                self._build(event, progress, verb,
                            score=progress.quiz_score, score_label="quiz")
            )

        if progress.exam_score is not None:
            verb = "passed" if progress.exam_score >= 0.7 else "failed"
            statements.append(
                self._build(event, progress, verb,
                            score=progress.exam_score, score_label="exam")
            )

        if progress.osce_score is not None:
            verb = "passed" if progress.osce_score >= 0.7 else "failed"
            statements.append(
                self._build(event, progress, verb,
                            score=progress.osce_score, score_label="osce")
            )

        # Competency / exposure level statements
        if progress.competency_level == CompetencyLevel.GREEN:
            statements.append(self._build(event, progress, "mastered"))
        elif progress.competency_level == CompetencyLevel.YELLOW:
            statements.append(self._build(event, progress, "progressed"))
        elif progress.exposure_level == ExposureLevel.RED:
            statements.append(self._build(event, progress, "experienced"))

        return statements

    def attendance_statement(
        self,
        event: CurriculumEvent,
        student_id: str,
    ) -> Dict[str, Any]:
        """Shorthand: single attendance statement."""
        progress = StudentProgress(
            event_id=event.id, student_id=student_id, attended=True,
        )
        return self._build(event, progress, "attended")

    # ── Internal builder ─────────────────────────────────────────────────

    def _build(
        self,
        event: CurriculumEvent,
        progress: StudentProgress,
        verb_key: str,
        *,
        score: Optional[float] = None,
        score_label: Optional[str] = None,
        extra_ext: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        stmt: Dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "actor": {
                "objectType": "Agent",
                "account": {
                    "homePage": self.homepage,
                    "name": progress.student_id,
                },
            },
            "verb": VERBS[verb_key],
            "object": {
                "objectType": "Activity",
                "id": f"{self.institution_iri}/curriculum/{event.id}",
                "definition": {
                    "name": {"en-US": event.title},
                    "description": {"en-US": event.description or event.topic},
                    "type": ACTIVITY_TYPES.get(
                        event.event_type.value,
                        "http://adlnet.gov/expapi/activities/lesson",
                    ),
                },
            },
            "timestamp": (
                progress.updated_at or datetime.now(timezone.utc)
            ).isoformat(),
            "context": {
                "extensions": {
                    f"{self.institution_iri}/context/subject": event.subject,
                    f"{self.institution_iri}/context/topic": event.topic,
                    f"{self.institution_iri}/context/year": event.year,
                    f"{self.institution_iri}/context/block": event.block,
                    f"{self.institution_iri}/context/course": event.course,
                    f"{self.institution_iri}/context/clerkship": event.clerkship,
                    f"{self.institution_iri}/context/exposure_level": (
                        progress.exposure_level.value
                    ),
                    f"{self.institution_iri}/context/competency_level": (
                        progress.competency_level.value
                    ),
                    f"{self.institution_iri}/context/attendance_status": (
                        "present" if progress.attended else "absent"
                    ),
                },
                "contextActivities": {
                    "category": [
                        {
                            "id": f"{self.institution_iri}/xapi/profiles/medical-curriculum",
                        }
                    ],
                    "grouping": self._aamc_grouping(event),
                },
            },
        }

        # Add objective IDs to context
        if event.learning_objectives:
            stmt["context"]["extensions"][
                f"{self.institution_iri}/context/objective_ids"
            ] = [o.id for o in event.learning_objectives]
            stmt["context"]["extensions"][
                f"{self.institution_iri}/context/aamc_tags"
            ] = list({o.aamc_domain.value for o in event.learning_objectives})

        if score is not None:
            stmt["result"] = {
                "score": {
                    "scaled": round(score, 4),
                    "raw": round(score * 100, 1),
                    "min": 0,
                    "max": 100,
                },
                "success": score >= 0.7,
                "completion": True,
            }
            if score_label:
                stmt["result"]["extensions"] = {
                    f"{self.institution_iri}/result/assessment_type": score_label,
                }

        if extra_ext:
            stmt["context"]["extensions"].update(extra_ext)

        return stmt

    def _aamc_grouping(self, event: CurriculumEvent) -> List[Dict[str, Any]]:
        """Build AAMC competency domain grouping activities."""
        seen = set()
        grouping = []
        for obj in event.learning_objectives:
            if obj.aamc_domain.value not in seen:
                seen.add(obj.aamc_domain.value)
                grouping.append({
                    "id": f"{self.institution_iri}/aamc-domain/{obj.aamc_domain.value}",
                    "definition": {
                        "name": {"en-US": obj.aamc_domain.value.replace("_", " ").title()},
                        "type": "https://w3id.org/xapi/medbiq/activity-types/competency",
                    },
                })
        return grouping
