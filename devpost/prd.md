---
doc: prd
status: approved
---

# ProofPath AI — Product Requirements

ProofPath AI helps students and recent graduates applying for entry-level data analyst internships connect job requirements to the project evidence they provide and build one small portfolio project around priority gaps.
Source: `scope.md > The Problem`, `scope.md > Who It's For`, `scope.md > The Unique Kernel`.

## The Core Journey

1. The user opens ProofPath AI and sees the product purpose, a short three-step explanation, and two ways to begin: **Analyze an Internship** or **Try Sample Data Analyst Internship**.
2. Either action opens the same guided input form. The sample option fills it with realistic, complete example data; the regular option opens it ready for the user's information.
3. The user enters a job description, and may add current skills (including skills they are learning) and relevant projects or work examples. For each example, the form asks what the user personally did and which tools they used. The form explains that the assessment evaluates submitted information and does not verify actual ability.
4. The user submits the form. A blank or unusably short job description prompts a clear message and preserves entered information. Missing skills or project examples do not block analysis.
5. The results page presents an assessment overview, then a skill-by-skill assessment. It distinguishes skills explicitly stated in the job description from reasonable but uncertain inferences, and flags ambiguous interpretations.
6. The user reviews a seven-day portfolio plan tailored to the role and supplied information. It builds toward one small project and prioritizes two or three evidence gaps where personal information is available. If both skills and examples are blank, it clearly identifies the plan as a general beginner-friendly starting point based on the job requirements.
7. Directly below the plan on the same scrollable results page, the user sees a concise final report and can download it. The report preserves the distinction between self-reported skills and supporting examples and makes uncertainty and limitations clear.

Source: `scope.md > The Core Workflow`, `scope.md > What "Working" Looks Like`, `scope.md > The POC Boundary`.

## Screens and Layout

### Home

- Show the app name **ProofPath AI**.
- Headline: **Turn Internship Requirements into Portfolio Evidence**.
- Short description: “Understand which skills an internship requires, identify where your project evidence is missing, and build a realistic seven-day portfolio plan.”
- Provide primary actions: **Analyze an Internship** and **Try Sample Data Analyst Internship**.
- Show a short three-step explanation: paste the job description; add skills and projects; receive an evidence-gap assessment and personalized portfolio plan.
- Both actions lead to the same input form. The sample action pre-fills the form with realistic example data.

### Guided input form

Use one simple form with clearly labeled fields and concise guidance:

1. **Internship job description** — required; explain that enough text is needed to identify meaningful requirements.
2. **Current skills** — optional; users can include skills they are still learning.
3. **Relevant projects or work examples** — optional; prompt for what the user personally did and which tools they used.

Show that the assessment evaluates submitted information and examples; it does not verify actual ability. Keep user-entered content when validation fails.

### Results page

Keep the complete assessment, plan, and report on one scrollable page in this order:

1. Assessment summary.
2. Skill-by-skill assessment.
3. Seven-day portfolio plan.
4. Final report.
5. **Download Report** action.

Use section headings and consistent styling so users can keep their place. Do not send them to another page to see the plan or report, or make them lose the assessment while navigating to the plan.

Source: `scope.md > What "Working" Looks Like`, `scope.md > The POC Boundary`.

## Look and Feel

- Modern, professional, clean style inspired by analytics and career-planning tools.
- Deep navy for headings, navigation, and important actions; teal for highlights, progress indicators, and positive actions; white or very light gray background.
- Clear, readable sans-serif typography with a strong heading hierarchy.
- Centered content area, consistent spacing, readable cards, and clear section headings.
- Make primary actions easy to find. Use consistent evidence-category styles with visible text labels and accessible contrast; never rely on color alone.
- Use icons or subtle visual cues only when they help comprehension. Avoid excessive animation, decorative graphics, unnecessary charts, and crowded layouts.
- Keep assessment cards or tables readable on a normal laptop screen. Show the seven days as a clear sequence. Make the final report organized and suitable for sharing.
- Include helpful empty states, input guidance, and friendly validation messages.

Source: `scope.md > Inspiration & Identity`.

## Features and Behavior

### Internship input and sample demo

