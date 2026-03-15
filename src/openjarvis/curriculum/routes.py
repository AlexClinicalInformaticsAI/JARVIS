"""FastAPI routes for curriculum calendar, student progress,
objective timelines, and competency engine.

Mounted under ``/v1/curriculum`` by the main app.
"""

from __future__ import annotations

import os
from datetime import date, datetime, time, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from openjarvis.curriculum.engine import compute_objective_progress
from openjarvis.curriculum.models import (
    AAMCDomain,
    CompetencyLevel,
    CurriculumEvent,
    EventType,
    ExposureLevel,
    LearningObjective,
    ObjectiveProgress,
    ObjectiveStage,
    StudentProgress,
)
from openjarvis.curriculum.store import CurriculumStore
from openjarvis.curriculum.xapi import XAPIStatementBuilder

router = APIRouter(prefix="/v1/curriculum", tags=["curriculum"])

_store: Optional[CurriculumStore] = None
_xapi = XAPIStatementBuilder()


def _get_store() -> CurriculumStore:
    global _store
    if _store is None:
        db_path = os.environ.get(
            "CURRICULUM_DB", os.path.expanduser("~/.openjarvis/curriculum.db")
        )
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        _store = CurriculumStore(db_path)
    return _store


# ── Request / Response models ────────────────────────────────────────────

class LearningObjectiveIn(BaseModel):
    id: str
    description: str
    aamc_domain: str = "medical_knowledge"
    bloom_level: str = "recall"
    epa_mapping: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    aamc_ci_keywords: List[str] = Field(default_factory=list)


class EventIn(BaseModel):
    id: str
    title: str
    event_type: str = "lecture"
    subject: str
    topic: str
    date: str
    start_time: str
    end_time: str
    year: int
    block: str = ""
    course: str = ""
    clerkship: str = ""
    location: str = ""
    instructor: str = ""
    description: str = ""
    learning_objectives: List[LearningObjectiveIn] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    resources: List[str] = Field(default_factory=list)
    recording_url: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProgressIn(BaseModel):
    event_id: str
    student_id: str
    attended: bool = False
    lecture_listened: bool = False
    recording_watched: bool = False
    assignment_completed: bool = False
    reading_completed: bool = False
    simulation_completed: bool = False
    patient_encounter_logged: bool = False
    quiz_score: Optional[float] = None
    exam_score: Optional[float] = None
    osce_score: Optional[float] = None
    faculty_observation: Optional[str] = None
    exposure_level: str = "none"
    competency_level: str = "none"
    experiential_notes: str = ""
    clinical_encounters: List[Dict[str, Any]] = Field(default_factory=list)


# ── Serializers ──────────────────────────────────────────────────────────

def _event_to_dict(ev: CurriculumEvent) -> Dict[str, Any]:
    return {
        "id": ev.id,
        "title": ev.title,
        "event_type": ev.event_type.value,
        "subject": ev.subject,
        "topic": ev.topic,
        "date": ev.date.isoformat(),
        "start_time": ev.start_time.isoformat(),
        "end_time": ev.end_time.isoformat(),
        "year": ev.year,
        "block": ev.block,
        "course": ev.course,
        "clerkship": ev.clerkship,
        "location": ev.location,
        "instructor": ev.instructor,
        "description": ev.description,
        "learning_objectives": [
            {
                "id": o.id,
                "description": o.description,
                "aamc_domain": o.aamc_domain.value,
                "bloom_level": o.bloom_level,
                "epa_mapping": o.epa_mapping,
                "tags": o.tags,
                "aamc_ci_keywords": o.aamc_ci_keywords,
            }
            for o in ev.learning_objectives
        ],
        "prerequisites": ev.prerequisites,
        "resources": ev.resources,
        "recording_url": ev.recording_url,
        "metadata": ev.metadata,
    }


def _progress_to_dict(p: StudentProgress) -> Dict[str, Any]:
    return {
        "event_id": p.event_id,
        "student_id": p.student_id,
        "attended": p.attended,
        "lecture_listened": p.lecture_listened,
        "recording_watched": p.recording_watched,
        "assignment_completed": p.assignment_completed,
        "reading_completed": p.reading_completed,
        "simulation_completed": p.simulation_completed,
        "patient_encounter_logged": p.patient_encounter_logged,
        "quiz_score": p.quiz_score,
        "exam_score": p.exam_score,
        "osce_score": p.osce_score,
        "faculty_observation": p.faculty_observation,
        "exposure_level": p.exposure_level.value,
        "competency_level": p.competency_level.value,
        "experiential_notes": p.experiential_notes,
        "clinical_encounters": p.clinical_encounters,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        "xapi_statements": p.xapi_statements,
    }


