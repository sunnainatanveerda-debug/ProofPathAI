"""Local ProofPath AI prototype for the approved demo workflow."""

import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request
from pydantic import ValidationError

from ai_service import AnalysisServiceError, analyze_submission
from models import AnalysisResult, AnalysisValidationError, EvidenceCategory
from sample_data import (
    SAMPLE_CURRENT_SKILLS,
    SAMPLE_JOB_DESCRIPTION,
    SAMPLE_PROJECTS_AND_WORK,
    SAMPLE_REPORT,
)

load_dotenv(Path(__file__).resolve().with_name(".env"))

logger = logging.getLogger(__name__)
app = Flask(__name__)
MIN_JOB_DESCRIPTION_LENGTH = 100


def submitted_values():
    """Return normalized form text so validation errors can preserve entries."""
    return {
        "job_description": request.form.get("job_description", "").strip(),
        "current_skills": request.form.get("current_skills", "").strip(),
        "projects_and_work": request.form.get("projects_and_work", "").strip(),
    }


def render_error(form_values, message, *, status=503):
    """Render a safe message without raw provider errors or response details."""
    return (
        render_template(
            "index.html",
            form_values=form_values,
            error=message,
            error_heading="Analysis could not be completed",
            show_demo_link=True,
            submit_label="Try Again",
        ),
        status,
    )


@app.get("/")
def home():
    """Show the shared form, optionally prefilled with editable sample data."""
    use_sample = request.args.get("sample") == "1"
    form_values = {
        "job_description": SAMPLE_JOB_DESCRIPTION if use_sample else "",
        "current_skills": SAMPLE_CURRENT_SKILLS if use_sample else "",
        "projects_and_work": SAMPLE_PROJECTS_AND_WORK if use_sample else "",
    }
    return render_template("index.html", form_values=form_values)


@app.post("/analyze")
def analyze_form():
    """Validate once, then render results only from the fully validated response."""
    form_values = submitted_values()
    job_description = form_values["job_description"]

    if len(job_description) < MIN_JOB_DESCRIPTION_LENGTH:
        return render_template(
            "index.html",
            form_values=form_values,
            error=(
                "Please paste the internship description. Add enough detail to "
                "identify the role and its responsibilities (at least "
                f"{MIN_JOB_DESCRIPTION_LENGTH} characters)."
            ),
            submit_label="Analyze an Internship",
        ), 400

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return render_error(
            form_values,
            "The Groq API key is not configured. Add GROQ_API_KEY to your local "
            ".env file, restart the app, then try again.",
        )

    try:
        result = analyze_submission(
            api_key=api_key,
            job_description=job_description,
            current_skills=form_values["current_skills"],
            projects_and_work=form_values["projects_and_work"],
        )
        if not isinstance(result, AnalysisResult):
            raise AnalysisValidationError("The response failed validation.")
        # Re-validate the exact data that will be rendered. This prevents a
        # bypassed/constructed model instance from reaching the personalized UI.
        result = AnalysisResult.model_validate(result.model_dump())
        result = result.validate_against_submission(
            job_description=job_description,
            current_skills=form_values["current_skills"],
            projects_and_work=form_values["projects_and_work"],
        )
    except AnalysisServiceError as exc:
        return render_error(form_values, exc.user_message)
    except (AnalysisValidationError, ValidationError):
        return render_error(
            form_values,
            "Groq returned a response that could not be validated. It was not "
            "treated as a personalized analysis. You can try again or view the "
            "separate demo example.",
        )
    except Exception as exc:
        # Do not log or render exception details, which can contain request metadata.
        # The exception class helps diagnose unexpected failures without exposing
        # submitted text, provider response bodies, headers, or credentials.
        logger.error("Unexpected analysis failure: exception_type=%s", type(exc).__name__)
        return render_error(
            form_values,
            "The analysis could not be completed right now. No automatic retry "
            "was made. You can try again or view the separate demo example.",
        )

    evidence_counts = {
        category: sum(skill.evidence_category == category for skill in result.skill_assessments)
        for category in EvidenceCategory.__args__
    }
    priority_gaps = [
        skill for skill in result.skill_assessments
        if skill.evidence_category in {"Evidence not provided", "Partial evidence"}
    ][:3]
    supported_strengths = [
        skill for skill in result.skill_assessments
        if skill.evidence_category == "Evidence provided" and skill.supporting_example_quote
    ]
    return render_template(
        "results.html",
        analysis=result,
        evidence_counts=evidence_counts,
        priority_gaps=priority_gaps,
        supported_strengths=supported_strengths,
        form_values=form_values,
    )


@app.get("/sample-report")
def sample_report():
    """Show a separate, fixed sample that is never based on submitted values."""
    return render_template("sample_report.html", report=SAMPLE_REPORT)


if __name__ == "__main__":
    # Debug mode stays off so Flask never exposes its interactive traceback page.
    app.run(debug=False)