- **Analyze an Internship** opens the empty guided form.
- **Try Sample Data Analyst Internship** opens the same form with realistic sample job description, skills, and project examples filled in; the sample is complete enough to demonstrate the full workflow.
- The user can edit sample values before submitting.
- Skills and project examples are optional. The job description must contain enough text to identify meaningful requirements.
- If the job description is blank or too short to analyze, show a friendly inline message asking the user to paste the internship description. Do not produce an assessment from an empty or unusable description.
- Preserve all entered information after a validation error.
- Explain what missing optional information means before analysis: without skills, the app cannot compare requirements with self-reported skills; without examples, it has no supporting evidence to assess. Neither case means the user lacks ability.
- **Success criteria:** Both home actions reach the same form; the sample is populated and editable; an unusable job description produces an inline message and no results; the user's other entries remain in the form after validation; blank optional fields do not block submission.

### Requirements and skill-by-skill evidence assessment

- List skills and requirements explicitly stated or reasonably inferred from the supplied job description. Do not omit an identified skill from the requirements list.
- Distinguish explicit requirements from reasonable inferences. Flag ambiguous interpretations as uncertain and briefly explain why the interpretation was included; do not present uncertain inferences as definite employer requirements.
- Provide an overview with the internship role, key identified skills, counts of evidence categories, and a brief explanation of the highest-priority evidence gaps. Counts describe evidence categories only and must not be presented as competence or ability scores.
- For each identified skill, show:
  - **Required skill**.
  - **Why it matters**, grounded in the job description.
  - **Evidence category**.
  - **User's supporting example**, if one was provided.
  - **What is missing** to make the example more relevant or clear.
  - **Suggested next step** to create or improve evidence.
- Use only these evidence categories:
  - **Evidence provided:** The user describes a relevant project or work example that supports the skill. A self-reported skill name alone never qualifies.
  - **Partial evidence:** The example demonstrates some relevant work, but only part of the requirement or lacks detail needed to connect it clearly to the role.
  - **Evidence not provided:** The job requires the skill or the user claims it, but no supporting example is described.
- If a user claims a skill without a supporting example, label it **“Skill claimed — evidence not provided.”** Do not say the user lacks the skill, infer ability from the claim, or claim to have independently verified ability.
- Apply this distinction consistently in the overview, every skill assessment, and the final report: a reported skill is a claim by the user; supporting evidence is a relevant described project or work example. Only the latter can be categorized as evidence provided.
- Do not label an example **Partial evidence** merely because information is absent. Use that category only when the described example demonstrates some relevant work. If the user's role or tools are unclear, identify what detail is needed.
- If skills and projects are both blank, explain that there is no personal skill or project information to compare. Show role requirements with evidence not provided, while making clear this is about the information submitted, not the user's ability.
- **Success criteria:** Every skill inferred or stated from the job description appears in the requirements list; explicit and inferred items are distinguishable; ambiguous items carry an uncertainty explanation; every skill row contains the defined fields; a skill name alone is never categorized as evidence provided; claims without examples receive the exact claim/evidence label; evidence categories distinguish user claims from relevant supporting examples everywhere; no category count or copy suggests verified ability; each evidence gap includes a concrete next step.

### Seven-day portfolio plan

- Offer a prominent **Create My 7-Day Portfolio Plan** action after the skill assessment. Activating it reveals or scrolls to the plan on the same results page without removing the assessment.
- Create seven realistic daily tasks that build on one another toward one small, end-to-end data analyst portfolio project.
- Each day includes a clear task, a tangible deliverable, the skill or evidence gap it addresses, a short explanation of its relevance, and a simple completion criterion.
- Adapt the plan to the job description, user-provided skills and examples, and available evidence. Prioritize two or three high-value gaps so the plan is achievable for a beginner.
- Use tools only when relevant to the role and feasible for the project. Do not require Excel, SQL, Python, and Power BI all in one plan.
- The suggested progression may include project question and dataset, data inspection/cleaning, analysis, focused practice of a priority skill, a visual summary when appropriate, findings and limitations, and packaging the work. Adapt this structure to the actual role rather than forcing every step or tool.
- If user experience details are insufficient, state the assumptions and offer a reasonable beginner-friendly default. If both skills and project examples are blank, label the plan as a general starting plan based on job requirements.
- The plan helps demonstrate selected skills; it must not promise mastery of all missing skills in seven days or claim that the project verifies ability.
- **Success criteria:** The plan contains seven ordered days, each with all five requested elements; tasks and deliverables form one coherent project; the plan addresses no more than two or three priority gaps when personal input allows; missing personal context and assumptions are disclosed; no mastery or verification claim appears.

