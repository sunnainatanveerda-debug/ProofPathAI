"""Groq assessment and deterministic plan generation with safe failures."""

import json
import logging
import re
from collections import Counter

from groq import APIConnectionError, APIStatusError, APITimeoutError, Groq, RateLimitError
from pydantic import ValidationError

from models import (
    AnalysisResult,
    AnalysisValidationError,
    GroqAssessmentResponse,
)
from plan_builder import build_seven_day_plan

logger = logging.getLogger(__name__)
MODEL_NAME = "openai/gpt-oss-20b"
REQUEST_TIMEOUT_SECONDS = 60.0
# The approved model supports up to 65,536 output tokens. Keep this cap below
# the published Free-plan 8K TPM limit while leaving headroom above the old
# 4,096 cap for the seven-day structured result.
MAX_COMPLETION_TOKENS = 6144
REASONING_EFFORT = "low"


def groq_response_schema() -> dict:
    """Build the strict provider schema for the AI assessment only."""
    return {
        "type": "object",
        "properties": {
            "role_title": {"type": "string"},
            "overview": {"type": "string"},
            "skill_assessments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "skill_name": {"type": "string"},
                        "requirement_type": {
                            "type": "string",
                            "enum": ["explicit", "preferred", "inferred"],
                        },
                        "job_description_basis_id": {"type": "string"},
                        "uncertainty_note": {"type": "string"},
                        "evidence_category": {
                            "type": "string",
                            "enum": [
                                "Evidence provided",
                                "Partial evidence",
                                "Evidence not provided",
                            ],
                        },
                        "supporting_example_quote": {"type": "string"},
                        "what_is_missing": {"type": "string"},
                        "suggested_next_step": {"type": "string"},
                    },
                    "required": [
                        "skill_name",
                        "requirement_type",
                        "job_description_basis_id",
                        "uncertainty_note",
                        "evidence_category",
                        "supporting_example_quote",
                        "what_is_missing",
                        "suggested_next_step",
                    ],
                    "additionalProperties": False,
                },
            },
            "assumptions_and_limitations": {"type": "string"},
        },
        "required": [
            "role_title", "overview", "skill_assessments", "assumptions_and_limitations",
        ],
        "additionalProperties": False,
    }


