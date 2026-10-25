"""Deterministic seven-day portfolio plan templates for validated assessments."""

import re

from models import (
    AnalysisValidationError,
    PlanDay,
    select_priority_assessments,
    validate_ordered_days,
    validate_plan_alignment,
)


_DATA_SKILL = re.compile(
    r"\b(?:sql|excel|spreadsheet|python|pandas|power\s*bi|tableau|dashboard|"
    r"data analys|data clean|statistics|visuali[sz]ation|database|query)\b",
    re.IGNORECASE,
)
_ASSUMPTIONS_GAP = re.compile(r"\bassumptions?\b.*\b(?:document|log|register|section)\b|\b(?:document|log|register|section)\b.*\bassumptions?\b", re.IGNORECASE)


def _artifact_name(skill_name: str, gap: str) -> str:
    """Choose a familiar output type from the assessed skill/gap wording."""
    text = f"{skill_name} {gap}".casefold()
    if "sql" in text or "query" in text or "database" in text:
        return "SQL query file"
    if "power bi" in text or "dashboard" in text or "visualization" in text or "visualisation" in text:
        return "dashboard file"
    if "excel" in text or "spreadsheet" in text:
        return "spreadsheet workbook"
    if "python" in text or "pandas" in text:
        return "Python analysis notebook"
    if "assumption" in text and any(term in text for term in ("document", "log", "register", "section")):
        return "assumptions document"
    if any(term in text for term in ("communication", "presentation", "reporting")):
        return "findings summary"
    if any(term in text for term in ("clean", "quality", "missing value", "duplicate")):
        return "data-quality note and cleaned sample file"
    return "skill evidence note"


def _is_assumptions_document_gap(skill) -> bool:
    return bool(_ASSUMPTIONS_GAP.search(f"{skill.skill_name} {skill.what_is_missing}"))


def _assign_targets(targets):
    """Spread selected targets across days, reserving days 1 and 5 for assumptions docs."""
    if not targets:
        raise AnalysisValidationError(
            "No validated skills are available for the portfolio plan.",
            field_path=("skill_assessments",),
            category="plan_targets_unavailable",
            expected_type="at least one validated assessment",
        )
    assumptions = next((item for item in targets if _is_assumptions_document_gap(item)), None)
    assignments = []
    other_targets = [item for item in targets if item is not assumptions]
    rotation = 0
    for day_number in range(1, 8):
        if assumptions is not None and day_number in {1, 5}:
            assignments.append(assumptions)
        elif other_targets:
            assignments.append(other_targets[rotation % len(other_targets)])
            rotation += 1
        elif assumptions is not None:
            assignments.append(assumptions)
        else:
            assignments.append(targets[(day_number - 1) % len(targets)])
    return assignments
def artifact_article(artifact: str) -> str:
    if artifact.casefold().startswith(("a ", "an ")):
        return ""
    if artifact.casefold().startswith(("sql ", "python ")):
        return "a"
    return "a"

