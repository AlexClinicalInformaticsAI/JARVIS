"""SQLite-backed persistence for curriculum events, student progress,
and longitudinal objective tracking."""

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
    ExposureLevel,
    LearningObjective,
    ObjectiveProgress,
    ObjectiveStage,
    StudentProgress,
)

# ── Table DDL ────────────────────────────────────────────────────────────

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
    course          TEXT NOT NULL DEFAULT '',
    clerkship       TEXT NOT NULL DEFAULT '',
    location        TEXT NOT NULL DEFAULT '',
    instructor      TEXT NOT NULL DEFAULT '',
    description     TEXT NOT NULL DEFAULT '',
    learning_objectives TEXT NOT NULL DEFAULT '[]',
    prerequisites   TEXT NOT NULL DEFAULT '[]',
    resources       TEXT NOT NULL DEFAULT '[]',
    recording_url   TEXT NOT NULL DEFAULT '',
    metadata        TEXT NOT NULL DEFAULT '{}'
);
"""

_CREATE_PROGRESS = """\
CREATE TABLE IF NOT EXISTS student_progress (
    event_id            TEXT NOT NULL,
    student_id          TEXT NOT NULL,
    attended            INTEGER NOT NULL DEFAULT 0,
    lecture_listened    INTEGER NOT NULL DEFAULT 0,
    recording_watched   INTEGER NOT NULL DEFAULT 0,
    assignment_completed INTEGER NOT NULL DEFAULT 0,
    reading_completed   INTEGER NOT NULL DEFAULT 0,
    simulation_completed INTEGER NOT NULL DEFAULT 0,
    patient_encounter_logged INTEGER NOT NULL DEFAULT 0,
    quiz_score          REAL,
    exam_score          REAL,
    osce_score          REAL,
    faculty_observation TEXT,
    exposure_level      TEXT NOT NULL DEFAULT 'none',
    competency_level    TEXT NOT NULL DEFAULT 'none',
    experiential_notes  TEXT NOT NULL DEFAULT '',
    clinical_encounters TEXT NOT NULL DEFAULT '[]',
    updated_at          TEXT,
    xapi_statements     TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (event_id, student_id)
);
"""

_CREATE_OBJ_PROGRESS = """\
CREATE TABLE IF NOT EXISTS objective_progress (
    objective_id    TEXT NOT NULL,
    student_id      TEXT NOT NULL,
    stage           TEXT NOT NULL DEFAULT 'not_started',
    exposure_level  TEXT NOT NULL DEFAULT 'none',
    competency_level TEXT NOT NULL DEFAULT 'none',
    encounter_count INTEGER NOT NULL DEFAULT 0,
    modalities_seen TEXT NOT NULL DEFAULT '[]',
    first_exposure  TEXT,
    last_exposure   TEXT,
    last_assessed   TEXT,
    last_applied    TEXT,
    assessment_scores TEXT NOT NULL DEFAULT '[]',
    trend           TEXT NOT NULL DEFAULT 'stable',
    days_since_last_exposure INTEGER,
    recommended_action TEXT NOT NULL DEFAULT '',
    updated_at      TEXT,
    PRIMARY KEY (objective_id, student_id)
);
"""

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_events_date ON curriculum_events (date);",
    "CREATE INDEX IF NOT EXISTS idx_events_year ON curriculum_events (year);",
    "CREATE INDEX IF NOT EXISTS idx_events_subject ON curriculum_events (subject);",
    "CREATE INDEX IF NOT EXISTS idx_events_block ON curriculum_events (block);",
    "CREATE INDEX IF NOT EXISTS idx_events_course ON curriculum_events (course);",
    "CREATE INDEX IF NOT EXISTS idx_progress_student ON student_progress (student_id);",
    "CREATE INDEX IF NOT EXISTS idx_obj_progress_student ON objective_progress (student_id);",
]


class CurriculumStore:
    """SQLite CRUD store for curriculum events, progress, and objectives."""

    def __init__(self, db_path: str | Path) -> None:
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_CREATE_EVENTS)
        self._conn.execute(_CREATE_PROGRESS)
        self._conn.execute(_CREATE_OBJ_PROGRESS)
        for idx in _INDEXES:
            self._conn.execute(idx)
        self._conn.commit()

    # ── Events ───────────────────────────────────────────────────────────

    def save_event(self, event: CurriculumEvent) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO curriculum_events "
            "(id, title, event_type, subject, topic, date, start_time, "
            "end_time, year, block, course, clerkship, location, instructor, "
            "description, learning_objectives, prerequisites, resources, "
            "recording_url, metadata) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
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
                event.course,
                event.clerkship,
                event.location,
                event.instructor,
                event.description,
                json.dumps([_obj_to_dict(o) for o in event.learning_objectives]),
                json.dumps(event.prerequisites),
                json.dumps(event.resources),
                event.recording_url,
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

    def get_blocks(self) -> List[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT block FROM curriculum_events WHERE block != '' ORDER BY block"
        ).fetchall()
        return [r["block"] for r in rows]

    def get_courses(self) -> List[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT course FROM curriculum_events WHERE course != '' ORDER BY course"
        ).fetchall()
        return [r["course"] for r in rows]

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

    # ── Objective → Event linking ────────────────────────────────────────

    def get_events_for_objective(self, objective_id: str) -> List[CurriculumEvent]:
        """Find all events that contain a given learning objective.

        This powers the 'previously covered' / 'will be covered' feature.
        """
        rows = self._conn.execute(
            "SELECT * FROM curriculum_events ORDER BY date, start_time"
        ).fetchall()
        result = []
        for r in rows:
            ev = _row_to_event(r)
            if any(o.id == objective_id for o in ev.learning_objectives):
                result.append(ev)
        return result

    def get_prior_events_for_objective(
        self, objective_id: str, before: date
    ) -> List[CurriculumEvent]:
        """Sessions covering the same objective *before* a given date."""
        all_events = self.get_events_for_objective(objective_id)
        return [e for e in all_events if e.date < before]

    def get_future_events_for_objective(
        self, objective_id: str, after: date
    ) -> List[CurriculumEvent]:
        """Sessions covering the same objective *after* a given date."""
        all_events = self.get_events_for_objective(objective_id)
        return [e for e in all_events if e.date > after]

    def get_objective_timeline(
        self, objective_id: str
    ) -> List[CurriculumEvent]:
        """Full timeline of events covering an objective (chronological)."""
        return self.get_events_for_objective(objective_id)

    # ── Student Progress ─────────────────────────────────────────────────

    def save_progress(self, p: StudentProgress) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO student_progress "
            "(event_id, student_id, attended, lecture_listened, "
            "recording_watched, assignment_completed, reading_completed, "
            "simulation_completed, patient_encounter_logged, "
            "quiz_score, exam_score, osce_score, faculty_observation, "
            "exposure_level, competency_level, "
            "experiential_notes, clinical_encounters, updated_at, xapi_statements) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                p.event_id,
                p.student_id,
                int(p.attended),
                int(p.lecture_listened),
                int(p.recording_watched),
                int(p.assignment_completed),
                int(p.reading_completed),
                int(p.simulation_completed),
                int(p.patient_encounter_logged),
                p.quiz_score,
                p.exam_score,
                p.osce_score,
                p.faculty_observation,
                p.exposure_level.value,
                p.competency_level.value,
                p.experiential_notes,
                json.dumps(p.clinical_encounters),
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

    def get_progress_for_objective(
        self, objective_id: str, student_id: str
    ) -> List[StudentProgress]:
        """Get all progress records for events containing a given objective."""
        events = self.get_events_for_objective(objective_id)
        result = []
        for ev in events:
            p = self.get_progress(ev.id, student_id)
            if p:
                result.append(p)
        return result

    def get_competency_summary(
        self, student_id: str, year: Optional[int] = None
    ) -> Dict[str, Any]:
        """Aggregate competency + exposure counts."""
        q = (
            "SELECT sp.competency_level, sp.exposure_level, COUNT(*) as cnt "
            "FROM student_progress sp "
            "JOIN curriculum_events ce ON sp.event_id = ce.id "
            "WHERE sp.student_id = ?"
        )
        params: list = [student_id]
        if year is not None:
            q += " AND ce.year = ?"
            params.append(year)
        q += " GROUP BY sp.competency_level, sp.exposure_level"
        rows = self._conn.execute(q, params).fetchall()
        return {
            "by_competency": {},
            "by_exposure": {},
            "combined": [
                {
                    "competency": r["competency_level"],
                    "exposure": r["exposure_level"],
                    "count": r["cnt"],
                }
                for r in rows
            ],
        }

    # ── Objective Progress (longitudinal) ────────────────────────────────

    def save_objective_progress(self, op: ObjectiveProgress) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO objective_progress "
            "(objective_id, student_id, stage, exposure_level, competency_level, "
            "encounter_count, modalities_seen, first_exposure, last_exposure, "
            "last_assessed, last_applied, assessment_scores, trend, "
            "days_since_last_exposure, recommended_action, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                op.objective_id,
                op.student_id,
                op.stage.value,
                op.exposure_level.value,
                op.competency_level.value,
                op.encounter_count,
                json.dumps(op.modalities_seen),
                op.first_exposure.isoformat() if op.first_exposure else None,
                op.last_exposure.isoformat() if op.last_exposure else None,
                op.last_assessed.isoformat() if op.last_assessed else None,
                op.last_applied.isoformat() if op.last_applied else None,
                json.dumps(op.assessment_scores),
                op.trend,
                op.days_since_last_exposure,
                op.recommended_action,
                op.updated_at.isoformat() if op.updated_at else None,
            ),
        )
        self._conn.commit()

    def get_objective_progress(
        self, objective_id: str, student_id: str
    ) -> Optional[ObjectiveProgress]:
        row = self._conn.execute(
            "SELECT * FROM objective_progress "
            "WHERE objective_id = ? AND student_id = ?",
            (objective_id, student_id),
        ).fetchone()
        return _row_to_obj_progress(row) if row else None

    def get_all_objective_progress(
        self, student_id: str
    ) -> List[ObjectiveProgress]:
        rows = self._conn.execute(
            "SELECT * FROM objective_progress WHERE student_id = ?",
            (student_id,),
        ).fetchall()
        return [_row_to_obj_progress(r) for r in rows]

    def get_stale_objectives(
        self, student_id: str
    ) -> List[ObjectiveProgress]:
        rows = self._conn.execute(
            "SELECT * FROM objective_progress "
            "WHERE student_id = ? AND stage = 'stale'",
            (student_id,),
        ).fetchall()
        return [_row_to_obj_progress(r) for r in rows]

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
        "aamc_ci_keywords": obj.aamc_ci_keywords,
    }


def _dict_to_obj(d: Dict[str, Any]) -> LearningObjective:
    return LearningObjective(
        id=d["id"],
        description=d["description"],
        aamc_domain=AAMCDomain(d["aamc_domain"]),
        bloom_level=d.get("bloom_level", "recall"),
        epa_mapping=d.get("epa_mapping"),
        tags=d.get("tags", []),
        aamc_ci_keywords=d.get("aamc_ci_keywords", []),
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
        course=d.get("course", ""),
        clerkship=d.get("clerkship", ""),
        location=d.get("location", ""),
        instructor=d.get("instructor", ""),
        description=d.get("description", ""),
        learning_objectives=[
            _dict_to_obj(o) for o in json.loads(d.get("learning_objectives", "[]"))
        ],
        prerequisites=json.loads(d.get("prerequisites", "[]")),
        resources=json.loads(d.get("resources", "[]")),
        recording_url=d.get("recording_url", ""),
        metadata=json.loads(d.get("metadata", "{}")),
    )


def _row_to_progress(row: sqlite3.Row) -> StudentProgress:
    d = dict(row)
    return StudentProgress(
        event_id=d["event_id"],
        student_id=d["student_id"],
        attended=bool(d["attended"]),
        lecture_listened=bool(d["lecture_listened"]),
        recording_watched=bool(d.get("recording_watched", 0)),
        assignment_completed=bool(d["assignment_completed"]),
        reading_completed=bool(d.get("reading_completed", 0)),
        simulation_completed=bool(d.get("simulation_completed", 0)),
        patient_encounter_logged=bool(d.get("patient_encounter_logged", 0)),
        quiz_score=d.get("quiz_score"),
        exam_score=d.get("exam_score"),
        osce_score=d.get("osce_score"),
        faculty_observation=d.get("faculty_observation"),
        exposure_level=ExposureLevel(d.get("exposure_level", "none")),
        competency_level=CompetencyLevel(d.get("competency_level", "none")),
        experiential_notes=d.get("experiential_notes", ""),
        clinical_encounters=json.loads(d.get("clinical_encounters", "[]")),
        updated_at=(
            datetime.fromisoformat(d["updated_at"]) if d.get("updated_at") else None
        ),
        xapi_statements=json.loads(d.get("xapi_statements", "[]")),
    )


def _row_to_obj_progress(row: sqlite3.Row) -> ObjectiveProgress:
    d = dict(row)
    return ObjectiveProgress(
        objective_id=d["objective_id"],
        student_id=d["student_id"],
        stage=ObjectiveStage(d.get("stage", "not_started")),
        exposure_level=ExposureLevel(d.get("exposure_level", "none")),
        competency_level=CompetencyLevel(d.get("competency_level", "none")),
        encounter_count=d.get("encounter_count", 0),
        modalities_seen=json.loads(d.get("modalities_seen", "[]")),
        first_exposure=(
            date.fromisoformat(d["first_exposure"]) if d.get("first_exposure") else None
        ),
        last_exposure=(
            date.fromisoformat(d["last_exposure"]) if d.get("last_exposure") else None
        ),
        last_assessed=(
            date.fromisoformat(d["last_assessed"]) if d.get("last_assessed") else None
        ),
        last_applied=(
            date.fromisoformat(d["last_applied"]) if d.get("last_applied") else None
        ),
        assessment_scores=json.loads(d.get("assessment_scores", "[]")),
        trend=d.get("trend", "stable"),
        days_since_last_exposure=d.get("days_since_last_exposure"),
        recommended_action=d.get("recommended_action", ""),
        updated_at=(
            datetime.fromisoformat(d["updated_at"]) if d.get("updated_at") else None
        ),
    )
