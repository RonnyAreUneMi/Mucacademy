"""Calificación de evaluaciones compartida por la web y la API móvil."""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from core.models import EvaluationAttempt

log = logging.getLogger(__name__)


def grade_and_record(evaluation, participant, answers: dict) -> dict | None:
    """Califica, registra el intento y emite certificados al aprobar.

    Devuelve un dict con score/correct/total/passed/detail/attempt, o None si
    no llegó ninguna respuesta válida. No verifica intentos disponibles: eso lo
    hace el llamador.
    """
    q_map = {str(q.id): q for q in evaluation.active_questions}
    graded_ids = [qid for qid in answers.keys() if qid in q_map]
    if not graded_ids:
        return None

    correct = 0
    detail = []
    for qid in graded_ids:
        q = q_map[qid]
        try:
            chosen = int(answers[qid])
        except (TypeError, ValueError):
            chosen = -1
        is_ok = (chosen == q.correct_idx)
        correct += int(is_ok)
        detail.append({
            'question_id': q.id,
            'chosen_idx': chosen,
            'correct_idx': q.correct_idx,
            'is_correct': is_ok,
            'explanation': q.explanation,
        })

    total = len(graded_ids)
    score = round(correct / total * 100, 1) if total else 0.0
    passed = score >= evaluation.pass_threshold

    attempt = EvaluationAttempt.objects.create(
        evaluation=evaluation, participant=participant,
        attempt_number=evaluation.attempts_used_by(participant) + 1,
        answers={k: answers[k] for k in graded_ids},
        question_ids=[int(x) for x in graded_ids],
        correct=correct, total=total, score=score, passed=passed,
        submitted_at=timezone.now(),
    )

    if passed:
        _auto_issue_on_pass(evaluation, participant)

    return {
        'attempt': attempt,
        'score': score,
        'correct': correct,
        'total': total,
        'passed': passed,
        'detail': detail,
    }


def _auto_issue_on_pass(evaluation, participant) -> None:
    """Emite certificados de seminario y/o programa (best-effort, nunca propaga)."""
    from core.services import programs as program_service
    try:
        with transaction.atomic():
            if evaluation.event_id:
                event = evaluation.event
                program_service.issue_seminar_certificate(event, participant)
                if event.program_id:
                    program_service.check_and_issue(event.program, participant)
            elif evaluation.program_id:
                program_service.check_and_issue(evaluation.program, participant)
    except Exception:
        log.exception(
            'Auto-issue de certificados fallo: evaluation=%s participant=%s',
            getattr(evaluation, 'id', None), getattr(participant, 'id', None),
        )