def _day_text(day_number, target, artifact, needs_dataset, assumptions_gap):
    skill = target.skill_name
    gap = target.what_is_missing
    project = "the portfolio project folder"
    if day_number == 1:
        if target is assumptions_gap:
            return (
                f"Create {project} and an initial assumptions document for {skill}, recording the project question and intended outcome.",
                "Portfolio project folder with a project brief and initial assumptions document.",
                "The assumptions document is saved in the folder and lists one project question and intended outcome.",
            )
        return (
            f"Create {project} and a brief for {skill} that names one manageable question and the assessed evidence need.",
            "Portfolio project folder containing a project brief and evidence checklist.",
            "The brief is saved and lists one question, the selected skill, and one planned artifact.",
        )

    if day_number == 2:
        if needs_dataset:
            return (
                f"Extend {project} with a source note and a small public or self-created synthetic dataset for {skill}.",
                "Portfolio project folder with a source note and a small dataset ready for analysis.",
                "The source note names the dataset source and the saved data file opens.",
            )
        return (
            f"Extend {project} with a three-item evidence checklist for {skill} based on this assessed gap: {gap}",
            "Portfolio project folder with an evidence checklist and artifact outline.",
            "The checklist lists three observable items tied to the assessed skill gap.",
        )

    if day_number == 3:
        if target is assumptions_gap:
            return (
                f"Extend the assumptions document with the project scope, evidence boundary, and first documented decisions for {skill}.",
                "Portfolio project folder with an assumptions document containing a scope and decision section.",
                "The assumptions document contains a scope section and at least two recorded decisions.",
            )
        return (
            f"Extend {project} by creating {artifact_article(artifact)} {artifact} for {skill}, addressing the assessed evidence need.",
            f"Portfolio project folder with {artifact_article(artifact)} {artifact} and one worked example.",
            f"The {artifact} is saved in the folder and contains one worked example.",
        )

    if day_number == 4:
        return (
            f"Extend {project} with checks for the {artifact} and record the results for {skill}.",
            f"Portfolio project folder with a validation checklist for the {artifact} and a results log.",
            f"The checklist records at least three pass-or-fix checks for the {artifact}.",
        )

    if day_number == 5:
        if target is assumptions_gap:
            return (
                "Improve the assumptions document using the saved check results; add decisions and explain one revision.",
                "Portfolio project folder with an improved assumptions document and a revision note.",
                "The assumptions document lists at least three decisions and records one revision.",
            )
        return (
            f"Improve the {artifact} using day four's saved checks and address the {skill} evidence need.",
            f"Portfolio project folder with a revised {artifact} and a change note.",
            f"The revised {artifact} records one change linked to a validation check.",
        )

    if day_number == 6:
        if "communication" in skill.casefold() or "presentation" in skill.casefold():
            return (
                f"Extend {project} with a short findings recording for {skill} and review it with a self-checklist.",
                "Portfolio project folder with a findings recording and a self-review checklist.",
                "The recording is saved and the checklist records three self-checks.",
            )
        return (
            f"Extend {project} with a concise interpretation of the {artifact} results and limitations for {skill}.",
            f"Portfolio project folder with a findings note explaining the {artifact} results and one limitation.",
            "The findings note records two project outcomes and one limitation.",
        )

    return (
        f"Extend the portfolio project folder by packaging the README and {skill} artifact for self-review.",
        "Portfolio project folder containing a README, project artifacts, source note, and limitations.",
        "The README lists the project question, files, source, two outcomes, and one limitation.",
    )


def build_seven_day_plan(skill_assessments) -> list[PlanDay]:
    """Build seven linked, independently checkable days from validated skills only."""
    targets = select_priority_assessments(skill_assessments)
    assumptions_gap = next((item for item in targets if _is_assumptions_document_gap(item)), None)
    assignments = _assign_targets(targets)
    needs_dataset = any(
        _DATA_SKILL.search(f"{item.skill_name} {item.what_is_missing}")
        for item in targets
    )
    days = []
    for day_number, target in enumerate(assignments, start=1):
        artifact = _artifact_name(target.skill_name, target.what_is_missing)
        task, deliverable, criterion = _day_text(
            day_number, target, artifact, needs_dataset, assumptions_gap
        )
        if day_number > 1 and not task.casefold().startswith(("extend", "improve", "package")):
            task = f"Extend the portfolio project folder: {task[0].lower() + task[1:]}"
        day = PlanDay.model_validate({
            "day_number": day_number,
            "task": task,
            "deliverable": deliverable,
            "targeted_gap": f"{target.skill_name} — Evidence gap: {target.what_is_missing}",
            "why_it_matters": f"This creates or strengthens submitted-example evidence for the assessed {target.skill_name} gap.",
            "completion_criterion": criterion,
        })
        days.append(day)

    validate_ordered_days(days)
    validate_plan_alignment(skill_assessments, days)
    return days
