import logging
import json
import unittest
from unittest.mock import patch

import httpx
from groq import APIConnectionError, BadRequestError
from pydantic import ValidationError

import ai_service
from models import (
    AnalysisResult,
    AnalysisValidationError,
    GroqAnalysisResponse,
    GroqAssessmentResponse,
    GroqPlanDay,
    GroqSkillAssessment,
    PlanDay,
    completion_criterion_is_checkable,
    skill_name_was_reported,
)
from sample_data import SAMPLE_CURRENT_SKILLS, SAMPLE_JOB_DESCRIPTION, SAMPLE_PROJECTS_AND_WORK


def walk_schema(schema):
    yield schema
    if isinstance(schema, dict):
        for value in schema.values():
            yield from walk_schema(value)
    elif isinstance(schema, list):
        for value in schema:
            yield from walk_schema(value)


def synthetic_provider_plan(skill_name):
    """Create a chained, self-checking project plan for provider-model tests."""
    topic = f"{skill_name} project artifact"
    days = []
    for number in range(1, 8):
        task = (
            f"Create the {topic} for day {number}." if number == 1
            else f"Extend the prior {topic} with day {number} results."
        )
        deliverable = (
            f"Saved {topic} containing day {number} results."
        )
        days.append({
            "day_number": number,
            "task": task,
            "deliverable": deliverable,
            "targeted_skill_name": skill_name,
            "why_it_matters": f"This adds {skill_name} evidence to the project.",
            "completion_criterion": f"The saved {topic} contains day {number} results and opens.",
        })
    return days


class GroqSchemaTests(unittest.TestCase):
    GROQ_SCHEMA_KEYS = {
        "type", "properties", "required",
        "additionalProperties", "enum", "items", "minimum", "maximum",
    }

    def test_prompt_requests_assessment_only_and_preserves_evidence_rules(self):
        prompt = ai_service.ASSESSMENT_PROMPT
        for field_name in (
            "role_title", "overview", "skill_assessments", "assumptions_and_limitations",
            "skill_name", "requirement_type", "job_description_basis_id", "uncertainty_note",
            "evidence_category", "supporting_example_quote", "what_is_missing", "suggested_next_step",
        ):
            self.assertIn(field_name, prompt)
        for enum_value in (
            "explicit", "preferred", "inferred", "Evidence provided",
            "Partial evidence", "Evidence not provided",
        ):
            self.assertIn(enum_value, prompt)
        self.assertIn("helpful", prompt)
        self.assertIn("means preferred", prompt)
        self.assertIn("exact contiguous excerpt", prompt)
        self.assertIn("self-reported skill name alone is not evidence", prompt)
        self.assertIn("Never add skill_claimed_by_user", prompt)
        self.assertIn("Do not return plan days", prompt)
        self.assertNotIn("plan_days", ai_service.groq_response_schema()["properties"])
        self.assertNotIn("Create exactly seven", prompt)

    def test_schema_has_required_closed_objects_and_documented_keywords(self):
        schema = ai_service.groq_response_schema()
        self.assertEqual(set(schema["properties"]), set(GroqAssessmentResponse.model_fields))
        self.assertNotIn("plan_days", schema["properties"])
        skill_properties = schema["properties"]["skill_assessments"]["items"]["properties"]
        self.assertNotIn("skill_claimed_by_user", skill_properties)
        self.assertEqual(set(skill_properties), set(GroqSkillAssessment.model_fields))
        for node in walk_schema(schema):
            if not isinstance(node, dict) or not any(
                keyword in node for keyword in ("type", "$ref", "enum", "anyOf")
            ):
                continue
            self.assertFalse(set(node) - self.GROQ_SCHEMA_KEYS)
            if node.get("type") == "object":
                self.assertEqual(node.get("additionalProperties"), False)
                self.assertEqual(set(node.get("properties", {})), set(node.get("required", [])))
        self.assertNotIn("$defs", schema)
        self.assertNotIn("$ref", json.dumps(schema))
    def test_strict_response_format_uses_supported_schema_configuration(self):
        response_format = ai_service.groq_response_format()
        self.assertEqual(response_format["type"], "json_schema")
        self.assertEqual(response_format["json_schema"]["name"], "proofpath_assessment")
        self.assertIs(response_format["json_schema"]["strict"], True)
        self.assertEqual(response_format["json_schema"]["schema"], ai_service.groq_response_schema())

        schema = response_format["json_schema"]["schema"]
        self.assertNotIn("$defs", schema)
        self.assertNotIn("$ref", json.dumps(schema))

    def test_local_pydantic_schema_keeps_response_constraints(self):
        raw_schema = AnalysisResult.model_json_schema()
        self.assertEqual(raw_schema["properties"]["plan_days"]["minItems"], 7)
        self.assertEqual(raw_schema["properties"]["plan_days"]["maxItems"], 7)

    def test_provider_candidate_is_converted_to_locally_validated_result(self):
        # Provider schema constraints do not replace local Pydantic/business-rule checks.
        candidate = {
            "role_title": "Data Analyst Intern",
            "overview": "SQL is stated; the submitted information contains no supporting project example.",
            "skill_assessments": [{
                "skill_name": "SQL",
                "requirement_type": "explicit",
                "job_description_basis_id": "jd_001",
                "uncertainty_note": "",
                "evidence_category": "Evidence not provided",
                "supporting_example_quote": "",
                "what_is_missing": "A SQL query example demonstrating joins, grouped totals, and findings.",
                "suggested_next_step": "Create a query-based analysis.",
            }],
            "plan_days": synthetic_provider_plan("SQL"),
            "assumptions_and_limitations": "Assessment is based only on submitted information.",
        }

        provider_result = GroqAnalysisResponse.model_validate_json(json.dumps(candidate))
        result = provider_result.with_user_skill_claims("SQL", {"jd_001": "SQL"})
        self.assertEqual([day.day_number for day in result.plan_days], list(range(1, 8)))
        self.assertEqual(
            result.skill_assessments[0].display_evidence_label,
            "Skill claimed — evidence not provided",
        )
        self.assertEqual(
            result.plan_days[0].targeted_gap,
            "SQL — Evidence gap: A SQL query example demonstrating joins, grouped totals, and findings.",
        )
        mismatched_gap = result.model_dump()
        mismatched_gap["plan_days"][0]["targeted_gap"] = "SQL evidence"
        with self.assertRaises(ValidationError):
            AnalysisResult.model_validate(mismatched_gap)

        candidate["skill_assessments"][0]["evidence_category"] = "Verified skill"
        with self.assertRaises(ValidationError):
            GroqAnalysisResponse.model_validate_json(json.dumps(candidate))

        candidate["skill_assessments"][0]["evidence_category"] = "Evidence provided"
        with self.assertRaises(ValidationError):
            GroqAnalysisResponse.model_validate_json(json.dumps(candidate))

        candidate["skill_assessments"][0]["evidence_category"] = "Evidence not provided"
        candidate["plan_days"] = candidate["plan_days"][:-1]
        with self.assertRaises(ValidationError):
            GroqAnalysisResponse.model_validate_json(json.dumps(candidate))

    def test_malformed_json_is_rejected_locally(self):
        with self.assertRaises(ValidationError):
            GroqAnalysisResponse.model_validate_json('{"role_title":')