def _obj_progress_to_dict(op: ObjectiveProgress) -> Dict[str, Any]:
    return {
        "objective_id": op.objective_id,
        "student_id": op.student_id,
        "stage": op.stage.value,
        "exposure_level": op.exposure_level.value,
        "competency_level": op.competency_level.value,
        "encounter_count": op.encounter_count,
        "modalities_seen": op.modalities_seen,
        "first_exposure": op.first_exposure.isoformat() if op.first_exposure else None,
        "last_exposure": op.last_exposure.isoformat() if op.last_exposure else None,
        "last_assessed": op.last_assessed.isoformat() if op.last_assessed else None,
        "last_applied": op.last_applied.isoformat() if op.last_applied else None,
        "assessment_scores": op.assessment_scores,
        "trend": op.trend,
        "days_since_last_exposure": op.days_since_last_exposure,
        "recommended_action": op.recommended_action,
    }


def _parse_event(body: EventIn) -> CurriculumEvent:
    return CurriculumEvent(
        id=body.id,
        title=body.title,
        event_type=EventType(body.event_type),
        subject=body.subject,
        topic=body.topic,
        date=date.fromisoformat(body.date),
        start_time=time.fromisoformat(body.start_time),
        end_time=time.fromisoformat(body.end_time),
        year=body.year,
        block=body.block,
        course=body.course,
        clerkship=body.clerkship,
        location=body.location,
        instructor=body.instructor,
        description=body.description,
        learning_objectives=[
            LearningObjective(
                id=o.id,
                description=o.description,
                aamc_domain=AAMCDomain(o.aamc_domain),
                bloom_level=o.bloom_level,
                epa_mapping=o.epa_mapping,
                tags=o.tags,
                aamc_ci_keywords=o.aamc_ci_keywords,
            )
            for o in body.learning_objectives
        ],
        prerequisites=body.prerequisites,
        resources=body.resources,
        recording_url=body.recording_url,
        metadata=body.metadata,
    )


def _empty_progress(event_id: str, student_id: str) -> Dict[str, Any]:
    return {
        "event_id": event_id,
        "student_id": student_id,
        "attended": False,
        "lecture_listened": False,
        "recording_watched": False,
        "assignment_completed": False,
        "reading_completed": False,
        "simulation_completed": False,
        "patient_encounter_logged": False,
        "quiz_score": None,
        "exam_score": None,
        "osce_score": None,
        "faculty_observation": None,
        "exposure_level": "none",
        "competency_level": "none",
        "experiential_notes": "",
        "clinical_encounters": [],
        "updated_at": None,
        "xapi_statements": [],
    }


# ── Event endpoints ─────────────────────────────────────────────────────

@router.get("/events")
async def list_events(
    start: Optional[str] = Query(None, description="ISO start date"),
    end: Optional[str] = Query(None, description="ISO end date"),
    year: Optional[int] = Query(None),
    subject: Optional[str] = Query(None),
    block: Optional[str] = Query(None),
    course: Optional[str] = Query(None),
):
    """Return curriculum events filtered by date range, year, subject, block, or course."""
    store = _get_store()
    if start and end:
        events = store.get_events_range(
            date.fromisoformat(start), date.fromisoformat(end)
        )
    elif year is not None:
        events = store.get_events_for_year(year)
    else:
        today = date.today()
        events = store.get_events_range(
            date(today.year, 1, 1), date(today.year, 12, 31)
        )
    if subject:
        events = [e for e in events if e.subject == subject]
    if block:
        events = [e for e in events if e.block == block]
    if course:
        events = [e for e in events if e.course == course]
    return [_event_to_dict(e) for e in events]


@router.get("/events/week")
async def week_events(week_start: str = Query(..., description="ISO Sunday date")):
    store = _get_store()
    return [
        _event_to_dict(e)
        for e in store.get_events_for_week(date.fromisoformat(week_start))
    ]


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    store = _get_store()
    ev = store.get_event(event_id)
    if not ev:
        raise HTTPException(404, "Event not found")
    return _event_to_dict(ev)


@router.post("/events")
async def create_event(body: EventIn):
    store = _get_store()
    ev = _parse_event(body)
    store.save_event(ev)
    return _event_to_dict(ev)


@router.post("/events/bulk")
async def create_events_bulk(body: List[EventIn]):
    store = _get_store()
    events = [_parse_event(b) for b in body]
    store.save_events_bulk(events)
    return {"created": len(events)}


@router.delete("/events/{event_id}")
async def delete_event(event_id: str):
    store = _get_store()
    store.delete_event(event_id)
    return {"deleted": event_id}


# ── Progress endpoints ───────────────────────────────────────────────────

@router.get("/progress/{event_id}/{student_id}")
async def get_progress(event_id: str, student_id: str):
    store = _get_store()
    p = store.get_progress(event_id, student_id)
    if not p:
        return _empty_progress(event_id, student_id)
    return _progress_to_dict(p)


