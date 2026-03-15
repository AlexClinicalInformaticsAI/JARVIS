"""Competency engine — computes exposure and competency scores.

For each learner-objective pair, derives:
  - exposure score  (attendance, recording, reading, simulation, encounters, recency)
  - competency score (quiz, exam, OSCE, faculty observation, milestone)
  - current colour for each axis
  - trend (improving / stable / declining / stale)
  - recommended next action

Also handles staleness detection and spaced-retrieval recommendations.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from openjarvis.curriculum.models import (
    CompetencyLevel,
    CurriculumEvent,
    ExposureLevel,
    ObjectiveProgress,
    ObjectiveStage,
    StudentProgress,
    STALE_THRESHOLD_DAYS,
)


# ── Exposure scoring ────────────────────────────────────────────────────

# Weights for different engagement modalities
_EXPOSURE_WEIGHTS: Dict[str, float] = {
    "attended": 1.0,
    "lecture_listened": 0.8,
    "recording_watched": 0.6,
    "reading_completed": 0.5,
    "assignment_completed": 0.7,
    "simulation_completed": 1.0,
    "patient_encounter_logged": 1.2,
}

# Modality diversity bonus: more modalities = deeper encoding
_MODALITY_BONUS = 0.15  # per additional modality beyond the first


def compute_exposure_score(progress_records: List[StudentProgress]) -> float:
    """Compute a 0.0–1.0 exposure score across all encounters.

    Factors:
      - engagement type weights
      - modality diversity
      - repetition count (diminishing returns)
      - recency weighting
    """
    if not progress_records:
        return 0.0

    raw = 0.0
    modalities_seen: set = set()

    for p in progress_records:
        record_score = 0.0
        if p.attended:
            record_score += _EXPOSURE_WEIGHTS["attended"]
            modalities_seen.add("lecture")
        if p.lecture_listened:
            record_score += _EXPOSURE_WEIGHTS["lecture_listened"]
            modalities_seen.add("lecture")
        if p.recording_watched:
            record_score += _EXPOSURE_WEIGHTS["recording_watched"]
            modalities_seen.add("recording")
        if p.reading_completed:
            record_score += _EXPOSURE_WEIGHTS["reading_completed"]
            modalities_seen.add("reading")
        if p.assignment_completed:
            record_score += _EXPOSURE_WEIGHTS["assignment_completed"]
            modalities_seen.add("assignment")
        if p.simulation_completed:
            record_score += _EXPOSURE_WEIGHTS["simulation_completed"]
            modalities_seen.add("simulation")
        if p.patient_encounter_logged:
            record_score += _EXPOSURE_WEIGHTS["patient_encounter_logged"]
            modalities_seen.add("clinical")

        raw += record_score

    # Modality diversity bonus
    diversity = max(0, len(modalities_seen) - 1) * _MODALITY_BONUS
    raw += diversity

    # Diminishing returns on repetition (log curve)
    repetition_factor = 1 + 0.3 * math.log1p(len(progress_records) - 1)
    raw *= repetition_factor

    # Normalize to 0–1 (5.0 is a reasonable saturation point)
    return min(1.0, raw / 5.0)


def exposure_to_level(score: float) -> ExposureLevel:
    """Map a 0–1 exposure score to a colour level."""
    if score < 0.15:
        return ExposureLevel.NONE
    if score < 0.35:
        return ExposureLevel.RED
    if score < 0.65:
        return ExposureLevel.YELLOW
    return ExposureLevel.GREEN


# ── Competency scoring ──────────────────────────────────────────────────

def compute_competency_score(progress_records: List[StudentProgress]) -> float:
    """Compute a 0.0–1.0 competency score from assessment evidence.

    Factors:
      - quiz scores (weighted 0.2)
      - exam scores (weighted 0.4)
      - OSCE scores (weighted 0.3)
      - faculty observation presence (weighted 0.1)
      - recency of assessment
    """
    if not progress_records:
        return 0.0

    quiz_scores: List[float] = []
    exam_scores: List[float] = []
    osce_scores: List[float] = []
    has_faculty_obs = False

    for p in progress_records:
        if p.quiz_score is not None:
            quiz_scores.append(p.quiz_score)
        if p.exam_score is not None:
            exam_scores.append(p.exam_score)
        if p.osce_score is not None:
            osce_scores.append(p.osce_score)
        if p.faculty_observation:
            has_faculty_obs = True

    components: List[Tuple[float, float]] = []  # (score, weight)

    if quiz_scores:
        # Use best recent scores (weighted average, latest heavier)
        avg = _recency_weighted_mean(quiz_scores)
        components.append((avg, 0.2))
    if exam_scores:
        avg = _recency_weighted_mean(exam_scores)
        components.append((avg, 0.4))
    if osce_scores:
        avg = _recency_weighted_mean(osce_scores)
        components.append((avg, 0.3))
    if has_faculty_obs:
        components.append((0.7, 0.1))  # faculty obs = baseline pass

    if not components:
        return 0.0

    total_weight = sum(w for _, w in components)
    weighted = sum(s * w for s, w in components) / total_weight
    return min(1.0, max(0.0, weighted))


def competency_to_level(score: float) -> CompetencyLevel:
    """Map a 0–1 competency score to a colour level."""
    if score < 0.1:
        return CompetencyLevel.NONE
    if score < 0.5:
        return CompetencyLevel.RED
    if score < 0.75:
        return CompetencyLevel.YELLOW
    return CompetencyLevel.GREEN


def _recency_weighted_mean(scores: List[float]) -> float:
    """Weighted average where later entries count more."""
    if not scores:
        return 0.0
    n = len(scores)
    weights = [1 + 0.5 * i for i in range(n)]
    total_w = sum(weights)
    return sum(s * w for s, w in zip(scores, weights)) / total_w


# ── Staleness & trend ───────────────────────────────────────────────────

def compute_trend(
    objective_progress: ObjectiveProgress,
    today: Optional[date] = None,
) -> str:
    """Determine the trend for an objective.

    Returns: 'improving' | 'stable' | 'declining' | 'stale'
    """
    today = today or date.today()

    # Check staleness first
    if objective_progress.last_exposure:
        gap = (today - objective_progress.last_exposure).days
        if gap > STALE_THRESHOLD_DAYS:
            return "stale"
    elif objective_progress.stage == ObjectiveStage.NOT_STARTED:
        return "stable"

    # Check assessment trend
    scores = objective_progress.assessment_scores
    if len(scores) >= 2:
        recent = scores[-2:]
        if recent[-1] > recent[-2] + 0.05:
            return "improving"
        if recent[-1] < recent[-2] - 0.05:
            return "declining"
    return "stable"


def compute_recommended_action(
    objective_progress: ObjectiveProgress,
    today: Optional[date] = None,
) -> str:
    """Generate a recommended next action for the learner."""
    today = today or date.today()

    stage = objective_progress.stage
    exp = objective_progress.exposure_level
    comp = objective_progress.competency_level

    # Stale check
    if objective_progress.last_exposure:
        gap = (today - objective_progress.last_exposure).days
        if gap > STALE_THRESHOLD_DAYS:
            return "Review — last exposure was over 90 days ago"

    if stage == ObjectiveStage.NOT_STARTED:
        return "Attend the next session covering this objective"

    if exp == ExposureLevel.NONE or exp == ExposureLevel.RED:
        return "Increase exposure — attend lectures, watch recordings, do readings"

    if comp == CompetencyLevel.NONE:
        return "Take a quiz or assessment to establish baseline competency"

    if comp == CompetencyLevel.RED:
        return "Review material and retake assessment — below expected performance"

    if comp == CompetencyLevel.YELLOW and exp == ExposureLevel.GREEN:
        return "Practice application — try simulation or clinical scenarios"

    if comp == CompetencyLevel.GREEN and stage != ObjectiveStage.APPLIED:
        return "Apply in clinical setting to confirm real-world competence"

    if stage == ObjectiveStage.MASTERED:
        return "Schedule periodic review to prevent competence decay"

    return "Continue current learning path"


# ── Full engine: compute ObjectiveProgress from raw data ─────────────────

def compute_objective_progress(
    objective_id: str,
    student_id: str,
    events: List[CurriculumEvent],
    progress_records: List[StudentProgress],
    today: Optional[date] = None,
) -> ObjectiveProgress:
    """Compute the full longitudinal ObjectiveProgress for one objective.

    Parameters
    ----------
    events
        All curriculum events that contain this objective.
    progress_records
        Student progress for those events (matched by event_id).
    """
    today = today or date.today()

    # Filter progress records that have matching events
    event_ids = {e.id for e in events}
    relevant = [p for p in progress_records if p.event_id in event_ids]

    exp_score = compute_exposure_score(relevant)
    comp_score = compute_competency_score(relevant)
    exp_level = exposure_to_level(exp_score)
    comp_level = competency_to_level(comp_score)

    # Collect modalities
    modalities: set = set()
    first_exp: Optional[date] = None
    last_exp: Optional[date] = None
    last_assessed: Optional[date] = None
    last_applied: Optional[date] = None
    assessment_scores: List[float] = []
    encounter_count = 0

    for ev, p in _match_events_progress(events, relevant):
        if not _has_engagement(p):
            continue
        encounter_count += 1

        if p.attended or p.lecture_listened:
            modalities.add("lecture")
        if p.recording_watched:
            modalities.add("recording")
        if p.reading_completed:
            modalities.add("reading")
        if p.assignment_completed:
            modalities.add("assignment")
        if p.simulation_completed:
            modalities.add("simulation")
        if p.patient_encounter_logged:
            modalities.add("clinical")

        if first_exp is None or ev.date < first_exp:
            first_exp = ev.date
        if last_exp is None or ev.date > last_exp:
            last_exp = ev.date

        for score in [p.quiz_score, p.exam_score, p.osce_score]:
            if score is not None:
                assessment_scores.append(score)
                last_assessed = ev.date

        if ev.event_type.value in ("clinical", "patient_encounter", "simulation", "osce"):
            last_applied = ev.date

    # Determine stage
    stage = _determine_stage(
        encounter_count, modalities, assessment_scores,
        last_applied, comp_level, last_exp, today,
    )

    obj = ObjectiveProgress(
        objective_id=objective_id,
        student_id=student_id,
        stage=stage,
        exposure_level=exp_level,
        competency_level=comp_level,
        encounter_count=encounter_count,
        modalities_seen=sorted(modalities),
        first_exposure=first_exp,
        last_exposure=last_exp,
        last_assessed=last_assessed,
        last_applied=last_applied,
        assessment_scores=assessment_scores,
        days_since_last_exposure=(
            (today - last_exp).days if last_exp else None
        ),
    )

    obj.trend = compute_trend(obj, today)
    obj.recommended_action = compute_recommended_action(obj, today)
    return obj


# ── Internal helpers ─────────────────────────────────────────────────────

def _match_events_progress(
    events: List[CurriculumEvent],
    progress: List[StudentProgress],
) -> List[tuple]:
    """Pair events with their progress records."""
    prog_map = {p.event_id: p for p in progress}
    pairs = []
    for ev in sorted(events, key=lambda e: e.date):
        p = prog_map.get(ev.id)
        if p:
            pairs.append((ev, p))
    return pairs


def _has_engagement(p: StudentProgress) -> bool:
    return (
        p.attended or p.lecture_listened or p.recording_watched
        or p.assignment_completed or p.reading_completed
        or p.simulation_completed or p.patient_encounter_logged
    )


def _determine_stage(
    encounter_count: int,
    modalities: set,
    assessment_scores: List[float],
    last_applied: Optional[date],
    comp_level: CompetencyLevel,
    last_exp: Optional[date],
    today: date,
) -> ObjectiveStage:
    """Determine the lifecycle stage of an objective."""
    if encounter_count == 0:
        return ObjectiveStage.NOT_STARTED

    # Check staleness
    if last_exp and (today - last_exp).days > STALE_THRESHOLD_DAYS:
        return ObjectiveStage.STALE

    if comp_level == CompetencyLevel.GREEN:
        if last_applied:
            return ObjectiveStage.MASTERED
        return ObjectiveStage.ASSESSED

    if last_applied:
        return ObjectiveStage.APPLIED

    if assessment_scores:
        return ObjectiveStage.ASSESSED

    if len(modalities) >= 2 or encounter_count >= 3:
        return ObjectiveStage.PRACTISED

    if encounter_count >= 2:
        return ObjectiveStage.REVISITED

    return ObjectiveStage.INTRODUCED