class SafeDiagnosticTests(unittest.TestCase):
    def _run_bad_request(self, body, *, api_key, submitted):
        response = httpx.Response(
            400,
            request=httpx.Request("POST", "https://example.invalid"),
            headers={"x-request-id": "req_test123"},
        )
        error = BadRequestError(
            "sensitive SDK exception message must not be logged",
            response=response,
            body=body,
        )

        request_arguments = []
        client_options = {}

        class FakeCompletions:
            def create(self, **kwargs):
                request_arguments.append(kwargs)
                raise error

        class FakeGroq:
            def __init__(self, **kwargs):
                client_options.update(kwargs)
                self.chat = type("Chat", (), {"completions": FakeCompletions()})()

        captured = []

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                captured.append(record.getMessage())

        handler = CaptureHandler()
        service_logger = logging.getLogger("ai_service")
        service_logger.addHandler(handler)
        try:
            with patch.object(ai_service, "Groq", FakeGroq):
                with self.assertRaises(ai_service.AnalysisServiceError):
                    ai_service.analyze_submission(
                        api_key=api_key,
                        job_description=submitted,
                        current_skills="SQL and Excel",
                        projects_and_work="A dashboard project",
                    )
        finally:
            service_logger.removeHandler(handler)
        return "\n".join(captured), request_arguments[0], client_options, len(request_arguments)

    def test_logs_safe_code_message_and_request_id_without_private_data(self):
        log_output, request, client_options, request_count = self._run_bad_request(
            {"error": {
                "type": "invalid_request_error",
                "code": "json_validate_failed",
                "message": "Invalid JSON Schema: unsupported keyword minLength; field SQL",
            }},
            api_key="sk-test-secret-value",
            submitted="Please analyze private employer text and SQL requirements here.",
        )
        self.assertIn("BadRequestError", log_output)
        self.assertIn("status=400", log_output)
        self.assertIn("req_test123", log_output)
        self.assertIn("error_code=json_validate_failed", log_output)
        self.assertIn("error_message=structured_output_validation_failed", log_output)
        self.assertNotIn("unsupported keyword minLength", log_output)
        self.assertNotIn("sk-test-secret-value", log_output)
        self.assertNotIn("private employer text", log_output)
        self.assertNotIn("sensitive SDK exception message", log_output)
        self.assertEqual(request["model"], ai_service.MODEL_NAME)
        self.assertEqual(request["response_format"], ai_service.groq_assessment_response_format())
        self.assertIs(request["include_reasoning"], False)
        self.assertEqual(request["reasoning_effort"], "low")
        self.assertEqual(request["max_completion_tokens"], ai_service.MAX_COMPLETION_TOKENS)
        self.assertEqual(ai_service.MAX_COMPLETION_TOKENS, 6144)
        self.assertEqual(client_options["max_retries"], 0)
        self.assertEqual(request_count, 1)
        self.assertNotIn("reasoning_format", request)
        self.assertEqual([message["role"] for message in request["messages"]], ["user"])
        self.assertIn("Return one JSON object only", request["messages"][0]["content"])
        self.assertIn('"job_description"', request["messages"][0]["content"])

    def test_assessment_schema_contains_no_plan_output(self):
        schema = ai_service.groq_assessment_response_schema()
        self.assertIn("skill_assessments", schema["required"])
        self.assertNotIn("plan_days", schema["properties"])
        self.assertFalse(schema["additionalProperties"])

    def test_one_groq_assessment_request_builds_plan_locally(self):
        candidate = {
            "role_title": "Data Analyst Intern",
            "overview": "The role asks for SQL analysis.",
            "skill_assessments": [{
                "skill_name": "SQL",
                "requirement_type": "explicit",
                "job_description_basis_id": "jd_001",
                "uncertainty_note": "",
                "evidence_category": "Evidence not provided",
                "supporting_example_quote": "",
                "what_is_missing": "A SQL query example with joins and grouped totals.",
                "suggested_next_step": "Create a documented query analysis.",
            }],
            "assumptions_and_limitations": "This assessment uses submitted information only.",
        }
        requests = []

        class FakeCompletions:
            def create(self, **kwargs):
                requests.append(kwargs)
                return type("Response", (), {"choices": [type("Choice", (), {
                    "finish_reason": "stop",
                    "message": type("Message", (), {"content": json.dumps(candidate)})(),
                })()]})()

        class FakeGroq:
            def __init__(self, **kwargs):
                self.options = kwargs
                self.chat = type("Chat", (), {"completions": FakeCompletions()})()

        with patch.object(ai_service, "Groq", FakeGroq):
            result = ai_service.analyze_submission(
                api_key="synthetic-key",
                job_description="SQL is required. Analyze a small dataset.",
                current_skills="",
                projects_and_work="",
            )
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["model"], ai_service.MODEL_NAME)
        self.assertEqual(requests[0]["response_format"], ai_service.groq_assessment_response_format())
        self.assertNotIn("plan_days", requests[0]["response_format"]["json_schema"]["schema"]["properties"])
        self.assertEqual([day.day_number for day in result.plan_days], list(range(1, 8)))
        self.assertEqual(
            {day.targeted_gap for day in result.plan_days},
            {"SQL — Evidence gap: A SQL query example with joins and grouped totals."},
        )
    def test_redacts_exact_submitted_values_and_credentials_from_message(self):
        log_output, _, _, _ = self._run_bad_request(
            {"error": {
                "code": "invalid_request_error",
                "message": (
                    "Invalid request for Please analyze private employer text here.; "
                    "key sk-test-secret-value; Authorization: Bearer header-secret-value"
                ),
            }},
            api_key="sk-test-secret-value",
            submitted="Please analyze private employer text here.",
        )
        self.assertIn("error_message=Invalid request for [redacted]", log_output)
        self.assertNotIn("private employer text", log_output)
        self.assertNotIn("sk-test-secret-value", log_output)
        self.assertNotIn("header-secret-value", log_output)

    def test_connection_diagnostic_logs_only_cause_types(self):
        nested_cause = OSError("nested private detail and api key sk-nested-secret")
        cause = ValueError("proxy credential proxy-password-secret")
        cause.__cause__ = nested_cause
        error = APIConnectionError(
            request=httpx.Request(
                "POST", "https://private-host.invalid/path?token=url-secret"
            )
        )
        error.__cause__ = cause

        class FakeCompletions:
            def create(self, **kwargs):
                raise error

        class FakeGroq:
            def __init__(self, **kwargs):
                self.chat = type("Chat", (), {"completions": FakeCompletions()})()

        captured = []

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                captured.append(record.getMessage())

        handler = CaptureHandler()
        service_logger = logging.getLogger("ai_service")
        service_logger.addHandler(handler)
        try:
            with patch.object(ai_service, "Groq", FakeGroq):
                with self.assertRaises(ai_service.AnalysisServiceError):
                    ai_service.analyze_submission(
                        api_key="sk-test-api-secret",
                        job_description="Private submitted job description.",
                        current_skills="SQL",
                        projects_and_work="Private project details.",
                    )
        finally:
            service_logger.removeHandler(handler)

        output = "\n".join(captured)
        self.assertIn("exception_type=APIConnectionError", output)
        self.assertIn("cause_type=ValueError", output)
        self.assertIn("nested_cause_type=OSError", output)
        for sensitive in (
            "nested private detail", "sk-nested-secret", "proxy credential",
            "proxy-password-secret", "private-host.invalid", "url-secret",
            "sk-test-api-secret", "Private submitted job description",
            "Private project details",
        ):
            self.assertNotIn(sensitive, output)

    def test_json_validate_failed_summarizes_candidate_without_logging_it(self):
        candidate = {
            "role_title": "Confidential employer internship",
            "overview": "private submitted project details",
        }
        log_output, _, _, _ = self._run_bad_request(
            {"error": {
                "code": "json_validate_failed",
                "message": "Generated JSON did not match the requested schema. Please adjust your prompt.",
                "failed_generation": candidate,
            }},
            api_key="sk-test-secret-value",
            submitted="Confidential employer internship and private submitted project details.",
        )
        self.assertIn("error_code=json_validate_failed", log_output)
        self.assertIn("error_message=structured_output_validation_failed", log_output)
        self.assertNotIn("Please adjust your prompt", log_output)
        self.assertIn("validation_detail=candidate_schema_mismatch:missing=", log_output)
        self.assertNotIn("Confidential employer internship", log_output)
        self.assertNotIn("private submitted project details", log_output)
        self.assertNotIn("failed_generation", log_output)

    def test_json_validate_failed_logs_safe_parse_location_not_candidate(self):
        submitted_private_text = "private employer details and personal project example"
        candidate = '{"role_title":"' + submitted_private_text
        log_output, _, _, _ = self._run_bad_request(
            {"error": {
                "code": "json_validate_failed",
                "message": "Generated JSON did not match the requested format.",
                "failed_generation": candidate,
            }},
            api_key="sk-test-secret-value",
            submitted=submitted_private_text,
        )

        self.assertIn("validation_detail=candidate_not_valid_json", log_output)
        self.assertIn("parse_error=Unterminated string starting at", log_output)
        self.assertIn("near_end=true", log_output)
        self.assertIn(f"chars={len(candidate)}", log_output)
        self.assertNotIn(submitted_private_text, log_output)
        self.assertNotIn("personal project example", log_output)
        self.assertNotIn("sk-test-secret-value", log_output)
        self.assertNotIn(candidate, log_output)

    def test_json_validate_failed_logs_safe_nonterminal_parse_location(self):
        candidate = "<private-prefix> {\"role_title\":\"private employer text\"}"
        log_output, _, _, _ = self._run_bad_request(
            {"error": {
                "code": "json_validate_failed",
                "message": "Generated response is not valid JSON.",
                "failed_generation": candidate,
            }},
            api_key="sk-test-secret-value",
            submitted="private employer text",
        )

        self.assertIn("parse_error=Expecting value", log_output)
        self.assertIn("near_end=false", log_output)
        self.assertNotIn("private-prefix", log_output)
        self.assertNotIn("private employer text", log_output)

    def test_completion_token_exhaustion_fails_safely_without_retry(self):
        private_candidate = {
            "role_title": "Private internship title",
            "overview": "Private submitted context",
        }
        log_output, request, client_options, request_count = self._run_bad_request(
            {"error": {
                "code": "json_validate_failed",
                "message": (
                    "Maximum completion tokens were reached before valid structured output; "
                    "candidate is missing required content for the private role."
                ),
                "failed_generation": private_candidate,
            }},
            api_key="sk-test-secret-value",
            submitted="Private role and project details that must not appear.",
        )
        self.assertIn("error_code=json_validate_failed", log_output)
        self.assertIn("error_message=structured_output_validation_failed", log_output)
        self.assertNotIn("Maximum completion tokens were reached", log_output)
        self.assertIn("validation_detail=candidate_schema_mismatch:missing=", log_output)
        self.assertNotIn("Private internship title", log_output)
        self.assertNotIn("Private submitted context", log_output)
        self.assertNotIn("Private role and project details", log_output)
        self.assertNotIn("sk-test-secret-value", log_output)
        self.assertEqual(request["max_completion_tokens"], 6144)
        self.assertEqual(request["reasoning_effort"], "low")
        self.assertEqual(client_options["max_retries"], 0)
        self.assertEqual(request_count, 1)

    def test_schema_uses_documented_arrays_enums_and_references(self):
        schema = ai_service.groq_response_schema()
        self.assertEqual(schema["properties"]["skill_assessments"]["type"], "array")
        self.assertEqual(schema["properties"]["skill_assessments"]["items"]["type"], "object")
        self.assertNotIn("plan_days", schema["properties"])
        skill_properties = schema["properties"]["skill_assessments"]["items"]["properties"]
        self.assertEqual(
            skill_properties["evidence_category"]["enum"],
            ["Evidence provided", "Partial evidence", "Evidence not provided"],
        )
        self.assertEqual(skill_properties["requirement_type"]["enum"], ["explicit", "preferred", "inferred"])

    def test_synthetic_grounding_rejection_logs_only_safe_field_diagnostic(self):
        # Simulate valid JSON from Groq whose quoted evidence is not present in
        # the submitted examples. This is one concrete AnalysisValidationError
        # branch; the previous generic log did not reveal whether this was the
        # branch hit by the reported live response.
        candidate = {
            "role_title": "Data Analyst Intern",
            "overview": "A synthetic analysis for diagnostics.",
            "skill_assessments": [{
                "skill_name": "SQL",
                "requirement_type": "explicit",
                "job_description_basis_id": "jd_001",
                "uncertainty_note": "",
                "evidence_category": "Evidence provided",
                "supporting_example_quote": "private generated quote not submitted",
                "what_is_missing": "A detailed example explaining analysis decisions and measured results.",
                "suggested_next_step": "Document a query example.",
            }],
            "plan_days": synthetic_provider_plan("SQL"),
            "assumptions_and_limitations": "Synthetic test only.",
        }
        assessment_candidate = {
            key: value for key, value in candidate.items() if key != "plan_days"
        }
        plan_candidate = {
            "plan_days": [
                {
                    **{key: value for key, value in day.items() if key != "targeted_skill_name"},
                    "targeted_priority_id": "priority_1",
                }
                for day in candidate["plan_days"]
            ]
        }
        fake_contents = [json.dumps(assessment_candidate), json.dumps(plan_candidate)]

        class FakeCompletions:
            def create(self, **kwargs):
                content = fake_contents.pop(0)
                return type("Response", (), {
                    "choices": [type("Choice", (), {
                        "finish_reason": "stop",
                        "message": type("Message", (), {"content": content})(),
                    })()]
                })()

        class FakeGroq:
            def __init__(self, **kwargs):
                self.chat = type("Chat", (), {"completions": FakeCompletions()})()

        captured = []

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                captured.append(record.getMessage())

        handler = CaptureHandler()
        service_logger = logging.getLogger("ai_service")
        service_logger.addHandler(handler)
        try:
            with patch.object(ai_service, "Groq", FakeGroq):
                with self.assertRaises(ai_service.AnalysisValidationError):
                    ai_service.analyze_submission(
                        api_key="sk-test-secret-value",
                        job_description="SQL internship requirement",
                        current_skills="SQL",
                        projects_and_work="A completed dashboard project.",
                    )
        finally:
            service_logger.removeHandler(handler)

        output = "\n".join(captured)
        self.assertIn("field_path=skill_assessments[0].supporting_example_quote", output)
        self.assertIn("error_type=grounding_mismatch", output)
        self.assertIn("expected_type=verbatim project/work excerpt", output)
        self.assertNotIn("private generated quote", output)
        self.assertNotIn("completed dashboard project", output)
        self.assertNotIn("sk-test-secret-value", output)

    def test_pydantic_diagnostic_excludes_invalid_values_and_messages(self):
        candidate = {
            "role_title": "private role text",
            "overview": "overview",
            "skill_assessments": [],
            "plan_days": [{"day_number": "private value"}],
            "assumptions_and_limitations": "limitations",
        }
        with self.assertRaises(ValidationError) as raised:
            AnalysisResult.model_validate(candidate)

        diagnostics = " ".join(ai_service._safe_validation_diagnostics(raised.exception))
        self.assertIn("field_path=skill_assessments", diagnostics)
        self.assertIn("error_type=too_short", diagnostics)
        self.assertIn("expected_type=array with required minimum length", diagnostics)
        self.assertIn("field_path=plan_days[0].day_number", diagnostics)
        self.assertIn("error_type=int_type", diagnostics)
        self.assertNotIn("private role text", diagnostics)
        self.assertNotIn("private value", diagnostics)


