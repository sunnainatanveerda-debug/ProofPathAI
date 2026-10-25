import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch

import app as proofpath_app
from ai_service import AnalysisServiceError
from models import AnalysisValidationError


def validated_analysis():
    """Return a model fixture whose evidence is grounded in the test submission."""
    
    days = [
    {
        "day_number": 1,
        "task": "Create a SQL project folder and document the query objective.",
        "deliverable": "A SQL project brief documenting the query objective.",
        "targeted_gap": "SQL — Evidence gap: A SQL analysis example with queries.",
        "why_it_matters": "This begins the SQL analysis evidence needed for the portfolio.",
        "completion_criterion": "The saved SQL project brief contains the query objective.",
    },
    {
        "day_number": 2,
        "task": "Extend the SQL project by saving a sample query and its results.",
        "deliverable": "A SQL query file containing a sample query and results.",
        "targeted_gap": "SQL — Evidence gap: A SQL analysis example with queries.",
        "why_it_matters": "This adds a concrete SQL example to the portfolio evidence.",
        "completion_criterion": "The saved SQL query file contains the sample query and its results.",
    },
    {
        "day_number": 3,
        "task": "Improve the SQL query file by documenting query outputs.",
        "deliverable": "A SQL analysis file with documented query outputs.",
        "targeted_gap": "SQL — Evidence gap: A SQL analysis example with queries.",
        "why_it_matters": "Documented outputs help demonstrate the SQL analysis process.",
        "completion_criterion": "The saved SQL analysis file contains documented query outputs.",
    },
    {
        "day_number": 4,
        "task": "Refine the SQL analysis file by checking query results and recording errors.",
        "deliverable": "A SQL analysis file and a query-check log.",
        "targeted_gap": "SQL — Evidence gap: A SQL analysis example with queries.",
        "why_it_matters": "Checking results provides evidence that the SQL work was tested.",
        "completion_criterion": "The saved query-check log records the checks and any errors found.",
    },
    {
        "day_number": 5,
        "task": "Update the SQL analysis file with corrected queries and documented results.",
        "deliverable": "An updated SQL analysis file containing corrected queries and results.",
        "targeted_gap": "SQL — Evidence gap: A SQL analysis example with queries.",
        "why_it_matters": "Corrections and documented results make the SQL example easier to verify.",
        "completion_criterion": "The saved SQL analysis file contains the corrected queries and documented results.",
    },
    {
        "day_number": 6,
        "task": "Expand the SQL analysis file with a findings note and conclusions.",
        "deliverable": "A SQL findings note summarizing query results and conclusions.",
        "targeted_gap": "SQL — Evidence gap: A SQL analysis example with queries.",
        "why_it_matters": "A findings note connects the SQL queries to their results.",
        "completion_criterion": "The saved SQL findings note lists the query results and conclusions.",
    },
    {
        "day_number": 7,
        "task": "Extend the SQL analysis project by packaging the files with a README.",
        "deliverable": "A packaged SQL project containing the analysis files and README.",
        "targeted_gap": "SQL — Evidence gap: A SQL analysis example with queries.",
        "why_it_matters": "A packaged project makes the SQL evidence easier to inspect.",
        "completion_criterion": "The saved README lists the SQL analysis files and explains the project contents.",
    },
]

    return proofpath_app.AnalysisResult.model_validate({
        "role_title": "Data Analyst Intern",
        "overview": "The role focuses on analysis and communicating findings.",
        "skill_assessments": [
            {
                "skill_name": "SQL",
                "requirement_type": "explicit",
                "job_description_basis": "SQL is required",
                "uncertainty_note": "SQL is directly stated in the job description.",
                "evidence_category": "Evidence not provided",
                "skill_claimed_by_user": True,
                "supporting_example_quote": "",
                "what_is_missing": "A SQL analysis example with queries.",
                "suggested_next_step": "Use SQL to answer one project question.",
            },
            {
                "skill_name": "Excel",
                "requirement_type": "preferred",
                "job_description_basis": "Excel experience is preferred",
                "uncertainty_note": "",
                "evidence_category": "Evidence provided",
                "skill_claimed_by_user": True,
                "supporting_example_quote": "I used Excel to clean a public movie ratings spreadsheet and make a pivot table.",
                "what_is_missing": "A short explanation of findings with supporting figures.",
                "suggested_next_step": "Document the cleaning choices and one finding.",
            },
            {
                "skill_name": "Communication",
                "requirement_type": "inferred",
                "job_description_basis": "present findings to the team",
                "uncertainty_note": "Presenting findings suggests communication, but it is an interpretation.",
                "evidence_category": "Partial evidence",
                "skill_claimed_by_user": False,
                "supporting_example_quote": "I wrote a short summary of the findings.",
                "what_is_missing": "A concise explanation of an analysis for an audience.",
                "suggested_next_step": "Write a short findings note with one recommendation.",
            },
        ],
        "plan_days": days,
        "assumptions_and_limitations": "This assessment uses only the submitted examples and does not verify ability.",
    })


