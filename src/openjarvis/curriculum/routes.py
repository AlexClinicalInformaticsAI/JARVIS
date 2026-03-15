"""FastAPI routes for curriculum calendar and student progress.

Mounted under ``/v1/curriculum`` by the main app.
"""

from __future__ import annotations

import os
from datetime import date, datetime, time, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from openjarvis.curriculum.models import (
    AAMCDomain,
    CompetencyLevel,
    CurriculumEvent,
    EventType,
    LearningObjective,
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


class EventIn(BaseModel):
    id: str
    title: str
    event_type: str = "lecture"
    subject: str
    topic: str
    date: str                    # ISO date
    start_time: str              # HH:MM
    end_time: str                # HH:MM
    year: int
    block: str = ""
    location: str = ""
    instructor: str = ""
    description: str = ""
    learning_objectives: List[LearningObjectiveIn] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    resources: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProgressIn(BaseModel):
    event_id: str
    student_id: str
    attended: bool = False
    lecture_listened: bool = False
    assignment_completed: bool = False
    quiz_score: Optional[float] = None
    exam_score: Optional[float] = None
    competency_level: str = "none"
    experiential_notes: str = ""


class ProgressOut(BaseModel):
    event_id: str
    student_id: str
    attended: bool
    lecture_listened: bool
    assignment_completed: bool
    quiz_score: Optional[float]
    exam_score: Optional[float]
    competency_level: str
    experiential_notes: str
    updated_at: Optional[str]
    xapi_statements: List[Dict[str, Any]]


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
            }
            for o in ev.learning_objectives
        ],
        "prerequisites": ev.prerequisites,
        "resources": ev.resources,
        "metadata": ev.metadata,
    }


def _progress_to_out(p: StudentProgress) -> ProgressOut:
    return ProgressOut(
        event_id=p.event_id,
        student_id=p.student_id,
        attended=p.attended,
        lecture_listened=p.lecture_listened,
        assignment_completed=p.assignment_completed,
        quiz_score=p.quiz_score,
        exam_score=p.exam_score,
        competency_level=p.competency_level.value,
        experiential_notes=p.experiential_notes,
        updated_at=p.updated_at.isoformat() if p.updated_at else None,
        xapi_statements=p.xapi_statements,
    )


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
            )
            for o in body.learning_objectives
        ],
        prerequisites=body.prerequisites,
        resources=body.resources,
        metadata=body.metadata,
    )


# ── Event endpoints ─────────────────────────────────────────────────────

@router.get("/events")
async def list_events(
    start: Optional[str] = Query(None, description="ISO start date"),
    end: Optional[str] = Query(None, description="ISO end date"),
    year: Optional[int] = Query(None),
    subject: Optional[str] = Query(None),
):
    """Return curriculum events filtered by date range, year, or subject."""
    store = _get_store()
    if start and end:
        events = store.get_events_range(
            date.fromisoformat(start), date.fromisoformat(end)
        )
    elif year is not None:
        events = store.get_events_for_year(year)
    else:
        # default: current calendar year
        today = date.today()
        events = store.get_events_range(
            date(today.year, 1, 1), date(today.year, 12, 31)
        )
    if subject:
        events = [e for e in events if e.subject == subject]
    return [_event_to_dict(e) for e in events]


@router.get("/events/week")
async def week_events(week_start: str = Query(..., description="ISO Sunday date")):
    """Return events for the week starting on *week_start* (Sunday)."""
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
        return ProgressOut(
            event_id=event_id,
            student_id=student_id,
            attended=False,
            lecture_listened=False,
            assignment_completed=False,
            quiz_score=None,
            exam_score=None,
            competency_level="none",
            experiential_notes="",
            updated_at=None,
            xapi_statements=[],
        )
    return _progress_to_out(p)


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
        assignment_completed=body.assignment_completed,
        quiz_score=body.quiz_score,
        exam_score=body.exam_score,
        competency_level=CompetencyLevel(body.competency_level),
        experiential_notes=body.experiential_notes,
        updated_at=datetime.now(timezone.utc),
    )

    # Auto-generate xAPI statements
    prog.xapi_statements = _xapi.from_progress(ev, prog)
    store.save_progress(prog)
    return _progress_to_out(prog)


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
    return [_progress_to_out(p) for p in progs]


@router.get("/competency/{student_id}")
async def competency_summary(
    student_id: str,
    year: Optional[int] = Query(None),
):
    store = _get_store()
    return store.get_competency_summary(student_id, year)


# ── Metadata endpoints ──────────────────────────────────────────────────

@router.get("/subjects")
async def list_subjects():
    return _get_store().get_subjects()


@router.get("/years")
async def list_years():
    return _get_store().get_years()


@router.get("/aamc-domains")
async def aamc_domains():
    """Return AAMC competency domains with labels."""
    return [
        {"value": d.value, "label": d.value.replace("_", " ").title()}
        for d in AAMCDomain
    ]