class MissingEvidenceDescriptionTests(unittest.TestCase):
    @staticmethod
    def assessment(what_is_missing):
        return {
            "skill_name": "SQL",
            "requirement_type": "explicit",
            "job_description_basis_id": "jd_001",
            "uncertainty_note": "",
            "evidence_category": "Evidence not provided",
            "supporting_example_quote": "",
            "what_is_missing": what_is_missing,
            "suggested_next_step": "Create a short SQL analysis with joins.",
        }

    def test_rejects_empty_short_and_fragmentary_gap_descriptions(self):
        for text in ("", "   ", "SQL", "A project", "More evidence needed"):
            with self.subTest(text=text), self.assertRaises(ValidationError):
                GroqSkillAssessment.model_validate(self.assessment(text))

    def test_accepts_concrete_gap_description_and_schema_stays_groq_compatible(self):
        text = "A SQL query example showing joins and grouped totals."
        result = GroqSkillAssessment.model_validate(self.assessment(text))
        self.assertEqual(result.what_is_missing, text)

        # The provider schema intentionally stays within its existing subset;
        # the stronger minimum and word-count checks run locally in Pydantic.
        provider_schema = ai_service.groq_response_schema()
        self.assertNotIn("minLength", json.dumps(provider_schema))
        local_schema = AnalysisResult.model_json_schema()
        self.assertTrue(any(
            isinstance(node, dict) and node.get("minLength") == 20
            for node in walk_schema(local_schema)
        ))