@router.put("/progress")
async def update_progress(body: ProgressIn):
    """Update student progress and auto-generate xAPI statements."""
    store = _get_store()
    ev = store.get_event(body.event_id)
    if not ev:
        raise HTTPException(404, "Event not found")

    prog = StudentProgress(
        event_id=body.event_id,
        student_id=body.student_id,
        attended=body.attended,
        lecture_listened=body.lecture_listened,
        recording_watched=body.recording_watched,
        assignment_completed=body.assignment_completed,
        reading_completed=body.reading_completed,
        simulation_completed=body.simulation_completed,
        patient_encounter_logged=body.patient_encounter_logged,
        quiz_score=body.quiz_score,
        exam_score=body.exam_score,
        osce_score=body.osce_score,
        faculty_observation=body.faculty_observation,
        exposure_level=ExposureLevel(body.exposure_level),
        competency_level=CompetencyLevel(body.competency_level),
        experiential_notes=body.experiential_notes,
        clinical_encounters=body.clinical_encounters,
        updated_at=datetime.now(timezone.utc),
    )

    # Auto-generate xAPI statements
    prog.xapi_statements = _xapi.from_progress(ev, prog)
    store.save_progress(prog)

    # Recompute objective progress for all objectives in this event
    for obj in ev.learning_objectives:
        obj_events = store.get_events_for_objective(obj.id)
        obj_progress = store.get_progress_for_objective(obj.id, body.student_id)
        op = compute_objective_progress(
            obj.id, body.student_id, obj_events, obj_progress
        )
        store.save_objective_progress(op)

    return _progress_to_dict(prog)


@router.get("/progress/range/{student_id}")
async def get_progress_range(
    student_id: str,
    start: str = Query(...),
    end: str = Query(...),
):
    store = _get_store()
    progs = store.get_student_progress_range(
        student_id, date.fromisoformat(start), date.fromisoformat(end)
    )
    return [_progress_to_dict(p) for p in progs]


# ── Objective timeline endpoints ─────────────────────────────────────────

@router.get("/objectives/{objective_id}/timeline")
async def objective_timeline(objective_id: str):
    """Full chronological timeline of events covering this objective."""
    store = _get_store()
    events = store.get_objective_timeline(objective_id)
    return [_event_to_dict(e) for e in events]


@router.get("/objectives/{objective_id}/prior")
async def objective_prior(objective_id: str, before: str = Query(...)):
    """Events covering this objective *before* a given date."""
    store = _get_store()
    events = store.get_prior_events_for_objective(
        objective_id, date.fromisoformat(before)
    )
    return [_event_to_dict(e) for e in events]


@router.get("/objectives/{objective_id}/future")
async def objective_future(objective_id: str, after: str = Query(...)):
    """Events covering this objective *after* a given date."""
    store = _get_store()
    events = store.get_future_events_for_objective(
        objective_id, date.fromisoformat(after)
    )
    return [_event_to_dict(e) for e in events]


@router.get("/objectives/{objective_id}/progress/{student_id}")
async def objective_progress(objective_id: str, student_id: str):
    """Longitudinal objective progress for one learner."""
    store = _get_store()
    op = store.get_objective_progress(objective_id, student_id)
    if not op:
        # Compute on the fly
        obj_events = store.get_events_for_objective(objective_id)
        obj_progs = store.get_progress_for_objective(objective_id, student_id)
        op = compute_objective_progress(
            objective_id, student_id, obj_events, obj_progs
        )
        store.save_objective_progress(op)
    return _obj_progress_to_dict(op)


# ── Competency engine endpoints ──────────────────────────────────────────

@router.get("/competency/{student_id}")
async def competency_summary(
    student_id: str,
    year: Optional[int] = Query(None),
):
    store = _get_store()
    return store.get_competency_summary(student_id, year)


@router.get("/competency/{student_id}/objectives")
async def all_objective_progress(student_id: str):
    """All longitudinal objective progress for a student."""
    store = _get_store()
    ops = store.get_all_objective_progress(student_id)
    return [_obj_progress_to_dict(op) for op in ops]


@router.get("/competency/{student_id}/stale")
async def stale_objectives(student_id: str):
    """Objectives flagged as stale (>90 days since last exposure)."""
    store = _get_store()
    ops = store.get_stale_objectives(student_id)
    return [_obj_progress_to_dict(op) for op in ops]


# ── Metadata endpoints ──────────────────────────────────────────────────

@router.get("/subjects")
async def list_subjects():
    return _get_store().get_subjects()


@router.get("/blocks")
async def list_blocks():
    return _get_store().get_blocks()


@router.get("/courses")
async def list_courses():
    return _get_store().get_courses()


@router.get("/years")
async def list_years():
    return _get_store().get_years()


@router.get("/aamc-domains")
async def aamc_domains():
    return [
        {"value": d.value, "label": d.value.replace("_", " ").title()}
        for d in AAMCDomain
    ]