class AnalysisFailurePageTests(unittest.TestCase):
    def setUp(self):
        proofpath_app.app.config["TESTING"] = True
        self.client = proofpath_app.app.test_client()

    def test_interpretation_uncertainty_is_supported_by_inferred_type(self):
        analysis = validated_analysis()
        explicit_with_note = analysis.skill_assessments[0].model_copy(
            update={"uncertainty_note": "A contextual note, not an uncertain inference."}
        )
        inferred = analysis.skill_assessments[2]
        self.assertFalse(explicit_with_note.uncertain)
        self.assertTrue(inferred.uncertain)

    def test_failure_keeps_form_values_and_links_to_separate_demo_report(self):
        submitted = {
            "job_description": (
                "Data Analyst Intern. The intern will use SQL to analyze product "
                "data, prepare reports, and communicate findings to the team."
            ),
            "current_skills": "SQL (learning joins), Excel",
            "projects_and_work": "I cleaned a class dataset and made a dashboard.",
        }
        with (
            patch.dict(os.environ, {"GROQ_API_KEY": "offline-test-key"}),
            patch(
                "app.analyze_submission",
                side_effect=AnalysisServiceError("Groq is temporarily unavailable."),
            ) as analyze_mock,
        ):
            response = self.client.post("/analyze", data=submitted)

        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 503)
        for value in submitted.values():
            self.assertIn(value, html)
        self.assertIn("Groq is temporarily unavailable.", html)
        self.assertIn("Demo example — not based on your inputs", html)
        self.assertIn('href="/sample-report"', html)
        self.assertEqual(analyze_mock.call_count, 1)

    def test_demo_report_remains_separate_and_prominently_labeled(self):
        response = self.client.get("/sample-report")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Demo example — not based on your inputs.", html)

    def test_invalid_ai_response_is_rejected_with_form_and_demo_link(self):
        submitted = {
            "job_description": (
                "Data Analyst Intern. The intern will use SQL to analyze product "
                "data, prepare reports, and communicate findings to the team."
            ),
            "current_skills": "SQL",
            "projects_and_work": "No project example yet.",
        }
        with (
            patch.dict(os.environ, {"GROQ_API_KEY": "offline-test-key"}),
            patch("app.analyze_submission", side_effect=AnalysisValidationError("invalid")),
        ):
            response = self.client.post("/analyze", data=submitted)

        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 503)
        self.assertIn("response that could not be validated", html)
        self.assertIn("Demo example — not based on your inputs", html)
        self.assertIn('href="/sample-report"', html)
        self.assertNotIn("Response checks passed", html)
        for value in submitted.values():
            self.assertIn(value, html)

    def test_success_renders_validated_assessment_and_seven_ordered_plan(self):
        submitted = {
            "job_description": (
                "Data Analyst Intern. SQL is required. Excel experience is preferred. "
                "The intern will clean sales data and present findings to the team."
            ),
            "current_skills": "SQL, Excel",
            "projects_and_work": (
                "In a class project, I used Excel to clean a public movie ratings "
                "spreadsheet and make a pivot table. I wrote a short summary of the findings."
            ),
        }
        analysis = validated_analysis()
        with (
            patch.dict(os.environ, {"GROQ_API_KEY": "offline-test-key"}),
            patch("app.analyze_submission", return_value=analysis) as analyze_mock,
        ):
            response = self.client.post("/analyze", data=submitted)

        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Data Analyst Intern", html)
        self.assertIn("Assessment summary", html)
        self.assertIn("Skill-by-skill assessment", html)
        self.assertIn("Job-description excerpt", html)
        self.assertNotIn("<dt>Why it matters</dt>", html)
        self.assertIn("class=\"requirement-summary-meta\"", html)
        self.assertIn("class=\"requirement-meta-field\"", html)
        self.assertIn("Requirement type</span><span class=\"requirement-type\">Explicit", html)
        self.assertIn("Requirement type</span><span class=\"requirement-type\">Preferred", html)
        self.assertIn("Requirement type</span><span class=\"requirement-type\">Inferred", html)
        self.assertIn("Why this inference is uncertain", html)
        self.assertEqual(html.count("Why this inference is uncertain"), 1)
        self.assertIn("Additional interpretation note", html)
        self.assertNotIn("Uncertain inference", html)
        self.assertNotIn("Uncertain interpretation:", html)
        self.assertIn("Skill claimed — evidence not provided", html)
        self.assertIn("I used Excel to clean a public movie ratings spreadsheet and make a pivot table.", html)
        self.assertIn("A SQL analysis example with queries.", html)
        self.assertIn("Use SQL to answer one project question.", html)
        self.assertIn("SQL — Evidence gap:</strong> A SQL analysis example with queries.", html)
        self.assertIn("Evidence gap addressed</dt><dd>SQL — Evidence gap: A SQL analysis example with queries.</dd>", html)
        self.assertIn("Evidence provided", html)
        self.assertIn("Partial evidence", html)
        self.assertIn("Evidence not provided", html)
        self.assertIn(
            "Counts group requirements by the evidence described in your submitted examples; they do not measure competence.",
            html,
        )
        self.assertIn("Each evidence label describes only the submitted project or work examples", html)
        self.assertIn("Submitted-example evidence", html)
        self.assertRegex(
            html,
            r'<span class="evidence-label-caption">Submitted-example evidence</span>\s*'
            r'<span class="evidence-badge evidence-\d+">',
        )
        styles = Path(proofpath_app.app.static_folder, "styles.css").read_text(encoding="utf-8")
        self.assertIn(".requirement-meta-field { display: inline-flex; flex-direction: column", styles)
        self.assertIn(".evidence-label-group { display: grid; justify-items: start; gap: 8px; }", styles)
        self.assertIn(".assessment-details > div { min-width: 0; display: grid; align-content: start; gap: 7px;", styles)
        self.assertIn('class="count-value"', html)
        self.assertIn("Counts use the three evidence categories.", html)
        self.assertIn("remains part of", html)
        self.assertIn("Evidence not provided.", html)
        self.assertIn("This assessment reflects only the information and examples you submitted", html)
        self.assertIn('id="plan-and-report" hidden', html)
        self.assertIn('aria-expanded="false"', html)
        self.assertIn("Create My 7-Day Portfolio Plan", html)
        self.assertIn("Final report", html)
        self.assertIn("Examples that support requirements", html)
        self.assertIn(
            "Excel — Preferred requirement — Evidence provided:", html
        )
        self.assertIn(
            "SQL — Evidence gap:</strong> A SQL analysis example with queries. "
            "<span>(Skill claimed — evidence not provided)</span>", html
        )
        self.assertIn(
            "Communication — Evidence gap:</strong> A concise explanation of an analysis for an audience. "
            "<span>(Partial evidence)</span>",
            html,
        )
        self.assertIn(
            "Only inferred requirements with a displayed uncertainty note are marked uncertain.",
            html,
        )
        self.assertNotIn("Requirement interpretations may be uncertain where noted", html)
        
        self.assertEqual(html.count('<li class="plan-day">'), 7)
        self.assertEqual(
            re.findall(r'class="plan-day-number">Day (\d)', html),
            list("1234567"),
        )

        expected_deliverables = [
            "A SQL project brief documenting the query objective.",
            "A SQL query file containing a sample query and results.",
            "A SQL analysis file with documented query outputs.",
            "A SQL analysis file and a query-check log.",
            "An updated SQL analysis file containing corrected queries and results.",
            "A SQL findings note summarizing query results and conclusions.",
            "A packaged SQL project containing the analysis files and README.",
        ]

        for deliverable in expected_deliverables:
            self.assertIn(deliverable, html)

        self.assertEqual(analyze_mock.call_count, 1)

    def test_report_disclaimer_does_not_claim_uncertainty_when_no_inference_exists(self):
        submitted = {
            "job_description": (
                "Data Analyst Intern. SQL is required. Excel experience is preferred. "
                "The intern will clean sales data and present findings to the team."
            ),
            "current_skills": "SQL, Excel",
            "projects_and_work": (
                "In a class project, I used Excel to clean a public movie ratings "
                "spreadsheet and make a pivot table."
            ),
        }
        analysis = validated_analysis().model_copy(
            update={"skill_assessments": validated_analysis().skill_assessments[:2]}
        )
        with (
            patch.dict(os.environ, {"GROQ_API_KEY": "offline-test-key"}),
            patch("app.analyze_submission", return_value=analysis),
        ):
            response = self.client.post("/analyze", data=submitted)

        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("No inferred requirements are marked uncertain", html)
        self.assertNotIn("Only inferred requirements with a displayed uncertainty note", html)

    def test_results_reveal_is_client_side_and_has_no_second_analysis_call(self):
        with open(proofpath_app.Path(__file__).resolve().parents[1] / "static" / "results.js", encoding="utf-8") as script_file:
            script = script_file.read()
        self.assertIn('aria-expanded', script)
        self.assertIn('planAndReport.hidden = isExpanded', script)
        self.assertNotIn("fetch(", script)
        self.assertNotIn("/analyze", script)

    def test_bypassed_invalid_model_never_renders_personalized_results(self):
        submitted = {
            "job_description": (
                "Data Analyst Intern. SQL is required. Excel experience is preferred. "
                "The intern will clean sales data and present findings to the team."
            ),
            "current_skills": "SQL, Excel",
            "projects_and_work": "A submitted example.",
        }
        invalid = proofpath_app.AnalysisResult.model_construct(
            role_title="PRIVATE INVALID RESULT",
            overview="must not appear",
            skill_assessments=[],
            plan_days=[],
            assumptions_and_limitations="invalid",
        )
        with (
            patch.dict(os.environ, {"GROQ_API_KEY": "offline-test-key"}),
            patch("app.analyze_submission", return_value=invalid),
        ):
            response = self.client.post("/analyze", data=submitted)

        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 503)
        self.assertIn("could not be validated", html)
        self.assertNotIn("PRIVATE INVALID RESULT", html)
        self.assertNotIn("must not appear", html)
        self.assertIn("Demo example — not based on your inputs", html)
        for value in submitted.values():
            self.assertIn(value, html)


if __name__ == "__main__":
    unittest.main()