class EvidenceGroundingTests(unittest.TestCase):
    JOB_DESCRIPTION = "Data Analyst Intern will use SQL for analysis."

    @staticmethod
    def make_result(
        quote,
        category="Evidence provided",
        basis="will use SQL for analysis",
        requirement_type="explicit",
    ):
        return AnalysisResult.model_validate({
            "role_title": "Data Analyst Intern",
            "overview": "A synthetic test assessment.",
            "skill_assessments": [{
                "skill_name": "SQL",
                "requirement_type": requirement_type,
                "job_description_basis": basis,
                "uncertainty_note": (
                    "This exact phrase suggests a communication requirement."
                    if requirement_type == "inferred" else ""
                ),
                "evidence_category": category,
                "skill_claimed_by_user": True,
                "supporting_example_quote": quote,
                "what_is_missing": "A detailed result note explaining query outputs and conclusions.",
                "suggested_next_step": "Document one result and its limits.",
            }],
            
            "plan_days": [{
                "day_number": number,
                "task": [
                    "Create a SQL project folder and document the query objective.",
                    "Extend the SQL project by saving a sample query and its results.",
                    "Improve the SQL analysis file by documenting query outputs.",
                    "Refine the SQL analysis file by checking query results and recording errors.",
                    "Update the SQL analysis file with corrected queries and documented results.",
                    "Expand the SQL analysis file with a findings note and conclusions.",
                    "Extend the SQL analysis file by packaging it with a README describing the results.",
                ][number - 1],
                "deliverable": [
                    "SQL project folder with a query objective note.",
                    "Saved SQL analysis file containing a sample query and results.",
                    "Updated SQL analysis file with documented query outputs.",
                    "Checked SQL analysis file with a recorded results and errors log.",
                    "Revised SQL analysis file with corrected queries and documented results.",
                    "SQL analysis file with a findings note and conclusions.",
                    "Completed SQL analysis file and README describing query results.",
                ][number - 1],
                "targeted_gap": "SQL — Evidence gap: A detailed result note explaining query outputs and conclusions.",
                "why_it_matters": "Documents SQL query outputs and conclusions as evidence of analytical work.",
                "completion_criterion": [
                    "The SQL project folder exists and contains a query objective note.",
                    "The SQL analysis file is saved and opens with a sample query and results.",
                    "The SQL analysis file contains documented query outputs.",
                    "The results log records checked queries and any errors.",
                    "The SQL analysis file contains corrected queries and documented results.",
                    "The findings note lists query results and conclusions.",
                    "The SQL analysis file and README are saved and open.",
                ][number - 1],
            } for number in range(1, 8)],
            "assumptions_and_limitations": "Synthetic test; ability is not verified.",
        })


    def validate_quote(self, quote, project_text):
        return self.make_result(quote).validate_against_submission(
            job_description=self.JOB_DESCRIPTION,
            current_skills="SQL",
            projects_and_work=project_text,
        )

    def validate_basis(self, basis, job_text, requirement_type="explicit"):
        result = self.make_result(
            "", category="Evidence not provided", basis=basis,
            requirement_type=requirement_type,
        )
        return result.validate_against_submission(
            job_description=job_text,
            current_skills="SQL",
            projects_and_work="",
        )

    def test_accepts_exact_basis_for_explicit_preferred_and_inferred_items(self):
        job = "Data Analyst Intern: SQL is required; Excel is preferred. Explain findings to the team."
        cases = [
            ("SQL is required", "explicit"),
            ("Excel is preferred", "preferred"),
            ("Explain findings to the team", "inferred"),
        ]
        for basis, kind in cases:
            with self.subTest(requirement_type=kind):
                result = self.validate_basis(basis, job, kind)
                self.assertEqual(result.skill_assessments[0].requirement_type, kind)

    def test_helpful_wording_is_preferred_not_explicit(self):
        job = "Power BI is helpful for the internship."
        result = self.make_result(
            "", category="Evidence not provided", basis=job,
            requirement_type="explicit",
        ).model_copy(update={"skill_assessments": [
            self.make_result(
                "", category="Evidence not provided", basis=job,
                requirement_type="explicit",
            ).skill_assessments[0].model_copy(update={"skill_name": "Power BI"})
        ]})
        with self.assertRaises(AnalysisValidationError) as raised:
            result.validate_against_submission(
                job_description=job, current_skills="", projects_and_work=""
            )
        self.assertEqual(raised.exception.category, "classification_mismatch")
        self.assertEqual(raised.exception.field_path,
                         ("skill_assessments", 0, "requirement_type"))

    def test_helpful_wording_does_not_reclassify_another_skill_in_same_excerpt(self):
        job = "SQL is required; Experience with Power BI is helpful."
        result = self.make_result(
            "", category="Evidence not provided", basis="SQL is required",
            requirement_type="explicit",
        )
        result.validate_against_submission(
            job_description=job, current_skills="SQL", projects_and_work=""
        )

    def test_basis_allows_only_whitespace_and_canonical_unicode_normalization(self):
        job = "Data Analyst Intern: SQL\r\n  is required; café reporting."
        self.validate_basis("SQL is required", job)

        decomposed_job = "Data Analyst Intern: use cafe\u0301 sales data."
        self.validate_basis("use café sales data", decomposed_job)

    def test_basis_rejects_paraphrase_case_punctuation_and_fabrication(self):
        job = "Data Analyst Intern: SQL is required, with careful reporting."
        invalid_bases = [
            "SQL must be used",  # paraphrase
            "sql is required",  # changed capitalization
            "SQL is required;",  # punctuation not present at this position
            "Python is required",  # fabricated excerpt
        ]
        for basis in invalid_bases:
            with self.subTest(basis=basis):
                with self.assertRaises(AnalysisValidationError) as raised:
                    self.validate_basis(basis, job)
                self.assertEqual(raised.exception.category, "grounding_mismatch")
                self.assertEqual(
                    raised.exception.field_path,
                    ("skill_assessments", 0, "job_description_basis"),
                )

    def test_basis_cannot_be_empty_or_missing_under_current_schema(self):
        with self.assertRaises(ValidationError):
            self.make_result("", category="Evidence not provided", basis="")
        candidate = self.make_result("", category="Evidence not provided").model_dump()
        del candidate["skill_assessments"][0]["job_description_basis"]
        with self.assertRaises(ValidationError):
            AnalysisResult.model_validate(candidate)

    def test_accepts_verbatim_quote_and_normalized_whitespace(self):
        project = "I used SQL to join orders\r\n\tand summarize sales."
        exact = self.validate_quote(
            "I used SQL to join orders and summarize sales.", project
        )
        self.assertEqual(exact.skill_assessments[0].evidence_category, "Evidence provided")

        # Whitespace is tolerated; punctuation and casing are kept intact.
        whitespace = self.validate_quote(
            "join orders and summarize", project
        )
        self.assertEqual(whitespace.skill_assessments[0].skill_name, "SQL")

        canonical_unicode = self.validate_quote("café sales", "I analyzed cafe\u0301 sales with SQL.")
        self.assertEqual(canonical_unicode.skill_assessments[0].skill_name, "SQL")

    def test_rejects_excerpt_not_present_and_does_not_log_its_value(self):
        result = self.make_result("I used SQL to analyze revenue.")
        with self.assertRaises(AnalysisValidationError) as raised:
            result.validate_against_submission(
                job_description=self.JOB_DESCRIPTION,
                current_skills="SQL",
                projects_and_work="I used SQL to join orders and summarize sales.",
            )
        self.assertEqual(
            raised.exception.field_path,
            ("skill_assessments", 0, "supporting_example_quote"),
        )
        self.assertEqual(raised.exception.category, "grounding_mismatch")
        self.assertNotIn("analyze revenue", str(raised.exception))

    def test_casing_and_punctuation_changes_are_not_treated_as_verbatim(self):
        for quote in (
            "used sql to join orders",
            "I used SQL to join orders; and summarize sales.",
        ):
            with self.subTest(quote=quote):
                with self.assertRaises(AnalysisValidationError):
                    self.validate_quote(quote, "I used SQL to join orders and summarize sales.")

    def test_skill_claim_without_project_example_remains_evidence_not_provided(self):
        result = self.make_result("", category="Evidence not provided")
        result.validate_against_submission(
            job_description=self.JOB_DESCRIPTION,
            current_skills="SQL",
            projects_and_work="",
        )
        assessment = result.skill_assessments[0]
        self.assertTrue(assessment.skill_claimed_by_user)
        self.assertEqual(assessment.display_evidence_label, "Skill claimed — evidence not provided")

    def test_empty_quote_is_allowed_only_for_no_evidence_and_field_is_required(self):
        self.make_result("", category="Evidence not provided")
        with self.assertRaises(ValidationError):
            self.make_result("")

        omitted = self.make_result("", category="Evidence not provided").model_dump()
        del omitted["skill_assessments"][0]["supporting_example_quote"]
        with self.assertRaises(ValidationError):
            AnalysisResult.model_validate(omitted)

        with self.assertRaises(ValidationError):
            self.make_result("SQL project quote", category="Evidence not provided")

    def test_claim_flag_is_derived_only_from_submitted_skills(self):
        # Built-in sample makes Excel/SQL claims explicit. “Attention to
        # detail” is a job requirement absent from current_skills; a written
        # summary is mentioned in project/work but is not a listed skill.
        self.assertTrue(skill_name_was_reported("Excel", SAMPLE_CURRENT_SKILLS))
        self.assertFalse(skill_name_was_reported("Attention to detail", SAMPLE_CURRENT_SKILLS))
        self.assertFalse(skill_name_was_reported("written summary", SAMPLE_CURRENT_SKILLS))

        # Whitespace and casing are normalized, while token boundaries avoid
        # claiming SQL based only on the different word “NoSQL”.
        self.assertTrue(skill_name_was_reported("POWER   BI", "power\tbi (beginner)"))
        self.assertTrue(skill_name_was_reported("written communication", SAMPLE_CURRENT_SKILLS))
        self.assertFalse(skill_name_was_reported("SQL", "NoSQL"))

    def test_provider_does_not_generate_claim_flag_and_result_derives_it(self):
        provider_candidate = {
            "role_title": "Data Analyst Intern",
            "overview": "Synthetic test response.",
            "skill_assessments": [
                {
                    "skill_name": "SQL", "requirement_type": "explicit",
                    "job_description_basis_id": "jd_001",
                    "uncertainty_note": "", "evidence_category": "Evidence not provided",
                    "supporting_example_quote": "", "what_is_missing": "A SQL project demonstrating joins, grouped totals, and findings.",
                    "suggested_next_step": "Create a query-based analysis.",
                },
                {
                    "skill_name": "written summary", "requirement_type": "inferred",
                    "job_description_basis_id": "jd_002",
                    "uncertainty_note": "Explaining findings suggests communication.",
                    "evidence_category": "Partial evidence",
                    "supporting_example_quote": "wrote a short summary of three patterns",
                    "what_is_missing": "A recommendation for a business audience with supporting figures.",
                    "suggested_next_step": "Add a concise recommendation.",
                },
            ],
            "plan_days": synthetic_provider_plan("SQL"),
            "assumptions_and_limitations": "Synthetic test; ability is not verified.",
        }

        provider = GroqAnalysisResponse.model_validate(provider_candidate)
        excerpts = ai_service.extract_job_description_excerpts(SAMPLE_JOB_DESCRIPTION)
        result = provider.with_user_skill_claims(SAMPLE_CURRENT_SKILLS, excerpts)
        self.assertTrue(result.skill_assessments[0].skill_claimed_by_user)
        self.assertFalse(result.skill_assessments[1].skill_claimed_by_user)
        self.assertEqual(
            result.skill_assessments[0].display_evidence_label,
            "Skill claimed — evidence not provided",
        )
        self.assertEqual([day.day_number for day in result.plan_days], list(range(1, 8)))

        # A contradictory/generated flag is not silently overwritten: the
        # provider model rejects it as an unexpected field.
        provider_candidate["skill_assessments"][0]["skill_claimed_by_user"] = False
        with self.assertRaises(ValidationError) as rejected:
            GroqAnalysisResponse.model_validate(provider_candidate)
        error = rejected.exception.errors(include_input=False)[0]
        self.assertEqual(error["loc"], ("skill_assessments", 0, "skill_claimed_by_user"))
        self.assertEqual(error["type"], "extra_forbidden")


