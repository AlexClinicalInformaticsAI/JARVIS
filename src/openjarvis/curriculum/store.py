"""SQLite-backed persistence for curriculum events and student progress."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Dict, List, Optional

from openjarvis.curriculum.models import (
    AAMCDomain,
    CompetencyLevel,
    CurriculumEvent,
    EventType,
    LearningObjective,
    StudentProgress,
)

_CREATE_EVENTS = """\
CREATE TABLE IF NOT EXISTS curriculum_events (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    subject         TEXT NOT NULL,
    topic           TEXT NOT NULL,
    date            TEXT NOT NULL,
    start_time      TEXT NOT NULL,
    end_time        TEXT NOT NULL,
    year            INTEGER NOT NULL,
    block           TEXT NOT NULL DEFAULT '',
    location        TEXT NOT NULL DEFAULT '',
    instructor      TEXT NOT NULL DEFAULT '',
    description     TEXT NOT NULL DEFAULT '',
    learning_objectives TEXT NOT NULL DEFAULT '[]',
    prerequisites   TEXT NOT NULL DEFAULT '[]',
    resources       TEXT NOT NULL DEFAULT '[]',
    metadata        TEXT NOT NULL DEFAULT '{}'
);
"""

_CREATE_PROGRESS = """\
CREATE TABLE IF NOT EXISTS student_progress (
    event_id            TEXT NOT NULL,
    student_id          TEXT NOT NULL,
    attended            INTEGER NOT NULL DEFAULT 0,
    lecture_listened    INTEGER NOT NULL DEFAULT 0,
    assignment_completed INTEGER NOT NULL DEFAULT 0,
    quiz_score          REAL,
    exam_score          REAL,
    competency_level    TEXT NOT NULL DEFAULT 'none',
    experiential_notes  TEXT NOT NULL DEFAULT '',
    updated_at          TEXT,
    xapi_statements     TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (event_id, student_id)
);
"""

_CREATE_IDX_DATE = """\
CREATE INDEX IF NOT EXISTS idx_events_date ON curriculum_events (date);
"""
_CREATE_IDX_YEAR = """\
CREATE INDEX IF NOT EXISTS idx_events_year ON curriculum_events (year);
"""
_CREATE_IDX_SUBJECT = """\
CREATE INDEX IF NOT EXISTS idx_events_subject ON curriculum_events (subject);
"""


class CurriculumStore:
    """SQLite CRUD store for curriculum events and student progress."""

    def __init__(self, db_path: str | Path) -> None:
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_CREATE_EVENTS)
        self._conn.execute(_CREATE_PROGRESS)
        self._conn.execute(_CREATE_IDX_DATE)
        self._conn.execute(_CREATE_IDX_YEAR)
        self._conn.execute(_CREATE_IDX_SUBJECT)
        self._conn.commit()

    # ── Events ───────────────────────────────────────────────────────────

    def save_event(self, event: CurriculumEvent) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO curriculum_events "
            "(id, title, event_type, subject, topic, date, start_time, "
            "end_time, year, block, location, instructor, description, "
            "learning_objectives, prerequisites, resources, metadata) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                event.id,
                event.title,
                event.event_type.value,
                event.subject,
                event.topic,
                event.date.isoformat(),
                event.start_time.isoformat(),
                event.end_time.isoformat(),
                event.year,
                event.block,
                event.location,
                event.instructor,
                event.description,
                json.dumps([_obj_to_dict(o) for o in event.learning_objectives]),
                json.dumps(event.prerequisites),
                json.dumps(event.resources),
                json.dumps(event.metadata),
            ),
        )
        self._conn.commit()

    def save_events_bulk(self, events: List[CurriculumEvent]) -> None:
        for ev in events:
            self.save_event(ev)

    def get_event(self, event_id: str) -> Optional[CurriculumEvent]:
        row = self._conn.execute(
            "SELECT * FROM curriculum_events WHERE id = ?", (event_id,)
        ).fetchone()
        return _row_to_event(row) if row else None

    def get_events_for_date(self, d: date) -> List[CurriculumEvent]:
        rows = self._conn.execute(
            "SELECT * FROM curriculum_events WHERE date = ? ORDER BY start_time",
            (d.isoformat(),),
        ).fetchall()
        return [_row_to_event(r) for r in rows]

    def get_events_for_week(self, week_start: date) -> List[CurriculumEvent]:
        """Return events for 7 days starting from *week_start* (Sunday)."""
        from datetime import timedelta

        end = week_start + timedelta(days=6)
        rows = self._conn.execute(
            "SELECT * FROM curriculum_events "
            "WHERE date >= ? AND date <= ? ORDER BY date, start_time",
            (week_start.isoformat(), end.isoformat()),
        ).fetchall()
        return [_row_to_event(r) for r in rows]

    def get_events_for_year(self, year: int) -> List[CurriculumEvent]:
        rows = self._conn.execute(
            "SELECT * FROM curriculum_events WHERE year = ? ORDER BY date, start_time",
            (year,),
        ).fetchall()
        return [_row_to_event(r) for r in rows]

    def get_events_range(self, start: date, end: date) -> List[CurriculumEvent]:
        rows = self._conn.execute(
            "SELECT * FROM curriculum_events "
            "WHERE date >= ? AND date <= ? ORDER BY date, start_time",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [_row_to_event(r) for r in rows]

    def get_subjects(self) -> List[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT subject FROM curriculum_events ORDER BY subject"
        ).fetchall()
        return [r["subject"] for r in rows]

    def get_years(self) -> List[int]:
        rows = self._conn.execute(
            "SELECT DISTINCT year FROM curriculum_events ORDER BY year"
        ).fetchall()
        return [r["year"] for r in rows]

    def delete_event(self, event_id: str) -> None:
        self._conn.execute(
            "DELETE FROM curriculum_events WHERE id = ?", (event_id,)
        )
        self._conn.commit()

    # ── Student Progress ─────────────────────────────────────────────────

    def save_progress(self, p: StudentProgress) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO student_progress "
            "(event_id, student_id, attended, lecture_listened, "
            "assignment_completed, quiz_score, exam_score, competency_level, "
            "experiential_notes, updated_at, xapi_statements) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                p.event_id,
                p.student_id,
                int(p.attended),
                int(p.lecture_listened),
                int(p.assignment_completed),
                p.quiz_score,
                p.exam_score,
                p.competency_level.value,
                p.experiential_notes,
                p.updated_at.isoformat() if p.updated_at else None,
                json.dumps(p.xapi_statements),
            ),
        )
        self._conn.commit()

    def get_progress(
        self, event_id: str, student_id: str
    ) -> Optional[StudentProgress]:
        row = self._conn.execute(
            "SELECT * FROM student_progress "
            "WHERE event_id = ? AND student_id = ?",
            (event_id, student_id),
        ).fetchone()
        return _row_to_progress(row) if row else None

    def get_student_progress_range(
        self, student_id: str, start: date, end: date
    ) -> List[StudentProgress]:
        rows = self._conn.execute(
            "SELECT sp.* FROM student_progress sp "
            "JOIN curriculum_events ce ON sp.event_id = ce.id "
            "WHERE sp.student_id = ? AND ce.date >= ? AND ce.date <= ? "
            "ORDER BY ce.date, ce.start_time",
            (student_id, start.isoformat(), end.isoformat()),
        ).fetchall()
        return [_row_to_progress(r) for r in rows]

    def get_competency_summary(
        self, student_id: str, year: Optional[int] = None
    ) -> Dict[str, Any]:
        """Aggregate competency counts across events."""
        q = (
            "SELECT sp.competency_level, COUNT(*) as cnt "
            "FROM student_progress sp "
            "JOIN curriculum_events ce ON sp.event_id = ce.id "
            "WHERE sp.student_id = ?"
        )
        params: list = [student_id]
        if year is not None:
            q += " AND ce.year = ?"
            params.append(year)
        q += " GROUP BY sp.competency_level"
        rows = self._conn.execute(q, params).fetchall()
        return {r["competency_level"]: r["cnt"] for r in rows}

    # ── Lifecycle ────────────────────────────────────────────────────────

    def close(self) -> None:
        self._conn.close()


# ── Row conversion helpers ───────────────────────────────────────────────

def _obj_to_dict(obj: LearningObjective) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "description": obj.description,
        "aamc_domain": obj.aamc_domain.value,
        "bloom_level": obj.bloom_level,
        "epa_mapping": obj.epa_mapping,
        "tags": obj.tags,
    }


def _dict_to_obj(d: Dict[str, Any]) -> LearningObjective:
    return LearningObjective(
        id=d["id"],
        description=d["description"],
        aamc_domain=AAMCDomain(d["aamc_domain"]),
        bloom_level=d.get("bloom_level", "recall"),
        epa_mapping=d.get("epa_mapping"),
        tags=d.get("tags", []),
    )


def _row_to_event(row: sqlite3.Row) -> CurriculumEvent:
    d = dict(row)
    return CurriculumEvent(
        id=d["id"],
        title=d["title"],
        event_type=EventType(d["event_type"]),
        subject=d["subject"],
        topic=d["topic"],
        date=date.fromisoformat(d["date"]),
        start_time=time.fromisoformat(d["start_time"]),
        end_time=time.fromisoformat(d["end_time"]),
        year=d["year"],
        block=d.get("block", ""),
        location=d.get("location", ""),
        instructor=d.get("instructor", ""),
        description=d.get("description", ""),
        learning_objectives=[
            _dict_to_obj(o) for o in json.loads(d.get("learning_objectives", "[]"))
        ],
        prerequisites=json.loads(d.get("prerequisites", "[]")),
        resources=json.loads(d.get("resources", "[]")),
        metadata=json.loads(d.get("metadata", "{}")),
    )


def _row_to_progress(row: sqlite3.Row) -> StudentProgress:
    d = dict(row)
    return StudentProgress(
        event_id=d["event_id"],
        student_id=d["student_id"],
        attended=bool(d["attended"]),
        lecture_listened=bool(d["lecture_listened"]),
        assignment_completed=bool(d["assignment_completed"]),
        quiz_score=d.get("quiz_score"),
        exam_score=d.get("exam_score"),
        competency_level=CompetencyLevel(d.get("competency_level", "none")),
        experiential_notes=d.get("experiential_notes", ""),
        updated_at=(
            datetime.fromisoformat(d["updated_at"]) if d.get("updated_at") else None
        ),
        xapi_statements=json.loads(d.get("xapi_statements", "[]")),
    )
