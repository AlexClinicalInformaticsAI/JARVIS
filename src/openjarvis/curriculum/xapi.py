"""xAPI (Experience API / Tin Can) statement builder for medical education.

Generates JSON-LD statements that conform to the xAPI 1.0.3 specification
and can be sent to any Learning Record Store (LRS).

Statement pattern:  Actor  +  Verb  +  Object  (+  Result  +  Context)

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
        """Generate one or more xAPI statements from a progress record."""
        statements: List[Dict[str, Any]] = []

        if progress.attended:
            statements.append(
                self._build(event, progress, "attended")
            )

        if progress.lecture_listened:
            statements.append(
                self._build(event, progress, "completed")
            )

        if progress.quiz_score is not None:
            verb = "passed" if progress.quiz_score >= 0.7 else "failed"
            statements.append(
                self._build(
                    event, progress, verb,
                    score=progress.quiz_score,
                    score_label="quiz",
                )
            )

        if progress.exam_score is not None:
            verb = "passed" if progress.exam_score >= 0.7 else "failed"
            statements.append(
                self._build(
                    event, progress, verb,
                    score=progress.exam_score,
                    score_label="exam",
                )
            )

        if progress.competency_level == CompetencyLevel.COMPETENCY:
            statements.append(
                self._build(event, progress, "mastered")
            )
        elif progress.competency_level == CompetencyLevel.PRACTICE:
            statements.append(
                self._build(event, progress, "progressed")
            )
        elif progress.competency_level == CompetencyLevel.EXPOSURE:
            statements.append(
                self._build(event, progress, "experienced")
            )

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
                    f"{self.institution_iri}/context/competency_level": (
                        progress.competency_level.value
                    ),
                },
                "contextActivities": {
                    "grouping": [
                        {
                            "id": f"{self.institution_iri}/aamc-domain/{d.value}",
                            "definition": {
                                "name": {"en-US": d.value.replace("_", " ").title()},
                                "type": "https://w3id.org/xapi/medbiq/activity-types/competency",
                            },
                        }
                        for obj in event.learning_objectives
                        for d in [obj.aamc_domain]
                    ],
                },
            },
        }

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

        return stmt