class JobDescriptionExcerptIdTests(unittest.TestCase):
    def test_excerpts_are_stable_verbatim_source_fragments(self):
        source = "Role: Data Analyst.\nUse SQL, not sql; retain punctuation!"
        excerpts = ai_service.extract_job_description_excerpts(source)
        self.assertEqual(list(excerpts), ["jd_001", "jd_002"])
        self.assertEqual(excerpts["jd_001"], "Role: Data Analyst.")
        self.assertEqual(excerpts["jd_002"], "Use SQL, not sql; retain punctuation!")
        self.assertIn(excerpts["jd_001"], source)
        self.assertIn(excerpts["jd_002"], source)

    def test_provider_selects_source_id_and_application_preserves_case_punctuation(self):
        source = "Required: SQL. Preferred: Power BI?"
        excerpts = ai_service.extract_job_description_excerpts(source)
        provider = GroqAnalysisResponse.model_validate({
            "role_title": "Analyst Intern", "overview": "Short assessment.",
            "skill_assessments": [{
                "skill_name": "SQL", "requirement_type": "explicit",
                "job_description_basis_id": "jd_001", "uncertainty_note": "",
                "evidence_category": "Evidence not provided", "supporting_example_quote": "",
                "what_is_missing": "A SQL query example demonstrating joins and aggregated totals.", "suggested_next_step": "Build a query example.",
            }, {
                "skill_name": "Power BI", "requirement_type": "preferred",
                "job_description_basis_id": "jd_002", "uncertainty_note": "",
                "evidence_category": "Evidence not provided", "supporting_example_quote": "",
                "what_is_missing": "A dashboard example with labeled metrics and clear trends.", "suggested_next_step": "Save a small dashboard.",
            }],
            "plan_days": synthetic_provider_plan("SQL"),
            "assumptions_and_limitations": "No ability was independently verified.",
        })
        result = provider.with_user_skill_claims("", excerpts)
        self.assertEqual(result.skill_assessments[0].job_description_basis, "Required: SQL.")
        self.assertEqual(result.skill_assessments[1].job_description_basis, "Preferred: Power BI?")

        # Provider output cannot supply a paraphrase or a differently cased/
        # punctuated replacement; free-form basis text is forbidden by schema.
        provider_payload = provider.model_dump()
        provider_payload["skill_assessments"][0]["job_description_basis"] = "required: sql"
        with self.assertRaises(ValidationError) as raised:
            GroqAnalysisResponse.model_validate(provider_payload)
        self.assertEqual(raised.exception.errors(include_input=False)[0]["type"], "extra_forbidden")

    def test_unknown_excerpt_id_rejects_even_an_inferred_requirement(self):
        provider = GroqAnalysisResponse.model_validate({
            "role_title": "Analyst Intern", "overview": "Short assessment.",
            "skill_assessments": [{
                "skill_name": "Leadership", "requirement_type": "inferred",
                "job_description_basis_id": "jd_999", "uncertainty_note": "No source clue.",
                "evidence_category": "Evidence not provided", "supporting_example_quote": "",
                "what_is_missing": "A relevant example demonstrating project decisions and results.", "suggested_next_step": "Document a project decision.",
            }],
            "plan_days": synthetic_provider_plan("Leadership"),
            "assumptions_and_limitations": "No ability was independently verified.",
        })
        with self.assertRaises(AnalysisValidationError) as raised:
            provider.with_user_skill_claims("", {"jd_001": "Use SQL."})
        self.assertEqual(raised.exception.category, "grounding_mismatch")
        self.assertEqual(raised.exception.field_path,
                         ("skill_assessments", 0, "job_description_basis_id"))