def groq_response_format() -> dict:
    """Return Groq strict Structured Outputs configuration for assessment."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "proofpath_assessment",
            "strict": True,
            "schema": groq_response_schema(),
        },
    }


def groq_assessment_response_schema() -> dict:
    """Compatibility alias for the assessment-only provider schema."""
    return groq_response_schema()


def groq_assessment_response_format() -> dict:
    """Compatibility alias for the assessment-only response format."""
    return groq_response_format()

def extract_job_description_excerpts(job_description: str) -> dict[str, str]:
    """Split source text at sentence/newline boundaries without editing excerpt text.

    IDs are stable for a given input ordering. Only outer whitespace is excluded;
    the returned excerpt itself is copied directly from the submitted string.
    """
    separators = re.compile(r"(?<=[.!?])[ \t]+|\r\n?|\n+")
    excerpts: dict[str, str] = {}
    start = 0
    for match in separators.finditer(job_description):
        raw = job_description[start:match.start()]
        excerpt = raw.strip()
        if excerpt:
            excerpts[f"jd_{len(excerpts) + 1:03d}"] = excerpt
        start = match.end()
    tail = job_description[start:].strip()
    if tail:
        excerpts[f"jd_{len(excerpts) + 1:03d}"] = tail
    return excerpts


_EXPECTED_TYPES_BY_ERROR = {
    "missing": "required field",
    "extra_forbidden": "no additional field",
    "literal_error": "one of the allowed enum values",
    "string_type": "string",
    "bool_type": "boolean",
    "int_type": "integer",
    "greater_than_equal": "integer within allowed range",
    "less_than_equal": "integer within allowed range",
    "list_type": "array",
    "too_short": "array with required minimum length",
    "too_long": "array with allowed maximum length",
    "value_error": "valid field relationship",
}

# These are fixed, application-authored Pydantic validator messages. Use them
# only as lookup keys: never include the underlying message in the log because
# provider/model validation errors can otherwise contain generated text.
_SAFE_MODEL_RELATIONSHIP_ERRORS = {
    "Each identified skill must appear only once.": (
        "skill_assessments[].skill_name", "duplicate_skill_name", "unique assessed skill names",
    ),
    "Plan days must be ordered from day 1 through day 7.": (
        "plan_days[].day_number", "day_order_mismatch", "seven days ordered from 1 through 7",
    ),
    "Every plan target must reference an assessed skill.": (
        "plan_days[].targeted_skill_name", "plan_target_mismatch", "target matching an assessed skill",
    ),
    "The plan must focus on no more than three evidence gaps.": (
        "plan_days[].targeted_skill_name", "plan_focus_mismatch", "no more than three targeted skills",
    ),
    "Every plan gap must use the matching assessment wording.": (
        "plan_days[].targeted_gap", "gap_wording_mismatch", "exact wording from its skill assessment",
    ),
    "Each plan day must target an assessed evidence gap.": (
        "plan_days[].targeted_skill_name", "plan_target_mismatch", "target matching an assessed evidence gap",
    ),
    "Each plan task must lead to its stated deliverable.": (
        "plan_days[].task->deliverable", "task_deliverable_mismatch", "task producing its stated deliverable",
    ),
    "Each completion criterion must check its stated deliverable.": (
        "plan_days[].deliverable->completion_criterion", "completion_check_mismatch", "criterion checking its deliverable",
    ),
    "Each plan day must connect its work to its targeted evidence gap.": (
        "plan_days[].task/deliverable/why_it_matters->targeted_skill", "gap_alignment_mismatch", "work addressing its targeted evidence gap",
    ),
    "Each day after day one must build on the previous project deliverable.": (
        "plan_days[].deliverable->next_day.task", "project_sequence_mismatch", "each day building on the previous deliverable",
    ),
    "Repeated evidence gaps must build on an earlier day's deliverable.": (
        "plan_days[].targeted_skill_name/task/deliverable", "repeated_gap_progression_mismatch", "repeated gap extending an earlier deliverable",
    ),
    "An assumptions-document gap needs a create-and-improve deliverable sequence.": (
        "plan_days[].task/deliverable/completion_criterion", "assumptions_sequence_mismatch", "assumptions document created then improved",
    ),
    "Plan days must be independently achievable.": (
        "plan_days[].task/deliverable/completion_criterion", "external_dependency", "independently achievable plan day",
    ),
    "Plan completion criteria must be objectively checkable.": (
        "plan_days[].completion_criterion", "criterion_not_checkable", "objective completion criterion",
    ),
    "Evidence categories require a described example.": (
        "skill_assessments[].evidence_category/supporting_example_quote", "evidence_relationship_mismatch", "provided evidence category with a supporting example",
    ),
    "Evidence not provided cannot include a supporting example.": (
        "skill_assessments[].evidence_category/supporting_example_quote", "evidence_relationship_mismatch", "no supporting example when evidence is not provided",
    ),
    "Inferred requirements need an interpretation note.": (
        "skill_assessments[].requirement_type/uncertainty_note", "inference_note_missing", "uncertainty note for inferred requirement",
    ),
    "Recommended next steps must be independently achievable.": (
        "skill_assessments[].suggested_next_step", "external_dependency", "independently achievable next step",
    ),
}


def _safe_validation_diagnostics(exc) -> list[str]:
    """Format only schema paths and static validation metadata for local logs."""
    if isinstance(exc, AnalysisValidationError):
        path_parts = []
        for part in exc.field_path:
            if isinstance(part, int) and part >= 0:
                path_parts.append(f"[{part}]")
            elif isinstance(part, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", part):
                path_parts.append(("." if path_parts else "") + part)
            else:
                path_parts.append("[redacted]")
        return [
            "field_path=" + ("".join(path_parts) or "$"),
            "error_type=" + (exc.category if re.fullmatch(r"[a-z_]{1,40}", exc.category) else "validation_error"),
            "expected_type=" + re.sub(r"[^a-zA-Z0-9 _/-]", "", exc.expected_type)[:80],
        ]

    if isinstance(exc, ValidationError):
        diagnostics = []
        for error in exc.errors(include_input=False)[:5]:
            context = error.get("ctx") or {}
            internal_error = context.get("error") if isinstance(context, dict) else None
            relationship = _SAFE_MODEL_RELATIONSHIP_ERRORS.get(str(internal_error))
            if relationship is not None:
                field_path, error_type, expected_type = relationship
                diagnostics.append(
                    f"field_path={field_path} error_type={error_type} expected_type={expected_type}"
                )
                continue
            parts = []
            for part in error.get("loc", ()):
                if isinstance(part, int) and part >= 0:
                    parts.append(f"[{part}]")
                elif isinstance(part, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", part):
                    parts.append(("." if parts else "") + part)
                else:
                    parts.append("[redacted]")
            error_type = error.get("type", "validation_error")
            if not isinstance(error_type, str) or not re.fullmatch(r"[a-z_]{1,60}", error_type):
                error_type = "validation_error"
            diagnostics.append(
                "field_path=" + ("".join(parts) or "$")
                + " error_type=" + error_type
                + " expected_type=" + _EXPECTED_TYPES_BY_ERROR.get(error_type, "valid field value")
            )
        return diagnostics or ["field_path=$", "error_type=validation_error", "expected_type=valid analysis"]

    return ["field_path=$", "error_type=validation_error", "expected_type=valid analysis"]


def _safe_error_fields(exc, sensitive_values):
    """Return conservative provider code/message values safe for local logs."""
    body = getattr(exc, "body", None)
    error = body.get("error", body) if isinstance(body, dict) else {}
    if not isinstance(error, dict):
        return "unavailable", "unavailable", "failed_generation_unavailable"

    def safe_code(value):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", value):
            return "unavailable"
        if any(isinstance(secret, str) and secret and secret.casefold() == value.casefold() for secret in sensitive_values):
            return "redacted"
        return value

    code = safe_code(error.get("code") or error.get("type"))
    message = error.get("message")
    # Validation errors can echo fragments from generated output. Keep this
    # provider message out of logs; the structured, type-only diagnostic below
    # is sufficient to investigate schema mismatches without exposing content.
    if code == "json_validate_failed":
        safe_message = "structured_output_validation_failed"
    elif not isinstance(message, str) or not message.strip():
        safe_message = "unavailable"
    else:
        safe_message = message
        # Redact complete submitted fields and their word tokens before logging,
        # while retaining non-overlapping provider diagnostics such as schema paths.
        for value in sorted(
            (item for item in sensitive_values if isinstance(item, str) and item),
            key=len,
            reverse=True,
        ):
            safe_message = re.sub(re.escape(value), "[redacted]", safe_message, flags=re.IGNORECASE)
        submitted_tokens = {
            token
            for value in sensitive_values
            if isinstance(value, str)
            for token in re.findall(r"\w+", value)
            if len(token) >= 2
        }
        for token in sorted(submitted_tokens, key=len, reverse=True):
            safe_message = re.sub(
                rf"(?<!\w){re.escape(token)}(?!\w)",
                "[redacted]",
                safe_message,
                flags=re.IGNORECASE,
            )
        safe_message = re.sub(r"(?i)bearer\s+\S+", "Bearer [redacted]", safe_message)
        safe_message = re.sub(r"(?i)(authorization\s*[:=]\s*)[^,;\s]+", r"\1[redacted]", safe_message)
        safe_message = " ".join(safe_message.split())[:240] or "unavailable"

    failed_generation = error.get("failed_generation")
    if failed_generation is None:
        failed_summary = "failed_generation_unavailable"
    else:
        try:
            candidate = json.loads(failed_generation) if isinstance(failed_generation, str) else failed_generation
            GroqAssessmentResponse.model_validate(candidate)
            failed_summary = "candidate_passed_local_pydantic"
        except json.JSONDecodeError as parse_error:
            # json.JSONDecodeError.msg is a parser-generated description, not
            # candidate text. Keep it allowlisted and log only location/size
            # metadata so a later request can distinguish a bad prefix from a
            # likely truncated response without exposing generated/user text.
            allowed_parse_messages = {
                "Expecting value",
                "Expecting property name enclosed in double quotes",
                "Expecting ',' delimiter",
                "Extra data",
                "Invalid control character at",
                "Invalid \\escape",
                "Invalid \\uXXXX escape",
                "Unterminated string starting at",
            }
            parse_message = (
                parse_error.msg
                if parse_error.msg in allowed_parse_messages
                else "other_json_parse_error"
            )
            candidate_length = len(failed_generation) if isinstance(failed_generation, str) else 0
            parse_near_end = candidate_length > 0 and (
                parse_error.pos >= candidate_length - 1
                or parse_error.msg == "Unterminated string starting at"
            )
            failed_summary = (
                "candidate_not_valid_json"
                f":parse_error={parse_message}"
                f",line={parse_error.lineno},column={parse_error.colno}"
                f",chars={candidate_length},near_end={str(parse_near_end).lower()}"
            )
        except ValidationError as validation_error:
            counts = Counter(item["type"] for item in validation_error.errors(include_input=False))
            allowed_types = {
                "missing", "extra_forbidden", "literal_error", "string_type", "bool_type",
                "int_type", "greater_than_equal", "less_than_equal", "value_error", "list_type",
            }
            safe_counts = [
                f"{error_type}={counts[error_type]}"
                for error_type in sorted(counts)
                if error_type in allowed_types and counts[error_type]
            ]
            failed_summary = "candidate_schema_mismatch:" + (",".join(safe_counts) or "other_validation_error")
            day_number_error = next(
                (
                    item for item in validation_error.errors(include_input=False)
                    if tuple(item.get("loc", ())) == ("plan_days", 5, "day_number")
                    and item.get("type") in {"int_type", "greater_than_equal", "less_than_equal"}
                ),
                None,
            )
            if day_number_error is not None:
                plan_days = candidate.get("plan_days") if isinstance(candidate, dict) else None
                day = plan_days[5] if isinstance(plan_days, list) and len(plan_days) > 5 else None
                number = day.get("day_number") if isinstance(day, dict) else None
                if number is None:
                    value_type = "null" if isinstance(day, dict) and "day_number" in day else "unavailable"
                elif isinstance(number, bool):
                    value_type = "boolean"
                elif isinstance(number, int):
                    value_type = "integer"
                elif isinstance(number, float):
                    value_type = "number"
                elif isinstance(number, str):
                    value_type = "string"
                elif isinstance(number, list):
                    value_type = "array"
                elif isinstance(number, dict):
                    value_type = "object"
                else:
                    value_type = "unavailable"
                failed_summary += (
                    ";field_path=plan_days[5].day_number"
                    f",rejected_value_type={value_type},expected_type=integer"
                )
        except (TypeError, ValueError):
            failed_summary = "candidate_unavailable_or_unparseable"
        except Exception:
            failed_summary = "candidate_unavailable_or_unparseable"

    return code, safe_message, failed_summary


class AnalysisServiceError(Exception):
    """An expected service failure with a sanitized message for the form."""

    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


SYSTEM_PROMPT = """You are ProofPath AI, a careful career-readiness assistant for entry-level data analyst internships. Assess only the job description, self-reported skills, and project/work examples submitted by the user. Assess the information provided; do not claim that a person's actual ability is verified.