### Final report and download

- Place the final report directly below the seven-day plan on the same results page.
- Include a concise summary of strengths supported by submitted examples, missing evidence, prioritized next steps, and expected portfolio deliverables. Explain relevant uncertainty and limits.
- Preserve the distinction between skills the user reports and examples supporting them. A self-reported skill name alone is never proof of demonstrated skill or a strength; only a relevant described project or work example can support an evidence-provided assessment. Keep the three evidence categories consistent with the skill-by-skill assessment. Do not invent experience, make unsupported conclusions, or imply independent verification.
- Provide a clearly visible **Download Report** button. A well-formatted PDF is preferred. If `4-spec` determines that reliable PDF generation is impractical within the hackathon, use a simpler downloadable format that preserves the report's essential content and readable section structure. The download action is required and must work end to end.
- **Success criteria:** The report appears below the plan; it includes the required summary sections and relevant uncertainty/limitations; clicking **Download Report** successfully downloads an openable, readable file containing the report's essential content and section structure; the downloaded report preserves the distinction between claimed skills and supporting examples; no content claims verified ability.

Source: `scope.md > What "Working" Looks Like`, `scope.md > The POC Boundary`, `scope.md > Explicitly Cut`.

## States and Boundaries

- **First visit:** Show the home content and both clear entry actions.
- **Sample selected:** The shared input form opens with complete, realistic example values that the user can edit.
- **Blank or unusable job description:** Show inline validation, preserve all entries, and do not generate results.
- **Skills left blank:** Allow analysis; explain that no self-reported skills were supplied for comparison. Do not conclude that the user has no skills.
- **Projects left blank:** Allow analysis; mark supporting examples as evidence not provided, explain that this does not establish lack of ability, and suggest concrete project evidence.
- **Both optional fields blank:** Allow analysis and create a clearly labeled, general beginner-friendly plan based on job requirements.
- **Ambiguous job-description language:** Flag and explain the uncertain interpretation in the assessment.
- **Results and plan:** Keep the assessment, plan, and report together on one scrollable page. Plan action must preserve the assessment.
- **No persistence requirement:** The demo does not require accounts or saved profiles; users can complete the workflow without signing in.

Source: `scope.md > The POC Boundary`, `scope.md > Explicitly Cut`.

## Product Decisions

- Focus the demo on entry-level data analyst internships so the one-week project can stay small and concrete.
- Offer a complete sample path for judges, while keeping the same form and workflow available for a user's own internship.
- Treat evidence categories as descriptions of supplied examples, not judgments of ability, and disclose uncertainty in inferred requirements.
- Keep the assessment, plan, and final report together on one results page to preserve context and simplify the demo.
- Prioritize two or three evidence gaps and one coherent project; a seven-day plan is a start toward evidence, not a promise of mastery.
- Use the learner's selected navy, teal, light background, readable typography, and accessible labels as visual direction.
- Prefer PDF download when a reliable approach fits the hackathon; the downloadable report itself is required.

## What We're Building

- One no-account workflow for entry-level data analyst internship applications.
- A professional home page, a shared input form with editable sample data, a requirements and evidence assessment, an adaptive seven-day project plan, and a final report with a download action.
- Friendly validation, empty states, preserved form entries after validation errors, uncertainty explanations, and accessible evidence-category labels.

## Deferred From the POC

- Support for internship roles beyond entry-level data analyst positions, as identified in `scope.md > Later`.
- Account creation and automatic skill verification, as excluded in `scope.md > Explicitly Cut`.

## Possible Later Enhancements

The scope identifies support for other internship roles as a possible later direction.

## Non-Goals

- Verify or certify a person's real-world skill or ability; the app only assesses information and examples the user provides.
- Promise mastery of every missing skill in seven days; the plan creates a small project to demonstrate selected skills.
- Require an account, create a complicated dashboard, or add unrelated features to this demo.
- Generate a competence score that suggests ability has been independently verified.

## Open Questions

- **Download format:** `4-spec` should choose PDF if it can be implemented reliably within the hackathon; otherwise choose a simpler downloadable format that keeps the report's essential content and readable structure. The end-to-end download is required in either format. Resolve the implementation choice before building.