class IndependentPlanTests(unittest.TestCase):
    @staticmethod
    def day(**updates):
        values = {
            "day_number": 6,
            "task": "Interpret results and document findings.",
            "deliverable": "A concise findings note.",
            "targeted_gap": "Analytical communication.",
            "why_it_matters": "Connects results to a business question.",
            "completion_criterion": "The note includes one finding and one limitation.",
        }
        values.update(updates)
        return values

    def test_plan_day_rejects_peer_review_and_questions_answered(self):
        for updates in (
            {"task": "Request peer review of the dashboard."},
            {"completion_criterion": "The list of questions answered is saved."},
        ):
            with self.subTest(updates=updates), self.assertRaises(ValidationError):
                PlanDay.model_validate(self.day(**updates))

    def test_plan_day_accepts_independent_self_check_and_open_questions(self):
        day = PlanDay.model_validate(self.day(
            deliverable="A self-review checklist and documented open questions.",
            completion_criterion="The checklist is complete and open questions are recorded.",
        ))
        self.assertEqual(day.day_number, 6)

    def test_plan_day_rejects_subjective_completion_criterion(self):
        with self.assertRaisesRegex(ValidationError, "objectively checkable"):
            PlanDay.model_validate(self.day(
                completion_criterion="The user understands the analysis and feels ready."
            ))

    def test_provider_plan_criterion_requires_an_observable_result(self):
        def day(number, criterion):
            return {
                "day_number": number,
                "task": f"Create the SQL analysis file with day {number} results.",
                "deliverable": f"Saved SQL analysis file containing day {number} results.",
                "targeted_gap": "SQL — Evidence gap: A documented SQL query example with results.",
                "why_it_matters": "This documents the SQL evidence gap.",
                "completion_criterion": criterion,
            }

        valid_criteria = (
            "The SQL analysis file is saved and opens.",
            "The data-quality note lists four cleaning decisions.",
            "The dashboard file opens and shows three labeled charts.",
            "The validation checklist passes all five documented checks.",
        )
        for criterion in valid_criteria:
            with self.subTest(criterion=criterion):
                self.assertTrue(completion_criterion_is_checkable(criterion))

        invalid_criteria = (
            "I understand the SQL topic and feel confident.",
            "A dashboard with three charts and clear labels.",
            "The project makes progress and feels ready.",
        )
        for criterion in invalid_criteria:
            with self.subTest(criterion=criterion):
                with self.assertRaises(ValidationError):
                    PlanDay.model_validate(day(1, criterion))

        response = {
            "plan_days": [
                day(number, "I understand the topic and feel confident." if number == 6 else
                    f"The SQL analysis file is saved and contains day {number} results.")
                for number in range(1, 8)
            ],
            "role_title": "Analyst Intern",
            "overview": "A test assessment.",
            "skill_assessments": [{
                "skill_name": "SQL", "requirement_type": "explicit",
                "job_description_basis": "SQL is required", "uncertainty_note": "",
                "evidence_category": "Evidence not provided", "skill_claimed_by_user": False,
                "supporting_example_quote": "",
                "what_is_missing": "A documented SQL query example with results.",
                "suggested_next_step": "Create a small SQL example.",
            }],
            "assumptions_and_limitations": "Synthetic test; ability is not verified.",
        }
        with self.assertRaises(ValidationError) as rejected:
            AnalysisResult.model_validate(response)
        diagnostic = " ".join(ai_service._safe_validation_diagnostics(rejected.exception))
        self.assertIn("field_path=plan_days[].completion_criterion", diagnostic)
        self.assertIn("error_type=criterion_not_checkable", diagnostic)
        self.assertIn("expected_type=objective completion criterion", diagnostic)

    def test_skill_next_step_rejects_peer_presentation_and_feedback(self):
        with self.assertRaises(ValidationError):
            GroqSkillAssessment.model_validate({
                "skill_name": "Communication", "requirement_type": "inferred",
                "job_description_basis_id": "jd_001",
                "uncertainty_note": "Presenting findings suggests communication.",
                "evidence_category": "Evidence not provided", "supporting_example_quote": "",
                "what_is_missing": "A concise findings explanation supported by analysis results.",
                "suggested_next_step": "Present summary to a peer and record feedback.",
            })

    def test_skill_next_step_accepts_self_recording_and_checklist(self):
        assessment = GroqSkillAssessment.model_validate({
            "skill_name": "Communication", "requirement_type": "inferred",
            "job_description_basis_id": "jd_001",
            "uncertainty_note": "Presenting findings suggests communication.",
            "evidence_category": "Evidence not provided", "supporting_example_quote": "",
            "what_is_missing": "A concise findings explanation supported by analysis results.",
            "suggested_next_step": (
                "Record a short presentation and review it using a self-checklist."
            ),
        })
        self.assertIn("self-checklist", assessment.suggested_next_step)


