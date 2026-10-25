import unittest

from models import AnalysisResult, SkillAssessment
from plan_builder import build_seven_day_plan


def assessed_skill(
    name,
    gap,
    category="Evidence not provided",
    quote="",
):
    return SkillAssessment.model_validate({
        "skill_name": name,
        "requirement_type": "explicit",
        "job_description_basis": f"The role requires {name}.",
        "uncertainty_note": "",
        "evidence_category": category,
        "skill_claimed_by_user": category != "Evidence not provided",
        "supporting_example_quote": quote,
        "what_is_missing": gap,
        "suggested_next_step": f"Create a small {name} example.",
    })


class DeterministicPlanBuilderTests(unittest.TestCase):
    def test_returns_exactly_seven_ordered_validated_days(self):
        skills = [assessed_skill("SQL", "A SQL query example with joins and grouped totals.")]
        plan = build_seven_day_plan(skills)
        self.assertEqual(len(plan), 7)
        self.assertEqual([day.day_number for day in plan], list(range(1, 8)))
        self.assertTrue(all(day.task and day.deliverable and day.completion_criterion for day in plan))
        self.assertTrue(all(day.targeted_gap.endswith(skills[0].what_is_missing) for day in plan))

    def test_many_gaps_select_only_first_three_in_assessment_order(self):
        skills = [
            assessed_skill("SQL", "A SQL query example with joins and grouped totals."),
            assessed_skill("Excel", "A spreadsheet example with formulas and a summary."),
            assessed_skill("Power BI", "A dashboard file showing labeled metrics."),
            assessed_skill("Python", "A notebook example with data cleaning and analysis."),
            assessed_skill("Statistics", "A documented test comparing two groups."),
        ]
        plan = build_seven_day_plan(skills)
        selected = {
            "SQL — Evidence gap: A SQL query example with joins and grouped totals.",
            "Excel — Evidence gap: A spreadsheet example with formulas and a summary.",
            "Power BI — Evidence gap: A dashboard file showing labeled metrics.",
        }
        self.assertTrue({day.targeted_gap for day in plan}.issubset(selected))
        self.assertEqual({day.targeted_gap for day in plan}, selected)

    def test_partial_and_missing_evidence_are_prioritized_in_stable_order(self):
        skills = [
            assessed_skill("Excel", "An example with a documented summary and formulas.", "Evidence provided", "I made a summary."),
            assessed_skill("SQL", "A query example that demonstrates joins and totals.", "Partial evidence", "I wrote a basic query."),
            assessed_skill("Python", "A notebook with cleaning steps and results."),
            assessed_skill("Power BI", "A dashboard with labeled metrics."),
        ]
        plan = build_seven_day_plan(skills)
        targets = {day.targeted_gap.split(" — Evidence gap:", 1)[0] for day in plan}
        self.assertEqual(targets, {"SQL", "Python", "Power BI"})
        self.assertNotIn("Excel", targets)

    def test_zero_gaps_uses_evidence_strengthening_targets_without_changing_evidence(self):
        skills = [
            assessed_skill("SQL", "A stronger SQL example with documented findings.", "Evidence provided", "I used SQL in a class project."),
            assessed_skill("Excel", "A short explanation of formulas and results.", "Evidence provided", "I used Excel to summarize records."),
            assessed_skill("Communication", "A concise findings explanation for an audience.", "Evidence provided", "I wrote a findings note."),
            assessed_skill("Python", "A notebook with a reproducible analysis.", "Evidence provided", "I used Python for a small analysis."),
        ]
        original = [skill.model_dump() for skill in skills]
        plan = build_seven_day_plan(skills)
        self.assertEqual({day.targeted_gap.split(" — Evidence gap:", 1)[0] for day in plan},
                         {"SQL", "Excel", "Communication"})
        self.assertEqual([skill.model_dump() for skill in skills], original)
        self.assertTrue(all(skill.evidence_category == "Evidence provided" for skill in skills))
        self.assertTrue(all(skill.supporting_example_quote for skill in skills))

    def test_no_gap_or_plan_text_invents_an_unassessed_target(self):
        skills = [
            assessed_skill("SQL", "A documented SQL query with joins and totals."),
            assessed_skill("Documentation", "An assumptions document with recorded decisions."),
            assessed_skill("Excel", "A workbook with a formula and summary."),
            assessed_skill("Python", "A notebook with reproducible results."),
        ]
        plan = build_seven_day_plan(skills)
        selected_names = {"SQL", "Documentation", "Excel"}
        for day in plan:
            target_name = day.targeted_gap.split(" — Evidence gap:", 1)[0]
            self.assertIn(target_name, selected_names)
            self.assertIn(target_name, day.why_it_matters)
            self.assertNotIn("Python", day.targeted_gap)

    def test_known_skill_templates_are_relevant_to_assessed_skill(self):
        examples = {
            "SQL": ("A SQL query file", "dataset"),
            "Excel": ("a spreadsheet workbook", "dataset"),
            "Python": ("a Python analysis notebook", "dataset"),
            "Power BI": ("a dashboard file", "dataset"),
            "Communication": ("a findings summary", None),
            "Documentation": ("an assumptions document", None),
        }
        gaps = {
            "SQL": "A SQL query example with joins and grouped totals.",
            "Excel": "A spreadsheet workbook with formulas and a summary.",
            "Python": "A Python notebook with cleaning and analysis results.",
            "Power BI": "A dashboard file with labeled metrics and charts.",
            "Communication": "A concise findings explanation for an audience.",
            "Documentation": "An assumptions document listing decisions and reasons.",
        }
        for skill_name, (artifact_hint, data_hint) in examples.items():
            with self.subTest(skill=skill_name):
                plan = build_seven_day_plan([assessed_skill(skill_name, gaps[skill_name])])
                text = " ".join(day.task + " " + day.deliverable for day in plan).casefold()
                self.assertIn(artifact_hint.casefold(), text)
                if data_hint:
                    self.assertIn("dataset", text)
                else:
                    self.assertNotIn("dataset", text)

    def test_assumptions_document_is_created_then_improved(self):
        skill = assessed_skill(
            "Documentation",
            "An assumptions document recording data choices and their reasons.",
        )
        plan = build_seven_day_plan([skill])
        self.assertIn("create", plan[0].task.casefold())
        self.assertIn("assumptions document", plan[0].deliverable.casefold())
        self.assertIn("improve", plan[4].task.casefold())
        self.assertIn("assumptions document", plan[4].deliverable.casefold())
        self.assertNotIn("dataset", " ".join(day.task for day in plan).casefold())

    def test_all_days_are_independent_checkable_and_form_a_progression(self):
        skills = [
            assessed_skill("SQL", "A SQL query example with joins and grouped totals."),
            assessed_skill("Power BI", "A dashboard file showing labeled metrics."),
        ]
        plan = build_seven_day_plan(skills)
        self.assertTrue(all("feedback" not in day.task.casefold() for day in plan))
        self.assertTrue(all("approval" not in day.completion_criterion.casefold() for day in plan))
        self.assertTrue(all(any(word in day.completion_criterion.casefold() for word in (
            "saved", "lists", "records", "opens", "contains", "shows", "passes"
        )) for day in plan))
        self.assertTrue(all(any(word in plan[index].task.casefold() for word in (
            "extend", "improve", "package"
        )) for index in range(1, 7)))
        AnalysisResult.model_validate({
            "role_title": "Analyst intern",
            "overview": "A deterministic test plan.",
            "skill_assessments": [skill.model_dump() for skill in skills],
            "plan_days": [day.model_dump() for day in plan],
            "assumptions_and_limitations": "Synthetic test data; ability is not verified.",
        })

    def test_every_selected_target_receives_relevant_work(self):
        skills = [
            assessed_skill("SQL", "A SQL query example with joins and grouped totals."),
            assessed_skill("Excel", "A workbook with a formula and summary."),
            assessed_skill("Python", "A notebook with reproducible analysis results."),
        ]
        plan = build_seven_day_plan(skills)
        for skill in skills:
            matching = [day for day in plan if day.targeted_gap.startswith(
                f"{skill.skill_name} — Evidence gap:")]
            self.assertTrue(matching)
            self.assertTrue(all(skill.skill_name in day.why_it_matters for day in matching))


if __name__ == "__main__":
    unittest.main()