Identify every distinct skill or requirement explicitly stated, preferred, or reasonably inferred from the job description. Use requirement_type values explicit, preferred, or inferred. Follow source wording: “helpful,” “preferred,” “nice to have,” “desirable,” or “a bonus” means preferred. Use inferred only when a source clue supports the interpretation; briefly explain uncertainty. For each skill, select one exact source excerpt ID from job_description_excerpts. Do not create or paraphrase source text. Do not include unsupported inferences.

Use only these evidence_category values: Evidence provided, Partial evidence, Evidence not provided. Evidence provided or Partial evidence requires a relevant project/work example. A self-reported skill name alone is not evidence. Copy supporting_example_quote as an exact contiguous excerpt from projects_and_work, preserving case and punctuation; whitespace may be normalized. If there is no relevant excerpt, return an empty quote and Evidence not provided. Never add skill_claimed_by_user; the application derives it from current_skills.

For each skill, provide a specific what_is_missing description of at least 20 characters and four meaningful words, plus an independently achievable suggested_next_step. Each suggested_next_step must describe an action the applicant can complete alone, using available tools and their own work. Prefer concrete actions such as creating a SQL query, documenting a cleaning decision, building a chart, or writing a findings summary. Do not recommend presenting to another person, requesting or collecting feedback, waiting for approval, or depending on a mentor, peer, manager, or other external person. When a communication skill is missing, the applicant can record a short presentation and evaluate it with a self-checklist. Keep the overview at or below 45 words and assessment prose concise. Return one JSON object only with role_title, overview, skill_assessments, and assumptions_and_limitations. Each skill assessment must contain skill_name, requirement_type, job_description_basis_id, uncertainty_note, evidence_category, supporting_example_quote, what_is_missing, and suggested_next_step. Do not return plan days or extra fields."""
ASSESSMENT_PROMPT = SYSTEM_PROMPT

def _request_structured_json(client, *, prompt, payload, response_format, sensitive_values):
    """Make one request without retries, returning only validated JSON data."""
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{
                "role": "user",
                "content": (
                    f"{prompt}\n\nSubmitted information (JSON):\n"
                    + json.dumps(payload, ensure_ascii=False)
                ),
            }],
            response_format=response_format,
            include_reasoning=False,
            reasoning_effort=REASONING_EFFORT,
            max_completion_tokens=MAX_COMPLETION_TOKENS,
        )
    except RateLimitError as exc:
        logger.warning("Groq request failed: exception_type=%s status=429", type(exc).__name__)
        raise AnalysisServiceError(
            "Groq's current Free-plan rate limit was reached. Wait for the limit "
            "to reset, then choose Try Again, or view the separate demo example."
        ) from exc
    except APITimeoutError as exc:
        logger.warning("Groq request failed: exception_type=%s category=timeout", type(exc).__name__)
        raise AnalysisServiceError(
            "Groq did not respond before the request timed out. No automatic "
            "retry was made. Choose Try Again or view the separate demo example."
        ) from exc
    except APIConnectionError as exc:
        cause = exc.__cause__
        nested_cause = getattr(cause, "__cause__", None) if cause is not None else None
        cause_type = type(cause).__name__ if cause is not None else "none"
        nested_cause_type = type(nested_cause).__name__ if nested_cause is not None else "none"
        logger.warning(
            "Groq request failed: exception_type=%s category=connection cause_type=%s nested_cause_type=%s",
            type(exc).__name__, cause_type, nested_cause_type,
        )
        raise AnalysisServiceError(
            "ProofPath AI could not connect to Groq. Check your connection and "
            "try again, or view the separate demo example."
        ) from exc
    except APIStatusError as exc:
        request_id = getattr(exc, "request_id", None)
        if not request_id:
            response_headers = getattr(getattr(exc, "response", None), "headers", {})
            request_id = response_headers.get("x-request-id") if hasattr(response_headers, "get") else None
        safe_request_id = (
            request_id
            if isinstance(request_id, str)
            and len(request_id) <= 100
            and request_id.replace("-", "").replace("_", "").isalnum()
            else "unavailable"
        )
        logger.warning(
            "Groq request failed: exception_type=%s status=%s request_id=%s error_code=%s error_message=%s validation_detail=%s",
            type(exc).__name__, exc.status_code, safe_request_id,
            *_safe_error_fields(exc, sensitive_values),
        )
        if exc.status_code in {401, 403}:
            message = (
                "Groq could not authenticate this request. Check that the local "
                ".env file contains a valid GROQ_API_KEY, then try again or "
                "view the separate demo example."
            )
        elif exc.status_code == 429:
            message = (
                "Groq's current Free-plan rate limit was reached. Wait for the "
                "limit to reset, then choose Try Again, or view the separate demo example."
            )
        elif exc.status_code >= 500:
            message = (
                "Groq is temporarily unavailable. No paid service or alternate "
                "model was used. Try again later or view the separate demo example."
            )
        else:
            message = (
                "Groq could not complete this request. No automatic retry was "
                "made. Try again or view the separate demo example."
            )
        raise AnalysisServiceError(message) from exc
    except Exception as exc:
        logger.error("Groq request failed: exception_type=%s", type(exc).__name__)
        raise AnalysisServiceError(
            "The Groq request could not be completed. No automatic retry was "
            "made. Try again or view the separate demo example."
        ) from exc

    if not response.choices:
        raise AnalysisValidationError("The response did not include a result.")
    choice = response.choices[0]
    if getattr(choice, "finish_reason", None) == "content_filter":
        raise AnalysisValidationError("The response was refused or filtered.")
    content = choice.message.content
    if not isinstance(content, str) or not content.strip():
        raise AnalysisValidationError("The response did not contain JSON content.")
    return content


def _validate_stage_response(content, model_type):
    try:
        return model_type.model_validate_json(content)
    except (AnalysisValidationError, ValidationError) as exc:
        logger.warning("Groq response rejected: %s", " ".join(_safe_validation_diagnostics(exc)))
        raise
    except Exception as exc:
        logger.warning("Groq response rejected: exception_type=%s", type(exc).__name__)
        raise AnalysisValidationError("The response failed validation.") from exc


def analyze_submission(
    *,
    api_key: str,
    job_description: str,
    current_skills: str,
    projects_and_work: str,
) -> AnalysisResult:
    """Request one validated assessment and generate its plan locally."""
    client = Groq(
        api_key=api_key,
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=0,
    )
    excerpts = extract_job_description_excerpts(job_description)
    submitted_payload = {
        "job_description": job_description,
        "job_description_excerpts": [
            {"id": excerpt_id, "text": excerpt}
            for excerpt_id, excerpt in excerpts.items()
        ],
        "current_skills": current_skills,
        "projects_and_work": projects_and_work,
    }
    private_inputs = (api_key, job_description, current_skills, projects_and_work)
    assessment_content = _request_structured_json(
        client,
        prompt=ASSESSMENT_PROMPT,
        payload=submitted_payload,
        response_format=groq_assessment_response_format(),
        sensitive_values=private_inputs,
    )
    assessment = _validate_stage_response(assessment_content, GroqAssessmentResponse)
    skill_assessments = assessment.resolve_skill_assessments(current_skills, excerpts)
    try:
        AnalysisResult.validate_skill_assessments_against_submission(
            skill_assessments,
            job_description=job_description,
            current_skills=current_skills,
            projects_and_work=projects_and_work,
        )
    except AnalysisValidationError as exc:
        logger.warning(
            "Groq response rejected: %s",
            " ".join(_safe_validation_diagnostics(exc)),
        )
        raise

    plan_days = build_seven_day_plan(skill_assessments)
    result = AnalysisResult.model_validate({
        "role_title": assessment.role_title,
        "overview": assessment.overview,
        "skill_assessments": [item.model_dump() for item in skill_assessments],
        "plan_days": [day.model_dump() for day in plan_days],
        "assumptions_and_limitations": assessment.assumptions_and_limitations,
    })
    return result.validate_against_submission(
        job_description=job_description,
        current_skills=current_skills,
        projects_and_work=projects_and_work,
    )