class PlanAlignmentTests(unittest.TestCase):
    @staticmethod
    def response(plan_days=None, missing="A SQL query example demonstrating joins and grouped totals."):
        return {
            "role_title": "Analyst Intern",
            "overview": "A synthetic portfolio assessment.",
            "skill_assessments": [{
                "skill_name": "SQL", "requirement_type": "explicit",
                "job_description_basis_id": "jd_001", "uncertainty_note": "",
                "evidence_category": "Evidence not provided", "supporting_example_quote": "",
                "what_is_missing": missing,
                "suggested_next_step": "Build a documented SQL query analysis.",
            }],
            "plan_days": plan_days if plan_days is not None else synthetic_provider_plan("SQL"),
            "assumptions_and_limitations": "Synthetic only; ability is not verified.",
        }

    @staticmethod
    def multi_target_response(target_count):
        skill_names = ["SQL", "Excel", "Power BI", "Python", "Statistics", "Communication", "Documentation"]
        selected = skill_names[:target_count]
        assessments = [{
            "skill_name": skill,
            "requirement_type": "explicit",
            "job_description_basis_id": "jd_001",
            "uncertainty_note": "",
            "evidence_category": "Evidence not provided",
            "supporting_example_quote": "",
            "what_is_missing": f"A documented {skill} example with clear steps and concrete results.",
            "suggested_next_step": f"Create a small {skill} analysis example.",
        } for skill in skill_names[:max(target_count, 1)]]
        days = []
        for number in range(1, 8):
            skill = selected[(number - 1) % len(selected)]
            action = "Create" if number == 1 else "Extend the prior"
            days.append({
                "day_number": number,
                "task": f"{action} {skill} portfolio project artifact with day {number} work.",
                "deliverable": f"Saved {skill} portfolio project artifact with day {number} output.",
                "targeted_skill_name": skill,
                "why_it_matters": f"This adds {skill} evidence to the selected gap.",
                "completion_criterion": (
                    f"The saved {skill} portfolio project artifact contains day {number} output."
                ),
            })
        return {
            "role_title": "Analyst Intern",
            "overview": "A synthetic portfolio assessment.",
            "skill_assessments": assessments,
            "plan_days": days,
            "assumptions_and_limitations": "Synthetic only; ability is not verified.",
        }

    def test_plan_accepts_one_two_or_three_consistent_targets(self):
        for target_count in (1, 2, 3):
            with self.subTest(target_count=target_count):
                result = GroqAnalysisResponse.model_validate(
                    self.multi_target_response(target_count)
                )
                targets = {day.targeted_skill_name for day in result.plan_days}
                self.assertLessEqual(len(targets), 3)
                self.assertEqual(len(targets), target_count)
                self.assertTrue(targets.issubset({
                    item.skill_name for item in result.skill_assessments
                }))
                self.assertEqual(
                    [day.day_number for day in result.plan_days], list(range(1, 8))
                )

    def test_plan_rejects_four_or_more_distinct_targets(self):
        for target_count in (4, 5, 6, 7):
            with self.subTest(target_count=target_count):
                candidate = self.multi_target_response(target_count)
                with self.assertRaisesRegex(ValidationError, "no more than three evidence gaps"):
                    GroqAnalysisResponse.model_validate(candidate)

    def test_rejects_task_that_does_not_address_its_target_gap(self):
        candidate = self.response()
        candidate["plan_days"][0].update({
            "task": "Write private unrelated notes for a different topic.",
            "deliverable": "A private unrelated notes document.",
            "why_it_matters": "This records a private general experience.",
            "completion_criterion": "The private unrelated notes document is saved and opens.",
        })
        with self.assertRaises(ValidationError) as raised:
            GroqAnalysisResponse.model_validate(candidate)
        diagnostics = " ".join(ai_service._safe_validation_diagnostics(raised.exception))
        self.assertIn(
            "field_path=plan_days[].task/deliverable/why_it_matters->targeted_skill",
            diagnostics,
        )
        self.assertIn("error_type=gap_alignment_mismatch", diagnostics)
        self.assertIn("expected_type=work addressing its targeted evidence gap", diagnostics)
        self.assertNotIn("private unrelated notes", diagnostics)
        self.assertNotIn("different topic", diagnostics)

    def test_duplicate_skill_root_error_has_specific_safe_diagnostic(self):
        candidate = self.response()
        candidate["skill_assessments"].append(dict(candidate["skill_assessments"][0]))
        with self.assertRaises(ValidationError) as raised:
            GroqAnalysisResponse.model_validate(candidate)

        errors = raised.exception.errors(include_input=False)
        self.assertEqual(errors[0].get("loc"), ())
        diagnostics = " ".join(ai_service._safe_validation_diagnostics(raised.exception))
        self.assertIn("field_path=skill_assessments[].skill_name", diagnostics)
        self.assertIn("error_type=duplicate_skill_name", diagnostics)
        self.assertIn("expected_type=unique assessed skill names", diagnostics)
        self.assertNotIn("Each identified skill must appear only once", diagnostics)

    def test_rejects_deliverable_or_completion_check_unrelated_to_task_output(self):
        for field_name, value in (
            ("deliverable", "A labeled Power BI dashboard file."),
            ("completion_criterion", "The final presentation recording plays."),
        ):
            candidate = self.response()
            candidate["plan_days"][0][field_name] = value
            with self.subTest(field=field_name), self.assertRaises(ValidationError):
                GroqAnalysisResponse.model_validate(candidate)

    def test_repeated_gap_requires_progression_from_prior_deliverable(self):
        candidate = self.response()
        candidate["plan_days"][1].update({
            "task": "Create a separate SQL query example for a new question.",
            "deliverable": "A separate SQL query example with grouped totals.",
            "why_it_matters": "It adds another SQL query example.",
            "completion_criterion": "The separate SQL query example is saved.",
        })
        with self.assertRaisesRegex(ValidationError, "Repeated evidence gaps"):
            GroqAnalysisResponse.model_validate(candidate)

    def test_assumptions_document_gap_requires_create_then_improve_artifact(self):
        missing = "An assumptions document listing data choices and their reasons."
        plan = synthetic_provider_plan("Documentation")
        plan[0].update({
            "task": "Create an assumptions log for the dataset choices.",
            "deliverable": "A saved assumptions log listing dataset choices.",
            "why_it_matters": "This documents assumptions for the project.",
            "completion_criterion": "The assumptions log is saved and lists dataset choices.",
        })
        plan[1].update({
            "task": "Improve the prior assumptions log with cleaning decisions.",
            "deliverable": "An updated assumptions log with cleaning choices.",
            "why_it_matters": "This improves the assumptions document evidence.",
            "completion_criterion": "The updated assumptions log lists cleaning choices.",
        })
        for number in range(3, 8):
            plan[number - 1].update({
                "task": f"Extend the prior assumptions log with project step {number} decisions.",
                "deliverable": f"An updated assumptions log with step {number} decisions.",
                "why_it_matters": "This extends the assumptions documentation for the project.",
                "completion_criterion": f"The updated assumptions log records step {number} decisions.",
            })
        candidate = self.response(plan, missing=missing)
        candidate["skill_assessments"][0]["skill_name"] = "Documentation"
        GroqAnalysisResponse.model_validate(candidate)

        plan[0].update({
            "task": "Record a short presentation about the assumptions document.",
            "deliverable": "A saved presentation recording about assumptions.",
            "why_it_matters": "This explains assumptions to a viewer.",
            "completion_criterion": "The presentation recording is saved and plays.",
        })
        with self.assertRaisesRegex(ValidationError, "create-and-improve deliverable sequence"):
            GroqAnalysisResponse.model_validate(candidate)


