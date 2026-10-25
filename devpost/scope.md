---
doc: scope
status: approved
---

# ProofPath AI

ProofPath AI helps internship applicants turn a job description and their own skill and project information into a grounded evidence-gap assessment and a focused portfolio plan.

## The Problem

Students and recent graduates may study tools such as Excel, SQL, Python, and Power BI without knowing which skills a particular internship expects them to demonstrate. Generic career advice often says what to study but does not give concrete steps or show how a candidate's project evidence relates to a specific role.

## The Unique Kernel

It makes the evidence behind each internship skill visible without treating a user's self-reported skill as verified ability. The report shows what examples the user provided, what is missing, and how to build a small portfolio that demonstrates relevant skills.

## Who It's For

Students and recent graduates applying for entry-level data analyst internships. They know or are learning tools such as Excel, SQL, Python, and Power BI, but need concrete guidance on what a role asks for and how to demonstrate their preparation.

## The Core Workflow

For each internship application, the user enters a job description and their current skills and relevant projects. ProofPath AI lists skills explicitly stated or reasonably inferred from the description, assesses the evidence supplied for each, and produces a tailored seven-day portfolio plan and report. If a requirement or skill is ambiguous, the app flags its interpretation as uncertain instead of presenting it as certain.

## Inspiration & Identity

The interface should feel clear, professional, and suitable for beginners. Explainability and reliability should be evident throughout the workflow.

## Why This Matters to the Learner

The learner wants students and recent graduates to get concrete, actionable steps rather than generic advice about what to study. They also want to learn to plan before coding and understand project decisions.

## What "Working" Looks Like

In a no-account demo, a user enters a sample entry-level data analyst internship description, their skills, and relevant projects. The app lists skills explicitly stated or reasonably inferred from the description and flags ambiguous interpretations. It assesses the information provided for each skill, then generates a personalized seven-day portfolio plan with realistic daily tasks and tangible deliverables that build toward one small portfolio project. The plan helps address priority evidence gaps; it does not promise mastery of every missing skill in seven days. The app then shows a final report with strengths, missing evidence, next steps, and portfolio deliverables that the user can view or download.

Evidence categories describe only the information supplied, not the user's actual ability:

- **Evidence provided:** The user describes a relevant project or work example demonstrating the skill.
- **Partial evidence:** The example demonstrates only part of the required skill or lacks enough detail.
- **Evidence not provided:** The role requires the skill or the user claims it, but no supporting example is described. When the user claims the skill without an example, label it **“Skill claimed — evidence not provided.”**

The app must not infer ability from a skill claim, claim to verify skills, or conclude that missing examples mean the user lacks ability. It should suggest concrete evidence that could help, such as a SQL project using joins, aggregations, CTEs, or data analysis.

## The POC Boundary

One workflow for entry-level data analyst internship applications: enter a job description, skills, and relevant projects; review explicitly stated or reasonably inferred requirements, with ambiguous interpretations flagged; review evidence gaps; receive a realistic seven-day plan of daily tasks and tangible deliverables building toward one small portfolio project; and view or download the final report. The plan targets priority evidence gaps without promising mastery of every missing skill. The demo works without account creation and uses a sample internship description.

## Later

Support for internship roles beyond entry-level data analyst positions.

## Explicitly Cut

- Account creation: the demo should let someone try the full workflow without an account.
- Automatic skill verification: the app assesses submitted examples and must not claim to validate a person's actual ability.