class GeneratedGrammarTests(unittest.TestCase):
    def test_clear_a_an_error_is_corrected_in_plan_prose_only(self):
        day = PlanDay.model_validate({
            "day_number": 1,
            "task": "Create a assumptions log template.",
            "deliverable": "A university dataset brief.",
            "targeted_gap": "Project framing.",
            "why_it_matters": "It gives a useful project starting point.",
            "completion_criterion": "The brief is saved.",
        })
        self.assertEqual(day.task, "Create an assumptions log template.")
        self.assertEqual(day.deliverable, "A university dataset brief.")

    def test_grounded_supporting_quote_is_not_grammar_rewritten(self):
        result = AnalysisResult.model_validate({
            "role_title": "Analyst Intern", "overview": "A concise overview.",
            "skill_assessments": [{
                "skill_name": "Documentation", "requirement_type": "explicit",
                "job_description_basis": "document assumptions",
                "uncertainty_note": "", "evidence_category": "Evidence provided",
                "skill_claimed_by_user": False,
                "supporting_example_quote": "I created a assumptions log template.",
                "what_is_missing": "Create an assumptions log template.",
                "suggested_next_step": "Create a assumptions log template.",
            }],
            "plan_days": [
    {
        **IndependentPlanTests.day(
            day_number=n,
            targeted_gap="Documentation — Evidence gap: Create an assumptions log template.",
        ),
        "task": [
            "Create an assumptions log for project decisions.",
            "Improve the assumptions log with data choices.",
            "Extend the assumptions log with documented reasons.",
            "Refine the assumptions log by checking each reason.",
            "Update the assumptions log with corrected reasons.",
            "Expand the assumptions log with a final findings note.",
            "Extend the assumptions log package with a README.",
        ][n - 1],
        "deliverable": [
            "A saved assumptions log for project decisions.",
            "An improved assumptions log with data choices.",
            "An extended assumptions log with documented reasons.",
            "A checked assumptions log with verified reasons.",
            "An updated assumptions log with corrected reasons.",
            "An expanded assumptions log with a findings note.",
            "An assumptions log package with a README.",
        ][n - 1],
        "completion_criterion": [
            "The assumptions log is saved and lists project decisions.",
            "The assumptions log is saved and lists data choices.",
            "The assumptions log contains documented reasons.",
            "The assumptions log contains checked reasons.",
            "The assumptions log lists corrected reasons.",
            "The findings note is saved and lists assumptions.",
            "The assumptions log package and README are saved.",
        ][n - 1],
    }
    for n in range(1, 8)
],
            "assumptions_and_limitations": "Based on submitted examples.",
        })
        assessment = result.skill_assessments[0]
        self.assertEqual(assessment.supporting_example_quote, "I created a assumptions log template.")
        self.assertEqual(assessment.what_is_missing, "Create an assumptions log template.")
        self.assertEqual(assessment.suggested_next_step, "Create an assumptions log template.")


if __name__ == "__main__":
    unittest.main()



